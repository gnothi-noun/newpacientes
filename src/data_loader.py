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


def get_filtered_data(imei: str, metric: str, date_start, date_end, time_start=None, time_end=None):
    """Filtra datos por IMEI, métrica, fechas y opcionalmente horario."""
    print("estoy filtrando lokooo")
    _, wearable_df = load_all_data() # me quedo solo con los valores de todas las metricas. 
                                     # Desestimo la lista de pacientes.

    mask = ( # Selecciono el imei, la metrica y el rango de tiempo en dias que coincida
             # con lo que ingresa el usuario
        
        (wearable_df["imei"] == str(imei)) &
        (wearable_df["metric"] == metric) &
        (wearable_df["record_datetime"] >= pd.to_datetime(date_start)) &
        (wearable_df["record_datetime"] <= pd.to_datetime(date_end))
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
    if len(df) > 1: #si hay al menos una medicion, entra al if 
        time_diffs = df["record_datetime"].diff() #diferencia entre uno y el anterior. Primero NaN
        print("Diferencia de tiempo:", time_diffs)
        gap_threshold = pd.Timedelta(minutes=GAP_THRESHOLD_MINUTES)
        gaps = time_diffs > gap_threshold
        print("Indx de tiempo mayor a 15min:", gaps)

        if gaps.any(): #gaps recorre toda la serie, si hay ANY que cumpla, entra
            # Crear todas las filas de gap con los dtypes correctos
            print("KE TE PASA", len(df[gaps].index))
            gap_rows = [] #creo una lista
            for idx in df[gaps].index: #le paso la lista de true y false a df para quedarme con los true
                gap_rows.append({# va a iterar sobre cada indice de gaps
                    "record_datetime": pd.to_datetime(df.loc[idx]["record_datetime"] - pd.Timedelta(seconds=1)),
                    "value": float('nan')  # Usar float('nan') para compatibilidad con dtype numérico
                })

            # Crear DataFrame de gaps con dtypes explícitos
            
            gap_df = pd.DataFrame(gap_rows)
            # gap_df["record_datetime"] = pd.to_datetime(gap_df["record_datetime"])
            # gap_df["value"] = gap_df["value"].astype(float)

            # Concatenar y reordenar
            df = pd.concat([df, gap_df], ignore_index=True)
            df = df.sort_values("record_datetime").reset_index(drop=True)

    df["ma_15m"] = df["value"].rolling(3, min_periods=1, center=True).mean()

    return df[["record_datetime", "value", "ma_15m"]]
