import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def load_patient_data(patient_id: str) -> pd.DataFrame:
    # TODO: adaptá a tu fuente real (CSV, DB, API, parquet, etc.)
    df = pd.read_csv(f"data/{patient_id}.csv")

    # Normalizá timestamps
    df["record_datetime"] = pd.to_datetime(df["record_datetime"], utc=True).dt.tz_convert("America/Argentina/Buenos_Aires")
    df = df.sort_values("record_datetime")

    return df
