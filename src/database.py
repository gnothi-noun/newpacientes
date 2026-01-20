import json
from functools import cache
import pandas as pd
import matplotlib.pyplot as plt

JSON_PATH = "RA.json"

@cache
def load_wearabledata():
    with open(JSON_PATH, "r") as f:
        data = json.load(f)
    return pd.DataFrame(data["wearabledata"])

def get_data(metric, select_imei, date_strt, date_nd):
    df = load_wearabledata()

    df["record_datetime"] = pd.to_datetime(df["record_datetime"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["imei"] = df["imei"].astype(str)
    select_imei = str(select_imei)

    date_strt = pd.to_datetime(date_strt)
    date_nd = pd.to_datetime(date_nd)

    data = df[
        (df["metric"] == metric) &
        (df["imei"] == select_imei) &
        (df["record_datetime"] >= date_strt) &
        (df["record_datetime"] <= date_nd)
    ][["record_datetime", "value"]].copy()

    data = data.sort_values("record_datetime")
    data = data.dropna(subset=["record_datetime", "value"])
    data["ma_15m"] = data["value"].rolling(3, min_periods=1, center=True).mean()
    return data

def show_dpressure (d_pressure):
    plt.style.use("dark_background")
    plt.figure()
    plt.plot(d_pressure["record_datetime"], d_pressure["ma_15m"], color="blue")
    plt.xlabel("Time", color="white")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Diastolic Blood Pressure", color="white")
    plt.title("Diastolic Blood Pressure vs Time", color="white")
    plt.grid(True, color="gray") 

def show_hrate (heart_rate):
    plt.style.use("dark_background")
    plt.figure()
    plt.plot(heart_rate["record_datetime"], heart_rate["ma_15m"], color="red")
    plt.xlabel("Time", color="white")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Heart Rate", color="white")
    plt.title("Heart Rate vs Time", color="white")
    plt.grid(True, color="gray") 

def show_oxsat (ox_sat):
    plt.style.use("dark_background")
    plt.figure()
    plt.plot(ox_sat["record_datetime"], ox_sat["ma_15m"], color="yellow")
    plt.xlabel("Time", color="white")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Blood Oxygen Saturation", color="white")
    plt.title("Blood Oxygen Saturation vs Time", color="white")
    plt.grid(True, color="gray") 

def show_temperature (temperature):
    plt.style.use("dark_background")
    plt.figure()
    plt.plot(temperature["record_datetime"], temperature["ma_15m"], color="orange")
    plt.xlabel("Time", color="white")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Temperature", color="white")
    plt.title("Temperature vs Time", color="white")
    plt.grid(True, color="gray") 
    
