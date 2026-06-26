"""Patient Monitor page - Individual patient vital signs monitoring."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from src.data_loader import get_patient_list
from src.config import METRICS


def create_patient_monitor_layout(selected_patient_id=None):
    """Create the patient monitor layout with filters and graph."""
    patients = get_patient_list()
    patient_options = [
        {"label": f"Paciente {row['patient_id']}", "value": row["patient_id"]}
        for _, row in patients.iterrows()
    ]

    # Solo preselecciona si se navegó a un paciente puntual (alarma/fila);
    # si no hay paciente (p. ej. desde "Monitor Paciente"), el dropdown va vacío.
    default_patient = selected_patient_id

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
            value=default_patient,
            placeholder="Buscá un paciente…",
            clearable=False,
            style={
                "backgroundColor": "#ff8a65",
                "color": "white"
            }
        ),

        html.Div(id="patient-info-card", className="my-3"),

        html.Hr(),

        dbc.Row([
            dbc.Col([
                html.Label("Fecha Inicio", className="small mb-1 d-block"),
                dcc.DatePickerSingle(id="date-start", display_format="DD/MM/YYYY"),
            ], width=6),
            dbc.Col([
                html.Label("Fecha Fin", className="small mb-1 d-block"),
                dcc.DatePickerSingle(id="date-end", display_format="DD/MM/YYYY"),
            ], width=6),
        ], className="g-2"),

        html.Hr(),

        dbc.Row([
            dbc.Col([
                html.Label("Hora Inicio", className="small mb-1"),
                dcc.Dropdown(
                    id="time-start", options=hour_options, value=0, clearable=False,
                    style={"backgroundColor": "#6f6f6f", "color": "white", "fontSize": "13px"},
                ),
            ], width=6),
            dbc.Col([
                html.Label("Hora Fin", className="small mb-1"),
                dcc.Dropdown(
                    id="time-end", options=hour_options, value=23, clearable=False,
                    style={"backgroundColor": "#6f6f6f", "color": "white", "fontSize": "13px"},
                ),
            ], width=6),
        ], className="g-2"),

        html.Hr(),

        html.Label("Metricas"),
        dcc.Checklist(
            id="metrics-checklist",
            options=metric_options,
            value=["heart_rate", "blood_oxygen_saturation"],
            labelStyle={"display": "block", "marginBottom": "5px"}
        ),

        html.Hr(),

        html.Label("Visualizacion"),
        dcc.RadioItems(
            id="view-mode",
            options=[
                {"label": " Superpuesto", "value": "overlay"},
                {"label": " Subplots", "value": "subplots"}
            ],
            value="overlay",
            labelStyle={"display": "block", "marginBottom": "5px"}
        ),

        html.Hr(),

        html.Label("Descargar informe"),
        dcc.RadioItems(
            id="report-format-monitor",
            options=[
                {"label": " PDF", "value": "pdf"},
                {"label": " CSV", "value": "csv"},
            ],
            value="pdf",
            labelStyle={"display": "inline-block", "marginRight": "12px"}
        ),
        dbc.Button("Descargar", id="download-report-monitor-btn", color="info",
                   className="w-100 mt-2", n_clicks=0),
        dcc.Download(id="download-report-monitor")

    ], width=3, className="bg-dark p-3", style={"height": "calc(100vh - 56px)", "overflowY": "auto"})

    main_content = dbc.Col([
        # Tarjetas de estadística + botón de análisis a la derecha de la última.
        html.Div([
            html.Div(id="stats-panel"),
            html.Div([
                dbc.Button("Tendencias y patrones", id="deep-analysis-btn",
                           color="primary", n_clicks=0),
                # Posicionado absoluto: aparece sin empujar las tarjetas.
                html.Div("Deslizá hacia abajo ⬇", id="deep-analysis-hint",
                         className="scroll-hint", style={"display": "none"}),
            ], className="ms-3 flex-shrink-0 align-self-start position-relative"),
        ], className="d-flex align-items-start mb-3"),
        dcc.Loading(
            id="loading",
            type="circle",
            children=[
                dcc.Graph(id="main-graph", config={"responsive": True}, className="mb-2"),
            ]
        ),

        # Sección de Análisis (se abre/cierra con el botón "Análisis" del panel lateral).
        dbc.Collapse(
            dcc.Loading(type="circle", children=html.Div(id="deep-analysis-content")),
            id="deep-analysis-collapse",
            is_open=False,
        ),
    ], width=9, className="p-3")

    return dbc.Container([
        dbc.Row([sidebar, main_content])
    ], fluid=True, className="bg-dark", style={"minHeight": "calc(100vh - 56px)"})
