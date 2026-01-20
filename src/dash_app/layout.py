from dash import html, dcc
import dash_bootstrap_components as dbc
import sys
sys.path.insert(0, "/home/pato/Documents/src/ongoing/ro/Pacientes")
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
        dcc.Dropdown(id="time-start", options=hour_options, value=0, clearable=False),

        html.Label("Hora Fin", className="mt-2"),
        dcc.Dropdown(id="time-end", options=hour_options, value=23, clearable=False),

        html.Hr(),

        html.Label("Métricas"),
        dcc.Checklist(
            id="metrics-checklist",
            options=metric_options,
            value=["heart_rate", "blood_oxygen_saturation"],
            labelStyle={"display": "block", "marginBottom": "5px"}
        ),

        html.Hr(),

        html.Label("Visualización"),
        dcc.RadioItems(
            id="view-mode",
            options=[
                {"label": " Superpuesto", "value": "overlay"},
                {"label": " Subplots", "value": "subplots"}
            ],
            value="overlay",
            labelStyle={"display": "block", "marginBottom": "5px"}
        )

    ], width=3, className="bg-dark p-3", style={"height": "100vh", "overflowY": "auto"})

    main_content = dbc.Col([
        dcc.Loading(
            id="loading",
            type="circle",
            children=[
                dcc.Graph(id="main-graph", style={"height": "65vh"}),
                html.Div(id="stats-panel", className="mt-3")
            ]
        )
    ], width=9, className="p-3")

    return dbc.Container([
        html.H2("Monitor de Signos Vitales", className="text-center my-3"),
        dbc.Row([sidebar, main_content])
    ], fluid=True, className="bg-dark", style={"minHeight": "100vh"})
