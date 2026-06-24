"""Análisis por paciente: línea base personalizada y tendencias (alerta temprana).

Dos análisis:
1. Línea base personalizada: para cada paciente y métrica, percentiles de SU propio
   histórico (banda circadiana por franja horaria, con fallback global). Sirve para
   marcar cuándo se sale de SU patrón, no del umbral genérico igual para todos.
2. Tendencia semanal: FC en reposo nocturna, SpO2 y temperatura agregadas por semana,
   con pendiente sobre las últimas semanas para detectar deterioro sostenido.

Solo usa FC, SpO2 y temperatura (sin pasos ni presión). Limpia artefactos del sensor.
Todo se precalcula una vez y se cachea (los datos son estáticos por despliegue).
Los umbrales viven en src/config.py (defaults, NO validados clínicamente).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from src.config import (
    ANALYSIS_METRICS,
    PLAUSIBILITY,
    ADVERSE_DIRECTION,
    SLOPE_THRESHOLDS,
    ACFG,
)
from src.data_loader import load_all_data, get_patient_list


def _apply_cleaning(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Única fuente de limpieza: descarta NaN y valores fuera de plausibilidad."""
    df = df.dropna(subset=["value"])
    bounds = PLAUSIBILITY.get(metric)
    if bounds is not None:
        lo, hi = bounds
        df = df[(df["value"] >= lo) & (df["value"] <= hi)]
    return df


@lru_cache(maxsize=16)
def get_clean_series(imei: str, metric: str) -> pd.DataFrame:
    """Serie completa (record_datetime, value) de un paciente+métrica, ya limpia.

    Para uso on-demand (gráficos). El overview usa un único groupby (ver abajo).
    """
    _, wearable_df = load_all_data()
    df = wearable_df[
        (wearable_df["imei"] == str(imei)) & (wearable_df["metric"] == metric)
    ][["record_datetime", "value"]]
    return _apply_cleaning(df, metric).sort_values("record_datetime").reset_index(drop=True)


# --------------------------- línea base personalizada ---------------------------
def compute_personal_baseline(df: pd.DataFrame, metric: str) -> dict:
    """Banda personal p10–p90 por franja horaria (circadiana) + banda global de fallback."""
    if len(df) < ACFG.baseline_min_readings:
        return {"available": False, "reason": "few_data", "metric": metric}

    lo_p, hi_p = ACFG.low_pct, ACFG.high_pct
    overall = (
        float(np.percentile(df["value"], lo_p)),
        float(np.percentile(df["value"], hi_p)),
    )

    bucket = (df["record_datetime"].dt.hour // ACFG.circadian_bucket_hours).astype(int)
    buckets: dict[int, tuple] = {}
    for b, g in df.groupby(bucket):
        if len(g) >= ACFG.baseline_bucket_min:
            buckets[int(b)] = (
                float(np.percentile(g["value"], lo_p)),
                float(np.percentile(g["value"], hi_p)),
            )

    return {"available": True, "metric": metric, "overall": overall, "buckets": buckets}


def band_for(df: pd.DataFrame, baseline: dict) -> tuple[pd.Series, pd.Series]:
    """Devuelve (low, high) por fila según la franja horaria (fallback a banda global)."""
    overall = baseline["overall"]
    buckets = baseline["buckets"]
    b = (df["record_datetime"].dt.hour // ACFG.circadian_bucket_hours).astype(int)
    low = b.map(lambda x: buckets.get(x, overall)[0])
    high = b.map(lambda x: buckets.get(x, overall)[1])
    return low, high


# --------------------------- tendencia semanal ---------------------------
def compute_weekly_trend(df: pd.DataFrame, metric: str) -> dict:
    """Agrega por día y luego por semana, y ajusta una pendiente a las últimas semanas.

    La ventana se ancla a la ÚLTIMA fecha de datos del paciente (no a hoy), porque los
    datos son históricos. Marca 'adverse' si la dirección es clínicamente mala y la
    pendiente supera el umbral de la métrica.
    """
    if df.empty:
        return {"available": False, "reason": "no_data", "metric": metric}

    s = df.set_index("record_datetime")["value"].sort_index()

    if metric == "heart_rate":
        # FC en reposo nocturna: percentil bajo de la FC entre 00:00 y 06:00.
        night = s.between_time(
            f"{ACFG.night_start_hour:02d}:00", f"{ACFG.night_end_hour:02d}:00"
        )
        if night.empty:
            return {"available": False, "reason": "no_data", "metric": metric}
        daily = night.groupby(night.index.date).quantile(ACFG.night_resting_pct / 100.0)
    else:
        # SpO2 y temperatura: mediana diaria.
        daily = s.groupby(s.index.date).median()

    if daily.empty:
        return {"available": False, "reason": "no_data", "metric": metric}

    daily.index = pd.to_datetime(daily.index)
    weekly = daily.resample("W").median().dropna().tail(ACFG.trend_weeks)

    values = [round(float(v), 1) for v in weekly.values]
    weeks = [str(d.date()) for d in weekly.index]

    if len(weekly) < ACFG.trend_min_weeks:
        return {"available": False, "reason": "few_weeks", "metric": metric,
                "weeks": weeks, "values": values}

    x = np.arange(len(weekly))
    slope = float(np.polyfit(x, weekly.values, 1)[0])
    adverse = (np.sign(slope) == ADVERSE_DIRECTION[metric]) and (
        abs(slope) >= SLOPE_THRESHOLDS[metric]
    )
    direction = "up" if slope > 0 else ("down" if slope < 0 else "flat")

    return {
        "available": True,
        "metric": metric,
        "weeks": weeks,
        "values": values,
        "slope": round(slope, 3),
        "direction": direction,
        "adverse": bool(adverse),
        "magnitude": round(slope * (len(weekly) - 1), 1),  # cambio total estimado
    }


# --------------------------- overview cacheado ---------------------------
@lru_cache(maxsize=1)
def get_analysis_overview() -> dict:
    """Calcula baseline + tendencia de cada paciente y métrica (una vez, cacheado).

    Guarda solo parámetros de banda y valores semanales (kilobytes), no series crudas.
    """
    _, wearable_df = load_all_data()

    # Un solo recorrido: limpiar por métrica (vectorizado) y agrupar por paciente.
    # Mucho más rápido que filtrar el df de ~2,3 M filas una vez por paciente+métrica.
    groups: dict[tuple, pd.DataFrame] = {}
    for metric in ANALYSIS_METRICS:
        sub = wearable_df[wearable_df["metric"] == metric][["imei", "record_datetime", "value"]]
        sub = _apply_cleaning(sub, metric)
        for imei, g in sub.groupby("imei"):
            groups[(str(imei), metric)] = (
                g[["record_datetime", "value"]].sort_values("record_datetime").reset_index(drop=True)
            )

    empty = pd.DataFrame(columns=["record_datetime", "value"])
    patients = get_patient_list()
    overview: dict[str, dict] = {}

    for _, p in patients.iterrows():
        pid = str(p["patient_id"])
        imei = str(p["imei"])
        baselines: dict[str, dict] = {}
        trends: dict[str, dict] = {}
        adverse_metrics: list[str] = []

        for metric in ANALYSIS_METRICS:
            df = groups.get((imei, metric), empty)
            baselines[metric] = compute_personal_baseline(df, metric)
            trend = compute_weekly_trend(df, metric)
            trends[metric] = trend
            if trend.get("adverse"):
                adverse_metrics.append(metric)

        overview[pid] = {
            "patient_id": pid,
            "imei": imei,
            "genre": p.get("genre", "") or "",
            "baselines": baselines,
            "trends": trends,
            "adverse_metrics": adverse_metrics,
            "any_adverse": bool(adverse_metrics),
        }

    return overview


def get_patient_analysis(patient_id: str) -> dict | None:
    return get_analysis_overview().get(str(patient_id))


def get_adverse_cohort() -> list[dict]:
    """Pacientes con alguna tendencia adversa, ordenados por severidad (triage)."""
    rows = [v for v in get_analysis_overview().values() if v["any_adverse"]]
    rows.sort(key=lambda v: len(v["adverse_metrics"]), reverse=True)
    return rows
