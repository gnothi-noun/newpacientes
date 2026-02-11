import json
from functools import lru_cache
from datetime import datetime, timedelta
import pandas as pd
import math
from src.config import METRICS

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


def get_patient_list():
    """Retorna lista de pacientes para el dropdown."""
    patients_df, _ = load_all_data()
    return patients_df[["patient_id", "imei", "genre", "date_of_birth", "hospital_id"]]


def get_patient_info(patient_id):
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


def get_patients_summary():
    """Get summary of all patients with their latest values and alert status."""
    patients_df, wearable_df = load_all_data()

    # Time window: last 7 days
    now = pd.Timestamp.now(tz="America/Argentina/Buenos_Aires")
    week_ago = now - pd.Timedelta(days=7)

    summary = []

    for _, patient in patients_df.iterrows():
        patient_id = patient["patient_id"]
        imei = str(patient["imei"])

        # Get data for this patient in the last 7 days
        patient_data = wearable_df[
            (wearable_df["imei"] == imei) &
            (wearable_df["record_datetime"] >= week_ago)
        ]

        patient_summary = {
            "patient_id": patient_id,
            "imei": imei,
            "genre": patient.get("genre", ""),
            "alerts": [],
            "metrics": {}
        }

        # Check each metric
        for metric_key, metric_cfg in METRICS.items():
            metric_data = patient_data[patient_data["metric"] == metric_key]

            if metric_data.empty:
                patient_summary["metrics"][metric_key] = {
                    "latest_value": None,
                    "has_alert": False,
                    "alert_type": None
                }
                continue

            # Get latest value
            latest_row = metric_data.loc[metric_data["record_datetime"].idxmax()]
            latest_value = latest_row["value"]

            # Check for alerts (values outside normal range)
            normal_min = metric_cfg.get("normal_min")
            normal_max = metric_cfg.get("normal_max")

            has_alert = False
            alert_type = None
            alert_value = None

            if normal_min is not None and normal_max is not None:
                # Find any values outside normal range in the last week
                low_alerts = metric_data[metric_data["value"] < normal_min]
                high_alerts = metric_data[metric_data["value"] > normal_max]

                if not low_alerts.empty:
                    has_alert = True
                    alert_type = "low"
                    # Get the most recent low alert value
                    alert_value = low_alerts.loc[low_alerts["record_datetime"].idxmax()]["value"]

                if not high_alerts.empty:
                    has_alert = True
                    alert_type = "high" if alert_type is None else "both"
                    # Get the most recent high alert value
                    high_val = high_alerts.loc[high_alerts["record_datetime"].idxmax()]["value"]
                    if alert_value is None or high_alerts["record_datetime"].max() > low_alerts["record_datetime"].max():
                        alert_value = high_val

            patient_summary["metrics"][metric_key] = {
                "latest_value": latest_value,
                "has_alert": has_alert,
                "alert_type": alert_type,
                "alert_value": alert_value
            }

            if has_alert:
                patient_summary["alerts"].append({
                    "metric": metric_key,
                    "metric_name": metric_cfg["name"],
                    "value": alert_value,
                    "unit": metric_cfg["unit"],
                    "type": alert_type,
                    "color": metric_cfg["color"]
                })

        summary.append(patient_summary)

    return summary


def get_patients_with_alerts():
    """Get only patients that have active alerts."""
    summary = get_patients_summary()
    return [p for p in summary if len(p["alerts"]) > 0]
