from __future__ import annotations
import json
from functools import lru_cache
from datetime import datetime, timedelta
import pandas as pd
import math
from src.config import METRICS, Alarm, AlertType

JSON_PATH = "RA.json"


@lru_cache(maxsize=1)
def load_all_data():
    """Carga datos una sola vez y los mantiene en memoria."""
    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    patients_df = pd.DataFrame(data["patients"])
    wearable_df = pd.DataFrame(data["wearabledata"])

    # Pre-procesar tipos
    # Los datos están en UTC, convertimos a hora de Argentina (UTC-3)
    wearable_df["record_datetime"] = (
        pd.to_datetime(wearable_df["record_datetime"])
        .dt.tz_localize("UTC")  # Datos en UTC
        .dt.tz_convert("America/Argentina/Buenos_Aires")  # Convertir a hora Argentina
    )
    wearable_df["value"] = pd.to_numeric(wearable_df["value"], errors="coerce")

    return patients_df, wearable_df


def get_patient_list() -> pd.DataFrame:
    """Retorna lista de pacientes para el dropdown."""
    patients_df, _ = load_all_data()
    return patients_df[["patient_id", "imei", "genre", "date_of_birth", "hospital_id"]]


def get_patient_info(patient_id: str) -> dict | None:
    """Retorna info de un paciente específico."""
    patients_df, _ = load_all_data()
    patient = patients_df[patients_df["patient_id"] == str(patient_id)]
    if patient.empty:
        return None
    return patient.iloc[0].to_dict()


def get_filtered_data(imei: str, metric: str, date_start, date_end, time_start=None, time_end=None):
    """Filtra datos por IMEI, métrica, fechas y opcionalmente horario."""
    _, wearable_df = load_all_data()

    # Si se especifican horas, combinar fecha + hora para crear datetime exacto
    if time_start is not None and time_end is not None:
        # Crear datetime de inicio: date_start a las time_start horas
        start_datetime = pd.to_datetime(date_start).tz_localize("America/Argentina/Buenos_Aires") + pd.Timedelta(hours=time_start)
        # Crear datetime de fin: date_end a las time_end horas
        end_datetime = pd.to_datetime(date_end).tz_localize("America/Argentina/Buenos_Aires") + pd.Timedelta(hours=time_end)
    else:
        # Sin filtro de hora: usar día completo
        start_datetime = pd.to_datetime(date_start).tz_localize("America/Argentina/Buenos_Aires")
        end_datetime = pd.to_datetime(date_end).tz_localize("America/Argentina/Buenos_Aires") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    mask = (
        (wearable_df["imei"] == str(imei)) &
        (wearable_df["metric"] == metric) &
        (wearable_df["record_datetime"] >= start_datetime) &
        (wearable_df["record_datetime"] <= end_datetime)
    )

    df: pd.DataFrame = wearable_df[mask].copy()

    df = df.sort_values("record_datetime").reset_index(drop=True) #Ordena segun fecha
    
    # Filtro: Detectar gaps mayores a 15 minutos entre datos consecutivos
    # Donde haya un gap > 15 min, se inserta NaN para romper la línea en el gráfico
    # Aplicar filtro de gaps: insertar NaN donde hay más de 15 minutos entre datos
    GAP_THRESHOLD_MINUTES = 30
    if len(df) > 1:
        time_diffs = df["record_datetime"].diff()
        gap_threshold = pd.Timedelta(minutes=GAP_THRESHOLD_MINUTES)
        gaps = time_diffs > gap_threshold

        if gaps.any():
            gap_rows = []
            for idx in df[gaps].index:
                gap_rows.append({
                    "record_datetime": pd.to_datetime(df.loc[idx]["record_datetime"] - pd.Timedelta(seconds=1)),
                    "value": math.nan
                })

            # Crear DataFrame de gaps con dtypes explícitos
            gap_df = pd.DataFrame(gap_rows)

            # Concatenar y reordenar
            df = pd.concat([df, gap_df], ignore_index=True)
            df = df.sort_values("record_datetime").reset_index(drop=True)

    # df["ma_15m"] = df["value"].rolling(3, min_periods=1, center=True).mean()

    # # Asegurar que donde value es NaN, ma_15m también sea NaN (para romper líneas en gráficos)
    # df.loc[df["value"].isna(), "ma_15m"] = float('nan')

    return df[["record_datetime", "value"]]


def _detect_alarms(
    patient_id: str,
    patient_data: pd.DataFrame,
    metric_filter: str | None = None,
) -> list[Alarm]:
    """Single source of truth for alarm detection.

    Scans patient_data for values outside normal ranges defined in METRICS.
    Returns one Alarm per out-of-range reading, sorted by timestamp descending.
    """
    alarms: list[Alarm] = []

    for metric_key, metric_cfg in METRICS.items():
        normal_min = metric_cfg.get("normal_min")
        normal_max = metric_cfg.get("normal_max")

        if normal_min is None or normal_max is None:
            continue

        if metric_filter and metric_filter != "all" and metric_filter != metric_key:
            continue

        metric_data = patient_data[patient_data["metric"] == metric_key]
        if metric_data.empty:
            continue

        low = metric_data[metric_data["value"] < normal_min]
        high = metric_data[metric_data["value"] > normal_max]

        for _, row in low.iterrows():
            alarms.append(Alarm.from_row(patient_id, metric_key, row, AlertType.LOW))

        for _, row in high.iterrows():
            alarms.append(Alarm.from_row(patient_id, metric_key, row, AlertType.HIGH))

    alarms.sort(key=lambda a: a.timestamp, reverse=True)
    return alarms


def get_patients_summary() -> list[dict]:
    """Get summary of all patients with their latest values and alert status."""
    patients_df, wearable_df = load_all_data()

    now = pd.Timestamp.now(tz="America/Argentina/Buenos_Aires")
    week_ago = now - pd.Timedelta(days=7)

    summary: list[dict] = []

    for _, patient in patients_df.iterrows():
        patient_id = str(patient["patient_id"])
        imei = str(patient["imei"])

        patient_data = wearable_df[
            (wearable_df["imei"] == imei) &
            (wearable_df["record_datetime"] >= week_ago)
        ]

        # Detect alarms via single source of truth
        alarms = _detect_alarms(patient_id, patient_data)

        # Build per-metric summary for the dashboard table
        metrics_summary: dict = {}
        for metric_key in METRICS:
            metric_alarms = [a for a in alarms if a.metric_key == metric_key]
            metric_data = patient_data[patient_data["metric"] == metric_key]

            if metric_data.empty:
                metrics_summary[metric_key] = {
                    "latest_value": None,
                    "has_alert": False,
                    "alert_type": None,
                }
                continue

            latest_value = metric_data.loc[metric_data["record_datetime"].idxmax()]["value"]
            has_alert = len(metric_alarms) > 0

            alert_type: AlertType | None = None
            display_value = latest_value
            if has_alert:
                types = {a.alert_type for a in metric_alarms}
                if AlertType.LOW in types and AlertType.HIGH in types:
                    alert_type = AlertType.BOTH
                else:
                    alert_type = next(iter(types))
                # Show the most recent alarm value instead of the latest reading
                display_value = metric_alarms[0].value

            metrics_summary[metric_key] = {
                "latest_value": latest_value,
                "display_value": display_value,
                "has_alert": has_alert,
                "alert_type": alert_type,
            }

        # Keep only the most recent alarm per metric for the dashboard cards
        seen_metrics: set[str] = set()
        dashboard_alarms: list[Alarm] = []
        for a in alarms:
            if a.metric_key not in seen_metrics:
                seen_metrics.add(a.metric_key)
                dashboard_alarms.append(a)

        summary.append({
            "patient_id": patient_id,
            "imei": imei,
            "genre": patient.get("genre", ""),
            "alerts": dashboard_alarms,
            "metrics": metrics_summary,
        })

    return summary


def get_patients_with_alerts() -> list[dict]:
    """Get only patients that have active alerts."""
    summary = get_patients_summary()
    return [p for p in summary if p["alerts"]]


def get_patient_alarm_history(
    patient_id: str,
    metric_filter: str | None = None,
    days: int | None = None,
) -> list[Alarm]:
    """Get historical alarms for a patient, sorted by timestamp descending."""
    patients_df, wearable_df = load_all_data()

    patient = patients_df[patients_df["patient_id"] == str(patient_id)]
    if patient.empty:
        return []

    imei = str(patient.iloc[0]["imei"])
    patient_data = wearable_df[wearable_df["imei"] == imei]

    if patient_data.empty:
        return []

    if days is not None:
        cutoff = pd.Timestamp.now(tz="America/Argentina/Buenos_Aires") - pd.Timedelta(days=days)
        patient_data = patient_data[patient_data["record_datetime"] >= cutoff]

    if patient_data.empty:
        return []

    return _detect_alarms(str(patient_id), patient_data, metric_filter)
