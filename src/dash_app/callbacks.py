from dash import callback, Output, Input, State, html, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from src.data_loader import (
    get_patient_info, get_filtered_data, load_all_data,
    get_patients_summary, get_patients_with_alerts
)
from src.dash_app.figures import create_overlaid_figure, create_subplot_figure, calculate_stats
from src.dash_app.pages.patient_monitor import create_patient_monitor_layout
from src.dash_app.pages.dashboard import (
    create_dashboard_layout, create_alerts_panel, create_patients_table
)


def register_callbacks(app):

    # ==================== ROUTING ====================
    @app.callback(
        Output('page-content', 'children'),
        Input('url', 'pathname'),
        State('selected-patient-store', 'data')
    )
    def display_page(pathname, stored_patient_id):
        if pathname == '/patient':
            return create_patient_monitor_layout(stored_patient_id)
        else:  # "/" or any other path -> Dashboard
            return create_dashboard_layout()

    # ==================== DASHBOARD CALLBACKS ====================
    @app.callback(
        Output('alerts-section', 'children'),
        Output('patients-table-container', 'children'),
        Input('url', 'pathname')
    )
    def update_dashboard(pathname):
        if pathname != '/' and pathname is not None:
            raise PreventUpdate

        # Get all patients summary
        all_patients = get_patients_summary()
        patients_with_alerts = get_patients_with_alerts()

        # Create components
        alerts_panel = create_alerts_panel(patients_with_alerts)
        patients_table = create_patients_table(all_patients)

        return alerts_panel, patients_table

    @app.callback(
        Output('url', 'pathname', allow_duplicate=True),
        Output('selected-patient-store', 'data'),
        Input({'type': 'alert-card', 'patient_id': ALL}, 'n_clicks'),
        Input({'type': 'patient-row', 'patient_id': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def navigate_to_patient(alert_clicks, row_clicks):
        if not ctx.triggered_id:
            raise PreventUpdate

        # Get the patient_id from the triggered component
        patient_id = ctx.triggered_id.get('patient_id')
        if patient_id:
            return '/patient', patient_id

        raise PreventUpdate

    # ==================== PATIENT MONITOR CALLBACKS ====================
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
        if not info:
            return html.Div("Paciente no encontrado"), None, None, None, None, None, None

        # Calcular edad
        try:
            dob = datetime.strptime(str(info["date_of_birth"]), "%Y-%m-%d %H:%M:%S")
            age = (datetime.now() - dob).days // 365
        except:
            age = "N/D"

        card = dbc.Card([
            dbc.CardBody([
                html.P(f"ID: {info['patient_id']}", className="mb-1"),
                html.P(f"Genero: {info['genre'] or 'N/D'}", className="mb-1"),
                html.P(f"Edad: {age} anos", className="mb-1"),
                html.P(f"Hospital: {info['hospital_id']}", className="mb-0")
            ])
        ], className="bg-transparent text-white")

        # Obtener rango de fechas disponible
        _, wearable_df = load_all_data()
        patient_data = wearable_df[wearable_df["imei"] == str(info["imei"])]

        if patient_data.empty:
            return card, None, None, None, None, None, None

        min_date = patient_data["record_datetime"].min().date()
        max_date = patient_data["record_datetime"].max().date()

        # Default to most recent 7 days (or all data if less than 7 days available)
        default_start_date = max(min_date, max_date - timedelta(days=6))

        return card, min_date, max_date, default_start_date, min_date, max_date, max_date

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
            return {}, html.Div("Selecciona paciente, fechas y metricas", className="bg-dark text-white")

        info = get_patient_info(patient_id)
        if not info:
            return {}, html.Div("Paciente no encontrado", className="text-danger")

        imei = info["imei"]

        # Obtener datos para cada metrica
        data_dict = {}
        for metric in metrics:
            df = get_filtered_data(imei, metric, date_start, date_end, time_start, time_end)
            data_dict[metric] = df

        # Verificar si hay datos
        total_points = sum(len(df) for df in data_dict.values())
        if total_points == 0:
            return {}, html.Div("Sin datos para el rango seleccionado", className="text-warning")

        # Generar figura segun modo
        if view_mode == "overlay":
            fig = create_overlaid_figure(data_dict)
        else:
            fig = create_subplot_figure(data_dict)

        # Calcular estadisticas
        stats = calculate_stats(data_dict)
        if not stats:
            return fig, html.Div()

        stats_content = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6(s["metric"], className="mb-2"),
                        html.P(f"Min: {s['min']:.1f} {s['unit']}", className="mb-1 small"),
                        html.P(f"Max: {s['max']:.1f} {s['unit']}", className="mb-1 small"),
                        html.P(f"Prom: {s['avg']:.1f} {s['unit']}", className="mb-0 small")
                    ], className="p-2")
                ], className="bg-dark text-white")
            ], width=2, className="mb-2") for s in stats
        ])

        return fig, stats_content
