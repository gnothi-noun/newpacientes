import json
from functools import lru_cache
import pandas as pd
import math

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

    # Convertir fechas a timezone-aware (Argentina) para comparar correctamente
    date_start_tz = pd.to_datetime(date_start).tz_localize("America/Argentina/Buenos_Aires")
    date_end_tz = pd.to_datetime(date_end).tz_localize("America/Argentina/Buenos_Aires") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    mask = ( # Selecciono el imei, la metrica y el rango de tiempo en dias que coincida
             # con lo que ingresa el usuario

        (wearable_df["imei"] == str(imei)) &
        (wearable_df["metric"] == metric) &
        (wearable_df["record_datetime"] >= date_start_tz) &
        (wearable_df["record_datetime"] <= date_end_tz)
    )

    df:pd.DataFrame = wearable_df[mask].copy()  # paso la mascara por todos los valores de todas
                                                # las metricas

    # Filtro por horario si se especifica
    if time_start is not None and time_end is not None:
        hour_mask = (
            (df["record_datetime"].dt.hour >= time_start) &
            (df["record_datetime"].dt.hour <= time_end)
        )
        df = df[hour_mask] # paso mascara de horas por el dataframe 
                           # que ya esta filtrado por todo lo demas

    df = df.sort_values("record_datetime").reset_index(drop=True) #Ordena segun fecha
    
    # Filtro: Detectar gaps mayores a 15 minutos entre datos consecutivos
    # Donde haya un gap > 15 min, se inserta NaN para romper la línea en el gráfico
    # Aplicar filtro de gaps: insertar NaN donde hay más de 15 minutos entre datos
    GAP_THRESHOLD_MINUTES = 15
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
