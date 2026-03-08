import pandas as pd
import matplotlib.pyplot as plt
from dataclasses import dataclass

user = "root"
password = "Mysqlpassword?"
host = "localhost"
port = 3306
db = "test1"

@dataclass(frozen=True)
class TimeConfig:
    sample_period_minutes: int = 5
    gap_threshold_minutes: int = 5  # para marcar "hueco" si supera esto
    tz: str = "America/Argentina/Buenos_Aires"
CFG = TimeConfig()

IMEI: dict[str, int] = {
    "614": 863269073649284,
    "561": 863269073647767,
    "554": 863269073647114,
    "578": 863269073645456,
    "620": 863269073646231,
    "609": 863269073646751,
    "623": 863269073648500,
    "587": 863269073640340,
    "565": 863269073645381,
    "593": 863269073648880,
    "603": 863269073647759,
    "616": 863269073649300,
    "456": 863269073649599,
    "519": 863269073647197,
    "545": 863269073648534,
    "602": 863269073646793,
    "557": 863269073647056,
    "621": 863269073647098,
    "600": 863269073646769,
    "610": 863269073647163,
    "G": 863269073647387,
    "L": 863269073648211,
    "R": 863269073648179,
}

METRICS = {
    "heart_rate": {
        "name": "Frecuencia Cardíaca",
        "color": "#FF6B6B",
        "unit": "bpm",
        "normal_min": 50,
        "normal_max": 120
    },
    "blood_oxygen_saturation": {
        "name": "Saturación O2",
        "color": "#4ECDC4",
        "unit": "%",
        "normal_min": 70,
        "normal_max": 100
    },
    "systolic_blood_pressure": {
        "name": "Presión Sistólica",
        "color": "#45B7D1",
        "unit": "mmHg",
        "normal_min": 90,
        "normal_max": 140
    },
    "diastolic_blood_pressure": {
        "name": "Presión Diastólica",
        "color": "#96CEB4",
        "unit": "mmHg",
        "normal_min": 60,
        "normal_max": 90
    },
    "temperature": {
        "name": "Temperatura",
        "color": "#FFEAA7",
        "unit": "°C",
        "normal_min": 30.0,
        "normal_max": 38.0
    },
    "daily_activity_steps": {
        "name": "Pasos Diarios",
        "color": "#DDA0DD",
        "unit": "pasos",
        "normal_min": 0,
        "normal_max": None
    }
}

