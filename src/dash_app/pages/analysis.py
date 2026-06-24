"""Página de Análisis: línea base personalizada + tendencias (alerta temprana)."""
from dash import html, dcc
import dash_bootstrap_components as dbc

from src.config import METRICS, ANALYSIS_METRICS
from src.data_loader import get_patient_list
from src.dash_app.figures import trend_badge


# Etiquetas cortas para la tabla de cohorte.
_SHORT = {
    "heart_rate": "FC",
    "blood_oxygen_saturation": "SpO2",
    "temperature": "Temp",
}


def create_cohort_table(rows: list[dict]):
    """Tabla de triage: pacientes con tendencia adversa ('a quién mirar hoy')."""
    if not rows:
        return dbc.Alert(
            "Ningún paciente con tendencia adversa en las últimas semanas.",
            color="success", className="text-center"
        )

    header = html.Thead(html.Tr(
        [html.Th("Paciente", className="text-center"), html.Th("Género", className="text-center")]
        + [html.Th(_SHORT[m], className="text-center") for m in ANALYSIS_METRICS]
        + [html.Th("Métricas en alerta", className="text-center")]
    ))

    body_rows = []
    for r in rows:
        cells = [
            html.Td(r["patient_id"], className="align-middle text-center"),
            html.Td(r.get("genre", "-") or "-", className="align-middle text-center"),
        ]
        for m in ANALYSIS_METRICS:
            arrow, color = trend_badge(r["trends"][m])
            cells.append(html.Td(
                html.Span(arrow, style={"color": color, "fontWeight": "bold", "fontSize": "1.2rem"}),
                className="align-middle text-center",
            ))
        cells.append(html.Td(
            dbc.Badge(str(len(r["adverse_metrics"])), color="danger"),
            className="align-middle text-center",
        ))
        body_rows.append(html.Tr(cells))

    return dbc.Table([header, html.Tbody(body_rows)],
                     bordered=True, hover=True, responsive=True, size="sm",
                     className="table-dark", style={"width": "auto"})


def create_analysis_layout(selected_patient_id=None):
    """Layout de la página de análisis (sidebar de filtros + contenido).

    El selector arranca vacío a propósito: el usuario elige el paciente
    (no hereda el último visto en otras páginas).
    """
    patients = get_patient_list()
    patient_options = [
        {"label": f"Paciente {row['patient_id']}", "value": row["patient_id"]}
        for _, row in patients.iterrows()
    ]

    metric_options = [{"label": METRICS[m]["name"], "value": m} for m in ANALYSIS_METRICS]

    sidebar = dbc.Col([
        html.H5("Análisis", className="mb-3"),

        html.Label("Paciente"),
        dcc.Dropdown(
            id="analysis-patient-dropdown",
            options=patient_options,
            value=None,
            placeholder="Elegí un paciente",
            clearable=False,
            style={"backgroundColor": "#ff8a65", "color": "white"},
        ),

        html.Hr(),

        html.Label("Métricas"),
        dcc.Checklist(
            id="analysis-metrics-checklist",
            options=metric_options,
            value=list(ANALYSIS_METRICS),
            labelStyle={"display": "block", "marginBottom": "5px"},
        ),

        html.Hr(),
        html.Small(
            "La banda muestra el rango usual del paciente (sus propios percentiles "
            "p10–p90 por franja horaria). Los puntos en naranja se salen de SU patrón. "
            "Las tendencias evalúan deterioro sostenido en las últimas semanas.",
            className="text-muted",
        ),
    ], width=3, className="bg-dark p-3", style={"height": "calc(100vh - 56px)", "overflowY": "auto"})

    main_content = dbc.Col([
        html.H5("A quién mirar hoy (tendencias adversas)", className="mb-2"),
        html.Div(id="analysis-cohort-table", className="mb-4"),
        html.Hr(),
        dcc.Loading(type="circle", children=[
            html.H5("Línea base personalizada", className="mb-2"),
            html.Div(id="analysis-baseline-container"),
            html.H5("Tendencias semanales", className="mt-3 mb-2"),
            html.Div(id="analysis-trend-panel"),
        ]),
    ], width=9, className="p-3")

    return dbc.Container([
        dbc.Row([sidebar, main_content])
    ], fluid=True, className="bg-dark", style={"minHeight": "calc(100vh - 56px)"})
