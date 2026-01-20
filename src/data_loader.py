import json
from functools import lru_cache
import pandas as pd

JSON_PATH = "RA.json"


@lru_cache(maxsize=1)
def load_all_data():
    """Carga datos una sola vez y los mantiene en memoria."""
    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    patients_df = pd.DataFrame(data["patients"])
    wearable_df = pd.DataFrame(data["wearabledata"])

    # Pre-procesar tipos
    wearable_df["record_datetime"] = pd.to_datetime(wearable_df["record_datetime"])
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


def get_filtered_data(imei, metric, date_start, date_end, time_start=None, time_end=None):
    """Filtra datos por IMEI, métrica, fechas y opcionalmente horario."""
    _, wearable_df = load_all_data()

    mask = (
        (wearable_df["imei"] == str(imei)) &
        (wearable_df["metric"] == metric) &
        (wearable_df["record_datetime"] >= pd.to_datetime(date_start)) &
        (wearable_df["record_datetime"] <= pd.to_datetime(date_end))
    )

    df = wearable_df[mask].copy()

    # Filtro por horario si se especifica
    if time_start is not None and time_end is not None:
        hour_mask = (
            (df["record_datetime"].dt.hour >= time_start) &
            (df["record_datetime"].dt.hour <= time_end)
        )
        df = df[hour_mask]

    df = df.sort_values("record_datetime")
    df["ma_15m"] = df["value"].rolling(3, min_periods=1, center=True).mean()

    return df[["record_datetime", "value", "ma_15m"]]
