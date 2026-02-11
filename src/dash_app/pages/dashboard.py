"""Dashboard page - Overview of all patients with alerts."""
from dash import html, dcc
import dash_bootstrap_components as dbc
from src.data_loader import get_patients_summary, get_patients_with_alerts
from src.config import METRICS


def create_alert_card(patient):
    """Create an alert card for a patient with alerts."""
    alerts = patient["alerts"]
    if not alerts:
        return None

    # Get the most critical alert (first one)
    main_alert = alerts[0]

    return dbc.Card([
        dbc.CardHeader([
            html.H5(f"Paciente {patient['patient_id']}", className="mb-0 text-white")
        ], className="bg-danger"),
        dbc.CardBody([
            html.Div([
                html.Span(f"{main_alert['value']:.1f}", className="display-6 text-danger"),
                html.Span(f" {main_alert['unit']}", className="text-muted")
            ]),
            html.P(main_alert['metric_name'], className="mb-1"),
            html.Small(
                f"{'Bajo' if main_alert['type'] == 'low' else 'Alto'} - Fuera de rango normal",
                className="text-muted"
            ),
            html.Hr(className="my-2"),
            html.Small(f"{len(alerts)} alerta(s) activa(s)", className="text-warning")
        ])
    ], className="h-100", style={"cursor": "pointer"}, id={"type": "alert-card", "patient_id": patient["patient_id"]})


def create_patient_row(patient):
    """Create a table row for a patient."""
    cells = [
        html.Td(patient["patient_id"], className="align-middle"),
        html.Td(patient.get("genre", "-"), className="align-middle"),
    ]

    # Add metric cells
    metric_keys = ["heart_rate", "blood_oxygen_saturation", "temperature", "systolic_blood_pressure"]
    for metric_key in metric_keys:
        metric_info = patient["metrics"].get(metric_key, {})
        value = metric_info.get("latest_value")
        has_alert = metric_info.get("has_alert", False)

        if value is not None:
            unit = METRICS[metric_key]["unit"]
            cell_class = "text-danger fw-bold" if has_alert else ""
            cell_content = f"{value:.1f} {unit}"
        else:
            cell_class = "text-muted"
            cell_content = "-"

        cells.append(html.Td(cell_content, className=f"align-middle {cell_class}"))

    # Alert indicator
    alert_count = len(patient["alerts"])
    if alert_count > 0:
        status = html.Span(
            f"{alert_count} alerta(s)",
            className="badge bg-danger"
        )
    else:
        status = html.Span("OK", className="badge bg-success")

    cells.append(html.Td(status, className="align-middle text-center"))

    return html.Tr(cells, id={"type": "patient-row", "patient_id": patient["patient_id"]}, style={"cursor": "pointer"})


def create_dashboard_layout():
    """Create the main dashboard layout."""
    return dbc.Container([
        # Alerts Section
        html.Div(id="alerts-section", className="mb-4"),

        # Summary Table Section
        html.Div([
            html.H4("Resumen de Pacientes", className="mb-3"),
            html.Div(id="patients-table-container")
        ])
    ], fluid=True, className="p-4", style={"minHeight": "calc(100vh - 56px)"})


def create_alerts_panel(patients_with_alerts):
    """Create the alerts panel with patient cards."""
    if not patients_with_alerts:
        return dbc.Alert(
            "No hay alertas activas en los ultimos 7 dias",
            color="success",
            className="text-center"
        )

    alert_cards = []
    for patient in patients_with_alerts[:6]:  # Show max 6 alerts
        card = create_alert_card(patient)
        if card:
            alert_cards.append(dbc.Col(card, width=12, md=6, lg=4, xl=2, className="mb-3"))

    return html.Div([
        html.H4([
            html.Span("Alertas Activas ", className="text-danger"),
            dbc.Badge(f"{len(patients_with_alerts)}", color="danger", className="ms-2")
        ], className="mb-3"),
        dbc.Row(alert_cards)
    ])


def create_patients_table(all_patients):
    """Create the summary table for all patients."""
    rows = [create_patient_row(p) for p in all_patients]

    return dbc.Table([
        html.Thead(html.Tr([
            html.Th("ID", className="text-center"),
            html.Th("Genero", className="text-center"),
            html.Th("FC (bpm)", className="text-center"),
            html.Th("SpO2 (%)", className="text-center"),
            html.Th("Temp (C)", className="text-center"),
            html.Th("PA Sist.", className="text-center"),
            html.Th("Estado", className="text-center"),
        ])),
        html.Tbody(rows)
    ], bordered=True, hover=True, responsive=True, className="table-dark")
