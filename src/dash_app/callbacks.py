from dash import callback, Output, Input, State, html, dcc, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from src.config import Alarm, AlertType
from src.data_loader import (
    get_patient_info, get_filtered_data, load_all_data,
    get_patients_summary, get_patients_with_alerts, get_patient_alarm_history
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
        Output('alarm-context-store', 'data', allow_duplicate=True),
        Input({'type': 'alert-card', 'patient_id': ALL}, 'n_clicks'),
        Input({'type': 'alert-badge', 'patient_id': ALL}, 'n_clicks'),
        Input({'type': 'patient-row', 'patient_id': ALL}, 'n_clicks'),
        Input({'type': 'alarm-history-btn', 'patient_id': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def navigate_to_patient(alert_clicks, badge_clicks, row_clicks, history_clicks):
        if not ctx.triggered_id:
            raise PreventUpdate

        # Ignore clicks on alarm-history-btn (handled by modal callback)
        if isinstance(ctx.triggered_id, dict) and ctx.triggered_id.get('type') == 'alarm-history-btn':
            raise PreventUpdate

        # Get the patient_id from the triggered component
        patient_id = ctx.triggered_id.get('patient_id')
        if not patient_id:
            raise PreventUpdate

        # Set alarm context for alert-card and alert-badge clicks
        alarm_context = {}
        trigger_type = ctx.triggered_id.get('type') if isinstance(ctx.triggered_id, dict) else None
        if trigger_type in ('alert-card', 'alert-badge'):
            patients_with_alerts = get_patients_with_alerts()
            for p in patients_with_alerts:
                if str(p["patient_id"]) == str(patient_id) and p["alerts"]:
                    # Store the most recent alarm
                    alarm: Alarm = p["alerts"][0]
                    alarm_context = alarm.to_context()
                    break

        return '/patient', patient_id, alarm_context

    # ==================== PATIENT MONITOR CALLBACKS ====================
    @app.callback(
        Output("patient-info-card", "children"),
        Output("date-start", "min_date_allowed"),
        Output("date-start", "max_date_allowed"),
        Output("date-start", "date"),
        Output("date-end", "min_date_allowed"),
        Output("date-end", "max_date_allowed"),
        Output("date-end", "date"),
        Output("metrics-checklist", "value"),
        Output("time-start", "value"),
        Output("time-end", "value"),
        Input("patient-dropdown", "value"),
        Input("alarm-context-store", "data")
    )
    def update_patient_info(patient_id, alarm_context):
        empty = html.Div(), None, None, None, None, None, None, ["heart_rate", "blood_oxygen_saturation"], 0, 23
        if not patient_id:
            return empty

        info = get_patient_info(patient_id)
        if not info:
            return html.Div("Paciente no encontrado"), None, None, None, None, None, None, ["heart_rate", "blood_oxygen_saturation"], 0, 23

        # Calcular edad
        try:
            dob = datetime.strptime(str(info["date_of_birth"]), "%Y-%m-%d %H:%M:%S")
            age = (datetime.now() - dob).days // 365
        except:
            age = "N/D"

        card = dbc.Card([
            dbc.CardBody([
                html.Small(f"ID: {info['patient_id']}", className="d-block mb-0"),
                html.Small(f"Genero: {info['genre'] or 'N/D'}", className="d-block mb-0"),
                html.Small(f"Edad: {age} anos", className="d-block mb-0"),
                html.Small(f"Hospital: {info['hospital_id']}", className="d-block mb-0")
            ], className="p-2")
        ], className="bg-transparent text-white")

        # Obtener rango de fechas disponible
        _, wearable_df = load_all_data()
        patient_data = wearable_df[wearable_df["imei"] == str(info["imei"])]

        if patient_data.empty:
            return card, None, None, None, None, None, None, ["heart_rate", "blood_oxygen_saturation"], 0, 23

        min_date = patient_data["record_datetime"].min().date()
        max_date = patient_data["record_datetime"].max().date()

        # Defaults
        default_metrics = ["heart_rate", "blood_oxygen_saturation"]
        default_time_start = 0
        default_time_end = 23

        # Check if coming from an alarm click
        if alarm_context and str(alarm_context.get("patient_id")) == str(patient_id):
            alarm_dt = datetime.fromisoformat(alarm_context["iso_date"])
            # ±2 hours window around the alarm
            window_start = alarm_dt - timedelta(hours=2)
            window_end = alarm_dt + timedelta(hours=2)
            default_start_date = window_start.date()
            default_end_date = window_end.date()
            default_time_start = window_start.hour
            default_time_end = window_end.hour
            # Show all core metrics so the user can correlate
            default_metrics = [
                "heart_rate", "blood_oxygen_saturation",
                "systolic_blood_pressure", "diastolic_blood_pressure",
            ]
        else:
            # Default to most recent 7 days
            default_start_date = max(min_date, max_date - timedelta(days=6))
            default_end_date = max_date

        return card, min_date, max_date, default_start_date, min_date, max_date, default_end_date, default_metrics, default_time_start, default_time_end

    @app.callback(
        Output("main-graph", "figure"),
        Output("stats-panel", "children"),
        Input("patient-dropdown", "value"),
        Input("date-start", "date"),
        Input("date-end", "date"),
        Input("time-start", "value"),
        Input("time-end", "value"),
        Input("metrics-checklist", "value"),
        Input("view-mode", "value"),
        Input("alarm-context-store", "data")
    )
    def update_graph(patient_id, date_start, date_end, time_start, time_end, metrics, view_mode, alarm_context):
        if not patient_id or not date_start or not date_end or not metrics:
            return {}, html.Div("Selecciona paciente, fechas y metricas", className="bg-dark text-white")

        # Hidden graph used for warning states
        hidden_graph = {
            "data": [],
            "layout": {"template": "plotly_dark", "height": 1, "paper_bgcolor": "rgba(0,0,0,0)",
                        "plot_bgcolor": "rgba(0,0,0,0)", "margin": {"t": 0, "b": 0, "l": 0, "r": 0},
                        "xaxis": {"visible": False}, "yaxis": {"visible": False},
                        "modebar": {"bgcolor": "rgba(0,0,0,0)", "orientation": "v", "activecolor": "rgba(0,0,0,0)", "color": "rgba(0,0,0,0)"}}
        }

        invalid_range = (date_start > date_end) or (date_start == date_end and time_start >= time_end)
        if invalid_range:
            warning = html.Div(
                html.Div(
                    "\u26a0\ufe0f La fecha de inicio no puede ser posterior a la fecha de fin. "
                    "Por favor, selecciona un rango de fechas valido.",
                    className="text-center text-white p-3",
                    style={"maxWidth": "500px", "backgroundColor": "#082e53",
                           "border": "1px solid #375a7f", "borderRadius": "4px"},
                ),
                style={"display": "flex", "alignItems": "center", "justifyContent": "center", "height": "65vh"},
            )
            return hidden_graph, warning

        info = get_patient_info(patient_id)
        if not info:
            return hidden_graph, html.Div("Paciente no encontrado", className="text-danger")

        imei = info["imei"]

        # Obtener datos para cada metrica
        data_dict = {}
        for metric in metrics:
            df = get_filtered_data(imei, metric, date_start, date_end, time_start, time_end)
            data_dict[metric] = df

        # Verificar si hay datos
        total_points = sum(len(df) for df in data_dict.values())
        if total_points == 0:
            warning = html.Div(
                html.Div(
                    "\ud83d\udcca No hay datos disponibles para el rango de tiempo seleccionado.",
                    className="text-center text-white p-3",
                    style={"maxWidth": "500px", "backgroundColor": "#082e53",
                           "border": "1px solid #375a7f", "borderRadius": "4px"},
                ),
                style={"display": "flex", "alignItems": "center", "justifyContent": "center", "height": "65vh"},
            )
            return hidden_graph, warning

        # Reconstruct Alarm from store context if it matches current patient/metrics
        alarm = None
        if (alarm_context
                and str(alarm_context.get("patient_id")) == str(patient_id)
                and alarm_context.get("metric_key") in metrics):
            alarm = Alarm.from_context(alarm_context)

        # Generar figura segun modo
        if view_mode == "overlay":
            fig = create_overlaid_figure(data_dict, alarm=alarm)
        else:
            fig = create_subplot_figure(data_dict, alarm=alarm)

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

    # ==================== ALARM HISTORY MODAL CALLBACKS ====================
    @app.callback(
        Output("alarm-history-modal", "is_open"),
        Output("alarm-history-patient-store", "data"),
        Output("alarm-history-modal-title", "children"),
        Output("alarm-history-metric-filter", "value"),
        Output("alarm-history-weeks-store", "data"),
        Input({"type": "alarm-history-btn", "patient_id": ALL}, "n_clicks"),
        Input("alarm-history-close-btn", "n_clicks"),
        State("alarm-history-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_alarm_history_modal(btn_clicks, close_click, is_open):
        trigger = ctx.triggered_id

        if trigger == "alarm-history-close-btn":
            return False, None, "", "all", 2

        if isinstance(trigger, dict) and trigger.get("type") == "alarm-history-btn":
            if any(c and c > 0 for c in btn_clicks):
                patient_id = trigger["patient_id"]
                return True, patient_id, f"Historial de Alarmas - Paciente {patient_id}", "all", 2

        raise PreventUpdate

    # Load more weeks callback
    @app.callback(
        Output("alarm-history-weeks-store", "data", allow_duplicate=True),
        Input("alarm-history-load-more-btn", "n_clicks"),
        State("alarm-history-weeks-store", "data"),
        prevent_initial_call=True
    )
    def load_more_weeks(n_clicks, current_weeks):
        if not n_clicks:
            raise PreventUpdate
        return (current_weeks or 2) + 1

    @app.callback(
        Output("alarm-history-table-container", "children"),
        Output("alarm-history-load-more-container", "style"),
        Input("alarm-history-patient-store", "data"),
        Input("alarm-history-metric-filter", "value"),
        Input("alarm-history-weeks-store", "data"),
        prevent_initial_call=True
    )
    def populate_alarm_history(patient_id, metric_filter, weeks):
        if not patient_id:
            raise PreventUpdate

        weeks = weeks or 2
        days = weeks * 7
        alarms = get_patient_alarm_history(patient_id, metric_filter, days=days)
        all_alarms = get_patient_alarm_history(patient_id, metric_filter)

        if not alarms:
            return dbc.Alert(
                f"No se encontraron alarmas en las ultimas {weeks} semanas.",
                color="info",
                className="text-center"
            ), {"display": "block"} if len(all_alarms) > 0 else {"display": "none"}

        rows = []
        for i, a in enumerate(alarms):
            badge_color = "danger" if a.alert_type == AlertType.HIGH else "warning"
            rows.append(html.Tr([
                html.Td(a.formatted_date),
                html.Td(a.metric_name),
                html.Td(f"{a.value:.1f} {a.unit}"),
                html.Td(html.Span(a.alert_type.display_name, className=f"badge bg-{badge_color}")),
                html.Td(dbc.Button(
                    "Ver",
                    id={"type": "alarm-row-btn", "index": i},
                    color="outline-light",
                    size="sm",
                ))
            ]))

        # Store alarm data for lookup when clicking "Ver"
        alarm_store = dcc.Store(
            id="alarm-list-store",
            data=[a.to_context() for a in alarms]
        )

        table = dbc.Table([
            html.Thead(html.Tr([
                html.Th("Fecha"),
                html.Th("Metrica"),
                html.Th("Valor"),
                html.Th("Tipo"),
                html.Th(""),
            ])),
            html.Tbody(rows)
        ], bordered=True, hover=True, responsive=True, className="table-dark", size="sm")

        # Hide "load more" if all alarms are already shown
        has_more = len(alarms) < len(all_alarms)
        load_more_style = {"display": "block"} if has_more else {"display": "none"}

        return html.Div([
            alarm_store,
            html.Small(
                f"{len(alarms)} alarma(s) en las ultimas {weeks} semanas"
                + (f" (de {len(all_alarms)} totales)" if has_more else " (todas)"),
                className="text-muted mb-2 d-block"
            ),
            table
        ]), load_more_style

    # ==================== ALARM ROW CLICK -> NAVIGATE ====================
    @app.callback(
        Output("alarm-history-modal", "is_open", allow_duplicate=True),
        Output("alarm-context-store", "data"),
        Output("url", "pathname", allow_duplicate=True),
        Output("selected-patient-store", "data", allow_duplicate=True),
        Input({"type": "alarm-row-btn", "index": ALL}, "n_clicks"),
        State("alarm-list-store", "data"),
        State("alarm-history-patient-store", "data"),
        prevent_initial_call=True
    )
    def navigate_from_alarm(btn_clicks, alarm_list, patient_id):
        if not ctx.triggered_id or not any(c and c > 0 for c in btn_clicks):
            raise PreventUpdate

        index = ctx.triggered_id["index"]
        if not alarm_list or index >= len(alarm_list):
            raise PreventUpdate

        alarm_data = alarm_list[index]
        alarm_data["patient_id"] = patient_id
        alarm_context = alarm_data

        return False, alarm_context, "/patient", patient_id
