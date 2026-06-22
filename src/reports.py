"""Generación de informes descargables (CSV y PDF) de métricas y alarmas.

Dos alcances:
- Por paciente: usa la selección del monitor (paciente, rango de fechas/horas, métricas).
  El PDF incluye, para CADA evento de alarma, un mini gráfico de esa métrica desde
  2 h antes hasta 2 h después del evento.
- Resumen: tabla de todos los pacientes con sus últimos valores y estado de alerta.

Pensado para la Raspberry Pi (headless): matplotlib usa el backend "Agg" y fpdf2 es
pura-Python. Las figuras se cierran siempre para no acumular memoria.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # backend sin display: DEBE ir antes de importar pyplot
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates as mdates  # noqa: E402
import pandas as pd  # noqa: E402
from fpdf import FPDF  # noqa: E402

from src.config import METRICS, CFG  # noqa: E402
from src.data_loader import (  # noqa: E402
    get_patient_info,
    get_filtered_data,
    get_patient_alarm_history,
    group_consecutive_alarms,
    get_patients_summary,
)
from src.dash_app.figures import calculate_stats  # noqa: E402

MAX_ALARM_CHARTS = 12
ALARM_WINDOW_HOURS = 2
TZ = CFG.tz

_FONT_DIR = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
_FONT_REGULAR = os.path.join(_FONT_DIR, "DejaVuSans.ttf")
_FONT_BOLD = os.path.join(_FONT_DIR, "DejaVuSans-Bold.ttf")

# Métricas mostradas en el resumen del dashboard (mismas que dashboard.py).
_SUMMARY_METRICS = [
    "heart_rate",
    "blood_oxygen_saturation",
    "temperature",
    "systolic_blood_pressure",
]


# --------------------------- helpers comunes ---------------------------
def _range_bounds(date_start, date_end, time_start, time_end):
    """Bordes tz-aware del rango (misma lógica que get_filtered_data)."""
    if time_start is not None and time_end is not None:
        start = pd.to_datetime(date_start).tz_localize(TZ) + pd.Timedelta(hours=time_start)
        end = pd.to_datetime(date_end).tz_localize(TZ) + pd.Timedelta(hours=time_end)
    else:
        start = pd.to_datetime(date_start).tz_localize(TZ)
        end = pd.to_datetime(date_end).tz_localize(TZ) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    return start, end


def _format_alarm_range(start, end, count) -> str:
    """Fecha puntual si es una sola alarma; rango "de X a Y" si son consecutivas."""
    if count <= 1:
        return start.strftime("%d/%m/%Y %H:%M")
    if start.date() == end.date():
        return f"{start.strftime('%d/%m/%Y')} {start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
    return f"{start.strftime('%d/%m/%Y %H:%M')} - {end.strftime('%d/%m/%Y %H:%M')}"


def _calc_age(dob_raw) -> str:
    try:
        dob = datetime.strptime(str(dob_raw), "%Y-%m-%d %H:%M:%S")
        return str((datetime.now() - dob).days // 365)
    except Exception:
        return "N/D"


# --------------------------- CSV por paciente ---------------------------
def build_patient_csv(patient_id, metrics, date_start, date_end, time_start, time_end) -> pd.DataFrame:
    """Lecturas en formato largo: fecha_hora, metrica, unidad, valor, fuera_de_rango."""
    cols = ["fecha_hora", "metrica", "unidad", "valor", "fuera_de_rango"]
    info = get_patient_info(patient_id)
    if not info:
        return pd.DataFrame(columns=cols)

    imei = str(info["imei"])
    parts = []
    for metric in metrics or []:
        cfg = METRICS.get(metric)
        if not cfg:
            continue
        df = get_filtered_data(imei, metric, date_start, date_end, time_start, time_end)
        df = df.dropna(subset=["value"]).reset_index(drop=True)
        if df.empty:
            continue

        nmin, nmax = cfg.get("normal_min"), cfg.get("normal_max")
        flags = pd.Series("no", index=df.index)
        if nmin is not None:
            flags[df["value"] < nmin] = "bajo"
        if nmax is not None:
            flags[df["value"] > nmax] = "alto"

        part = pd.DataFrame({
            "fecha_hora": df["record_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S"),
            "metrica": cfg["name"],
            "unidad": cfg["unit"],
            "valor": df["value"],
            "fuera_de_rango": flags,
        })
        parts.append(part)

    if not parts:
        return pd.DataFrame(columns=cols)

    out = pd.concat(parts, ignore_index=True)
    return out.sort_values(["fecha_hora", "metrica"]).reset_index(drop=True)[cols]


# --------------------------- gráfico de un evento de alarma ---------------------------
def _render_alarm_chart_png(imei: str, event: dict) -> bytes:
    """Gráfico PNG de la métrica del evento, de 2 h antes a 2 h después."""
    metric = event["metric_key"]
    cfg = METRICS[metric]
    win_start = event["start"] - pd.Timedelta(hours=ALARM_WINDOW_HOURS)
    win_end = event["end"] + pd.Timedelta(hours=ALARM_WINDOW_HOURS)

    # get_filtered_data filtra por hora entera: pedimos de más y recortamos exacto.
    df = get_filtered_data(imei, metric, win_start.date(), win_end.date(),
                           win_start.hour, win_end.hour + 1)
    df = df[(df["record_datetime"] >= win_start) & (df["record_datetime"] <= win_end)]

    fig, ax = plt.subplots(figsize=(6, 2.5), dpi=80)
    try:
        ax.plot(df["record_datetime"], df["value"], color=cfg["color"], linewidth=1.3)

        nmin, nmax = cfg.get("normal_min"), cfg.get("normal_max")
        if nmin is not None and nmax is not None:
            ax.axhspan(nmin, nmax, color="green", alpha=0.08, label="Rango normal")
        elif nmin is not None:
            ax.axhline(nmin, color="green", alpha=0.35, linestyle="--")

        d = df.dropna(subset=["value"])
        if nmin is not None:
            low = d[d["value"] < nmin]
            ax.scatter(low["record_datetime"], low["value"], color="red", s=12, zorder=5)
        if nmax is not None:
            high = d[d["value"] > nmax]
            ax.scatter(high["record_datetime"], high["value"], color="red", s=12, zorder=5)

        ax.set_title(f"{cfg['name']} ({cfg['unit']})", fontsize=9)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        return buf.getvalue()
    finally:
        plt.close(fig)


# --------------------------- PDF: utilidades fpdf2 ---------------------------
def _new_pdf() -> FPDF:
    pdf = FPDF()
    pdf.add_font("DejaVu", "", _FONT_REGULAR)
    pdf.add_font("DejaVu", "B", _FONT_BOLD)
    pdf.set_auto_page_break(auto=True, margin=15)
    return pdf


def _title(pdf: FPDF, text: str):
    pdf.set_font("DejaVu", "B", 16)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _line(pdf: FPDF, text: str, bold: bool = False, size: int = 10):
    pdf.set_font("DejaVu", "B" if bold else "", size)
    pdf.cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")


def _table(pdf: FPDF, headers, rows, widths, fills=None):
    pdf.set_font("DejaVu", "B", 9)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, align="C")
    pdf.ln()
    pdf.set_font("DejaVu", "", 9)
    for i, row in enumerate(rows):
        if pdf.get_y() > 275:
            pdf.add_page()
            pdf.set_font("DejaVu", "B", 9)
            for h, w in zip(headers, widths):
                pdf.cell(w, 7, h, border=1, align="C")
            pdf.ln()
            pdf.set_font("DejaVu", "", 9)
        fill = bool(fills[i]) if fills else False
        if fill:
            pdf.set_fill_color(255, 224, 224)
        for val, w in zip(row, widths):
            pdf.cell(w, 6, str(val), border=1, fill=fill)
        pdf.ln()


# --------------------------- PDF por paciente ---------------------------
def build_patient_pdf(patient_id, metrics, date_start, date_end, time_start, time_end) -> bytes:
    pdf = _new_pdf()
    pdf.add_page()
    _title(pdf, "Informe de Paciente")

    info = get_patient_info(patient_id)
    if not info:
        _line(pdf, "Paciente no encontrado.")
        return bytes(pdf.output())

    imei = str(info["imei"])
    _line(pdf, f"Paciente: {info.get('patient_id', patient_id)}", bold=True, size=11)
    _line(pdf, f"Género: {info.get('genre') or 'N/D'}    "
               f"Edad: {_calc_age(info.get('date_of_birth'))} años    "
               f"Hospital: {info.get('hospital_id', 'N/D')}")
    _line(pdf, f"Rango: {date_start} {int(time_start):02d}:00  a  {date_end} {int(time_end):02d}:00")
    _line(pdf, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    pdf.ln(3)

    # --- Estadísticas por métrica ---
    _line(pdf, "Estadísticas por métrica", bold=True, size=12)
    data_dict = {
        m: get_filtered_data(imei, m, date_start, date_end, time_start, time_end).dropna(subset=["value"])
        for m in (metrics or [])
    }
    stats = calculate_stats(data_dict)
    if stats:
        rows = [
            [s["metric"], f"{s['min']:.1f}", f"{s['max']:.1f}", f"{s['avg']:.1f}", s["unit"]]
            for s in stats
        ]
        _table(pdf, ["Métrica", "Mín", "Máx", "Prom", "Unidad"], rows, [70, 30, 30, 30, 30])
    else:
        _line(pdf, "Sin datos en el rango seleccionado.")
    pdf.ln(3)

    # --- Alarmas del rango (agrupadas en eventos) ---
    start_dt, end_dt = _range_bounds(date_start, date_end, time_start, time_end)
    metric_set = set(metrics or [])
    alarms = [
        a for a in get_patient_alarm_history(patient_id, "all", days=None)
        if a.metric_key in metric_set and start_dt <= a.timestamp <= end_dt
    ]
    events = group_consecutive_alarms(alarms)

    _line(pdf, "Alarmas", bold=True, size=12)
    if not events:
        _line(pdf, "No se registraron alarmas en el rango seleccionado.")
        return bytes(pdf.output())

    rows = [
        [
            _format_alarm_range(e["start"], e["end"], e["count"]),
            e["metric_name"],
            f"{e['extreme_value']:.1f} {e['unit']}",
            e["alert_type"].display_name,
            e["count"],
        ]
        for e in events
    ]
    _table(pdf, ["Fecha", "Métrica", "Valor", "Tipo", "N°"], rows, [70, 45, 30, 25, 20])
    pdf.ln(3)

    # --- Un gráfico por evento (acotado) ---
    _line(pdf, "Gráficos alrededor de cada alarma (±2 h)", bold=True, size=12)
    shown = events[:MAX_ALARM_CHARTS]
    if len(events) > MAX_ALARM_CHARTS:
        _line(pdf, f"Mostrando los primeros {MAX_ALARM_CHARTS} de {len(events)} eventos.")
    for e in shown:
        if pdf.get_y() > 195:
            pdf.add_page()
        caption = (f"{e['metric_name']} - {e['alert_type'].display_name} - "
                   f"{_format_alarm_range(e['start'], e['end'], e['count'])}")
        _line(pdf, caption, bold=True, size=9)
        png = _render_alarm_chart_png(imei, e)
        pdf.image(io.BytesIO(png), w=180)
        pdf.ln(2)

    return bytes(pdf.output())


# --------------------------- Resumen de todos los pacientes ---------------------------
def _summary_rows():
    summary = get_patients_summary()
    rows = []
    for p in summary:
        metrics = p.get("metrics", {})
        values = []
        for k in _SUMMARY_METRICS:
            m = metrics.get(k, {})
            val = m.get("display_value", m.get("latest_value"))
            values.append(f"{val:.1f}" if val is not None else "-")
        rows.append({
            "paciente": p["patient_id"],
            "genero": p.get("genre", "") or "-",
            "values": values,
            "alerta": "Sí" if p["alerts"] else "No",
            "n_alertas": len(p["alerts"]),
            "has_alert": bool(p["alerts"]),
        })
    return rows


def build_summary_csv() -> pd.DataFrame:
    rows = _summary_rows()
    out = []
    for r in rows:
        row = {"paciente": r["paciente"], "genero": r["genero"]}
        for k, v in zip(_SUMMARY_METRICS, r["values"]):
            row[METRICS[k]["name"]] = v
        row["alerta"] = r["alerta"]
        row["n_alertas"] = r["n_alertas"]
        out.append(row)
    return pd.DataFrame(out)


def build_summary_pdf() -> bytes:
    pdf = _new_pdf()
    pdf.add_page()
    _title(pdf, "Resumen de Pacientes")
    _line(pdf, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    pdf.ln(3)

    rows_data = _summary_rows()
    headers = ["Paciente", "Género", "FC", "SpO2", "Temp", "PA Sist", "Alerta", "N°"]
    widths = [24, 20, 24, 24, 24, 28, 24, 22]
    rows = [
        [r["paciente"], r["genero"], *r["values"], r["alerta"], r["n_alertas"]]
        for r in rows_data
    ]
    fills = [r["has_alert"] for r in rows_data]
    _table(pdf, headers, rows, widths, fills=fills)
    return bytes(pdf.output())
