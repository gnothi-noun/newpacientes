# Documento de Diseño: GUI Dash para Monitoreo de Pacientes

## 1. Contexto del Proyecto

### 1.1 Estado Actual
- **Ubicación**: `/home/pato/Documents/src/ongoing/ro/Pacientes/`
- **Fuente de datos**: `RA.json` (59 MB)
- **Pacientes**: 25 registrados, 19 con datos de wearables
- **Registros wearable**: 271,632 mediciones
- **Período de datos**: 2025-12-03 al 2026-01-12 (~40 días)

### 1.2 Estructura del JSON

```json
{
  "patients": [
    {
      "patient_id": "519",
      "imei": "863269073647197",
      "genre": "Mujer",
      "date_of_birth": "1934-05-19 00:00:00",
      "hospital_id": "Residencia Asturiana",
      "diabetes_mellitus": 0,
      "charlson_index": null,
      "barthel_index": null
    }
  ],
  "wearabledata": [
    {
      "wearable_data_id": "xxx",
      "imei": "863269073645381",
      "metric": "heart_rate",
      "value": 89.0,
      "record_datetime": "2026-01-10 12:43:06"
    }
  ],
  "perceivedhealthdata": [...],
  "labresults": [],
  "sessionresults": []
}
```

### 1.3 Métricas Disponibles

| Métrica | Descripción | Rango Típico |
|---------|-------------|--------------|
| `heart_rate` | Frecuencia cardíaca | 60-100 bpm |
| `blood_oxygen_saturation` | Saturación de oxígeno | 95-100% |
| `systolic_blood_pressure` | Presión sistólica | 90-140 mmHg |
| `diastolic_blood_pressure` | Presión diastólica | 60-90 mmHg |
| `temperature` | Temperatura corporal | 36-37.5 °C |
| `daily_activity_steps` | Pasos diarios | Variable |

### 1.4 Código Existente

| Archivo | Función | Uso |
|---------|---------|-----|
| `src/database.py` | `load_wearabledata()` | Carga JSON con cache |
| `src/database.py` | `get_data(metric, imei, start, end)` | Filtra datos, calcula media móvil |
| `src/config.py` | `IMEI` dict | Mapeo patient_id → IMEI |
| `src/config.py` | `TimeConfig` | Configuración de zona horaria |

---

## 2. Arquitectura de la GUI

### 2.1 Stack Tecnológico

- **Framework**: Dash 2.14+
- **Componentes UI**: dash-bootstrap-components (tema DARKLY)
- **Gráficos**: Plotly 5.18+
- **Datos**: Pandas con cache

### 2.2 Estructura de Archivos Final

```
Pacientes/
├── app.py                      # Punto de entrada
├── RA.json                     # Datos (existente)
├── DISENO_GUI.md              # Este documento
│
├── src/
│   ├── __init__.py            # Existente
│   ├── config.py              # Modificar: agregar METRICS
│   ├── database.py            # Existente (sin cambios)
│   ├── data_loader.py         # NUEVO: Carga optimizada
│   │
│   └── dash_app/              # NUEVO: Módulo de la GUI
│       ├── __init__.py
│       ├── layout.py          # Definición del layout
│       ├── callbacks.py       # Lógica de interactividad
│       └── figures.py         # Generación de gráficos
│
└── assets/                    # NUEVO: Recursos estáticos
    └── custom.css             # Estilos personalizados
```

---

## 3. Diseño de Interfaz

### 3.1 Layout General

```
┌────────────────────────────────────────────────────────────────┐
│                    MONITOR DE SIGNOS VITALES                    │
├─────────────────────┬──────────────────────────────────────────┤
│   SIDEBAR (300px)   │            ÁREA PRINCIPAL                 │
│                     │                                          │
│ ┌─────────────────┐ │  ┌────────────────────────────────────┐  │
│ │ Paciente:    [▼]│ │  │                                    │  │
│ └─────────────────┘ │  │                                    │  │
│                     │  │         GRÁFICO INTERACTIVO        │  │
│ ┌─────────────────┐ │  │           (Plotly)                 │  │
│ │ INFO PACIENTE   │ │  │                                    │  │
│ │ ID: 519         │ │  │                                    │  │
│ │ Género: Mujer   │ │  │                                    │  │
│ │ Edad: 91 años   │ │  │                                    │  │
│ │ Hospital: R.A.  │ │  └────────────────────────────────────┘  │
│ └─────────────────┘ │                                          │
│                     │  ┌────────────────────────────────────┐  │
│ RANGO DE FECHAS     │  │ ESTADÍSTICAS DEL PERÍODO           │  │
│ Desde: [📅]         │  │ HR:  min=62  max=98  avg=78 bpm    │  │
│ Hasta: [📅]         │  │ SpO2: min=95 max=99  avg=97 %      │  │
│                     │  │ ...                                │  │
│ RANGO HORARIO       │  └────────────────────────────────────┘  │
│ Desde: [08:00 ▼]    │                                          │
│ Hasta: [20:00 ▼]    │                                          │
│                     │                                          │
│ MÉTRICAS            │                                          │
│ ☑ Frec. Cardíaca    │                                          │
│ ☑ Saturación O2     │                                          │
│ ☐ Presión Sistólica │                                          │
│ ☐ Presión Diastól.  │                                          │
│ ☐ Temperatura       │                                          │
│ ☐ Pasos Diarios     │                                          │
│                     │                                          │
│ VISUALIZACIÓN       │                                          │
│ ◉ Superpuesto       │                                          │
│ ○ Subplots          │                                          │
└─────────────────────┴──────────────────────────────────────────┘
```

### 3.2 Componentes UI

| Componente | Tipo Dash | ID | Descripción |
|------------|-----------|-----|-------------|
| Selector paciente | `dcc.Dropdown` | `patient-dropdown` | Lista de patient_id |
| Info paciente | `dbc.Card` | `patient-info-card` | Datos demográficos |
| Fecha inicio | `dcc.DatePickerSingle` | `date-start` | Calendario |
| Fecha fin | `dcc.DatePickerSingle` | `date-end` | Calendario |
| Hora inicio | `dcc.Dropdown` | `time-start` | 00:00 a 23:00 |
| Hora fin | `dcc.Dropdown` | `time-end` | 00:00 a 23:00 |
| Métricas | `dcc.Checklist` | `metrics-checklist` | Selección múltiple |
| Modo vista | `dcc.RadioItems` | `view-mode` | Superpuesto/Subplots |
| Gráfico | `dcc.Graph` | `main-graph` | Plotly interactivo |
| Stats | `html.Div` | `stats-panel` | Min/max/avg por métrica |
| Loading | `dcc.Loading` | `loading` | Spinner durante carga |

---

## 4. Configuración de Métricas

Agregar en `src/config.py`:

```python
METRICS = {
    "heart_rate": {
        "name": "Frecuencia Cardíaca",
        "color": "#FF6B6B",
        "unit": "bpm",
        "normal_min": 60,
        "normal_max": 100
    },
    "blood_oxygen_saturation": {
        "name": "Saturación O2",
        "color": "#4ECDC4",
        "unit": "%",
        "normal_min": 95,
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
        "normal_min": 36.0,
        "normal_max": 37.5
    },
    "daily_activity_steps": {
        "name": "Pasos Diarios",
        "color": "#DDA0DD",
        "unit": "pasos",
        "normal_min": 0,
        "normal_max": None
    }
}
```

---

## 5. Implementación: Pasos a Seguir

### Paso 1: Instalar Dependencias

```bash
pip install dash dash-bootstrap-components plotly
```

### Paso 2: Crear Estructura de Directorios

```bash
mkdir -p src/dash_app assets
touch src/dash_app/__init__.py
touch src/dash_app/layout.py
touch src/dash_app/callbacks.py
touch src/dash_app/figures.py
touch src/data_loader.py
touch assets/custom.css
touch app.py
```

### Paso 3: Implementar `src/data_loader.py`

```python
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
    patient = patients_df[patients_df["patient_id"] == patient_id].iloc[0]
    return patient.to_dict()

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
```

### Paso 4: Implementar `src/dash_app/figures.py`

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.config import METRICS

def create_overlaid_figure(data_dict):
    """Crea figura con métricas superpuestas."""
    fig = go.Figure()

    for metric, df in data_dict.items():
        if df.empty:
            continue
        cfg = METRICS[metric]
        fig.add_trace(go.Scatter(
            x=df["record_datetime"],
            y=df["ma_15m"],
            name=cfg["name"],
            line=dict(color=cfg["color"], width=2),
            hovertemplate=f"{cfg['name']}: %{{y:.1f}} {cfg['unit']}<extra></extra>"
        ))

    fig.update_layout(
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60),
        xaxis_title="Fecha/Hora",
        yaxis_title="Valor"
    )

    return fig

def create_subplot_figure(data_dict):
    """Crea figura con subplots separados."""
    metrics = [m for m, df in data_dict.items() if not df.empty]
    n = len(metrics)

    if n == 0:
        return go.Figure()

    fig = make_subplots(
        rows=n, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[METRICS[m]["name"] for m in metrics]
    )

    for i, metric in enumerate(metrics, 1):
        df = data_dict[metric]
        cfg = METRICS[metric]
        fig.add_trace(
            go.Scatter(
                x=df["record_datetime"],
                y=df["ma_15m"],
                name=cfg["name"],
                line=dict(color=cfg["color"], width=2)
            ),
            row=i, col=1
        )
        fig.update_yaxes(title_text=cfg["unit"], row=i, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=200 * n,
        showlegend=False,
        margin=dict(l=60, r=20, t=40, b=40)
    )

    return fig

def calculate_stats(data_dict):
    """Calcula estadísticas por métrica."""
    stats = []
    for metric, df in data_dict.items():
        if df.empty:
            continue
        cfg = METRICS[metric]
        stats.append({
            "metric": cfg["name"],
            "min": df["value"].min(),
            "max": df["value"].max(),
            "avg": df["value"].mean(),
            "unit": cfg["unit"]
        })
    return stats
```

### Paso 5: Implementar `src/dash_app/layout.py`

```python
from dash import html, dcc
import dash_bootstrap_components as dbc
from src.data_loader import get_patient_list
from src.config import METRICS

def create_layout():
    patients = get_patient_list()
    patient_options = [
        {"label": f"Paciente {row['patient_id']}", "value": row["patient_id"]}
        for _, row in patients.iterrows()
    ]

    metric_options = [
        {"label": cfg["name"], "value": key}
        for key, cfg in METRICS.items()
    ]

    hour_options = [{"label": f"{h:02d}:00", "value": h} for h in range(24)]

    sidebar = dbc.Col([
        html.H5("Filtros", className="mb-3"),

        html.Label("Paciente"),
        dcc.Dropdown(
            id="patient-dropdown",
            options=patient_options,
            value=patient_options[0]["value"] if patient_options else None,
            clearable=False
        ),

        html.Div(id="patient-info-card", className="my-3"),

        html.Hr(),

        html.Label("Fecha Inicio"),
        dcc.DatePickerSingle(id="date-start", display_format="DD/MM/YYYY"),

        html.Label("Fecha Fin", className="mt-2"),
        dcc.DatePickerSingle(id="date-end", display_format="DD/MM/YYYY"),

        html.Hr(),

        html.Label("Hora Inicio"),
        dcc.Dropdown(id="time-start", options=hour_options, value=0),

        html.Label("Hora Fin", className="mt-2"),
        dcc.Dropdown(id="time-end", options=hour_options, value=23),

        html.Hr(),

        html.Label("Métricas"),
        dcc.Checklist(
            id="metrics-checklist",
            options=metric_options,
            value=["heart_rate", "blood_oxygen_saturation"],
            labelStyle={"display": "block"}
        ),

        html.Hr(),

        html.Label("Visualización"),
        dcc.RadioItems(
            id="view-mode",
            options=[
                {"label": "Superpuesto", "value": "overlay"},
                {"label": "Subplots", "value": "subplots"}
            ],
            value="overlay",
            labelStyle={"display": "block"}
        )

    ], width=3, className="bg-dark p-3")

    main_content = dbc.Col([
        dcc.Loading(
            id="loading",
            type="circle",
            children=[
                dcc.Graph(id="main-graph", style={"height": "60vh"}),
                html.Div(id="stats-panel", className="mt-3")
            ]
        )
    ], width=9)

    return dbc.Container([
        html.H2("Monitor de Signos Vitales", className="text-center my-3"),
        dbc.Row([sidebar, main_content])
    ], fluid=True)
```

### Paso 6: Implementar `src/dash_app/callbacks.py`

```python
from dash import callback, Output, Input, html
import dash_bootstrap_components as dbc
from datetime import datetime
from src.data_loader import get_patient_info, get_filtered_data, load_all_data
from src.dash_app.figures import create_overlaid_figure, create_subplot_figure, calculate_stats
from src.config import METRICS

def register_callbacks(app):

    @app.callback(
        Output("patient-info-card", "children"),
        Output("date-start", "min_date_allowed"),
        Output("date-start", "max_date_allowed"),
        Output("date-start", "date"),
        Output("date-end", "min_date_allowed"),
        Output("date-end", "max_date_allowed"),
        Output("date-end", "date"),
        Input("patient-dropdown", "value")
    )
    def update_patient_info(patient_id):
        if not patient_id:
            return html.Div(), None, None, None, None, None, None

        info = get_patient_info(patient_id)

        # Calcular edad
        dob = datetime.strptime(info["date_of_birth"], "%Y-%m-%d %H:%M:%S")
        age = (datetime.now() - dob).days // 365

        card = dbc.Card([
            dbc.CardBody([
                html.P(f"ID: {info['patient_id']}"),
                html.P(f"Género: {info['genre'] or 'N/D'}"),
                html.P(f"Edad: {age} años"),
                html.P(f"Hospital: {info['hospital_id']}")
            ])
        ], className="bg-secondary")

        # Obtener rango de fechas disponible
        _, wearable_df = load_all_data()
        patient_data = wearable_df[wearable_df["imei"] == info["imei"]]

        if patient_data.empty:
            return card, None, None, None, None, None, None

        min_date = patient_data["record_datetime"].min().date()
        max_date = patient_data["record_datetime"].max().date()

        return card, min_date, max_date, min_date, min_date, max_date, max_date

    @app.callback(
        Output("main-graph", "figure"),
        Output("stats-panel", "children"),
        Input("patient-dropdown", "value"),
        Input("date-start", "date"),
        Input("date-end", "date"),
        Input("time-start", "value"),
        Input("time-end", "value"),
        Input("metrics-checklist", "value"),
        Input("view-mode", "value")
    )
    def update_graph(patient_id, date_start, date_end, time_start, time_end, metrics, view_mode):
        if not patient_id or not date_start or not date_end or not metrics:
            return {}, html.Div("Selecciona paciente, fechas y métricas")

        info = get_patient_info(patient_id)
        imei = info["imei"]

        # Obtener datos para cada métrica
        data_dict = {}
        for metric in metrics:
            df = get_filtered_data(imei, metric, date_start, date_end, time_start, time_end)
            data_dict[metric] = df

        # Generar figura según modo
        if view_mode == "overlay":
            fig = create_overlaid_figure(data_dict)
        else:
            fig = create_subplot_figure(data_dict)

        # Calcular estadísticas
        stats = calculate_stats(data_dict)
        stats_content = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(s["metric"]),
                        html.P(f"Min: {s['min']:.1f} {s['unit']}"),
                        html.P(f"Max: {s['max']:.1f} {s['unit']}"),
                        html.P(f"Prom: {s['avg']:.1f} {s['unit']}")
                    ])
                ], className="bg-secondary")
            ], width=2) for s in stats
        ])

        return fig, stats_content
```

### Paso 7: Implementar `app.py`

```python
from dash import Dash
import dash_bootstrap_components as dbc
from src.dash_app.layout import create_layout
from src.dash_app.callbacks import register_callbacks
from src.data_loader import load_all_data

# Pre-cargar datos
print("Cargando datos...")
load_all_data()
print("Datos cargados.")

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    suppress_callback_exceptions=True
)

app.layout = create_layout()
register_callbacks(app)

if __name__ == "__main__":
    app.run(debug=True, port=8050)
```

### Paso 8: Modificar `src/config.py`

Agregar la configuración de `METRICS` (ver sección 4).

### Paso 9: CSS Opcional (`assets/custom.css`)

```css
.Select-control {
    background-color: #303030 !important;
}

.card {
    border: 1px solid #444;
}

.checklist-label {
    margin-left: 8px;
}
```

---

## 6. Verificación

1. **Ejecutar la app**:
   ```bash
   python app.py
   ```

2. **Abrir navegador**: http://localhost:8050

3. **Probar funcionalidad**:
   - [ ] Cambiar paciente → info y fechas se actualizan
   - [ ] Cambiar rango de fechas → gráfico se actualiza
   - [ ] Filtrar por horario → solo muestra datos de esas horas
   - [ ] Activar/desactivar métricas → gráfico cambia
   - [ ] Cambiar modo vista → superpuesto vs subplots
   - [ ] Hover sobre gráfico → muestra valores
   - [ ] Zoom/pan en gráfico → Plotly interactivo

---

## 7. Consideraciones de Performance

| Problema | Solución |
|----------|----------|
| JSON de 59MB tarda en cargar | `@lru_cache` carga una vez al inicio |
| Muchos puntos ralentizan Plotly | Media móvil reduce ruido visual |
| Filtros lentos | Filtrado vectorizado con Pandas |

Para datasets más grandes, considerar:
- Convertir a Parquet (5-10x más rápido)
- Downsampling a intervalos fijos para visualización
- Paginación de datos

---

## 8. Extensiones Futuras

1. **Exportar CSV**: Botón para descargar datos filtrados
2. **Alertas**: Resaltar valores fuera de rango normal
3. **Comparación**: Vista multi-paciente
4. **Historial clínico**: Integrar `perceivedhealthdata` del JSON
5. **Anotaciones**: Marcar eventos en el gráfico
