"""Convierte RA.json -> Parquet para desplegar en la Raspberry Pi.

Por qué: cargar el RA.json de ~444 MB con json.load + pandas consume varios GB
de RAM (imposible en una Raspberry Pi de 2 GB). Este script hace el trabajo
pesado en la máquina de desarrollo (con RAM de sobra) y deja dos archivos
Parquet ya procesados y livianos:

    RA_patients.parquet   (lista de pacientes)
    RA_wearable.parquet   (serie temporal, solo columnas usadas)

Esos archivos se copian a la Raspberry, donde la app los lee con
pandas.read_parquet de forma rápida y con poca memoria.

Uso (en la PC de desarrollo, con el entorno del proyecto activado):

    python convert_to_parquet.py

Opcional: rutas de entrada/salida por variables de entorno
VITAICARE_JSON, VITAICARE_PATIENTS_PARQUET, VITAICARE_WEARABLE_PARQUET.
"""
from __future__ import annotations

import json

from src.data_loader import (
    JSON_PATH,
    PARQUET_PATIENTS,
    PARQUET_WEARABLE,
    build_dataframes,
)


def main() -> None:
    print(f"Leyendo {JSON_PATH} ...")
    with open(JSON_PATH, "r") as f:
        data = json.load(f)

    print("Construyendo DataFrames (procesando tipos y zona horaria) ...")
    patients_df, wearable_df = build_dataframes(data)

    print(f"  pacientes: {len(patients_df):,} filas")
    print(f"  wearable : {len(wearable_df):,} filas")

    print(f"Escribiendo {PARQUET_PATIENTS} ...")
    patients_df.to_parquet(PARQUET_PATIENTS, index=False, compression="snappy")

    print(f"Escribiendo {PARQUET_WEARABLE} ...")
    wearable_df.to_parquet(PARQUET_WEARABLE, index=False, compression="snappy")

    print("Listo. Copiá los dos archivos .parquet a la Raspberry Pi.")


if __name__ == "__main__":
    main()
