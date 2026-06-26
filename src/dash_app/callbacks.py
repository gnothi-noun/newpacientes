from dash import callback, Output, Input, State, html, dcc, ALL, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from src.config import Alarm, AlertType
from src.data_loader import (
    get_patient_info, get_filtered_data, load_all_data,
    get_patients_summary, get_patients_with_alerts, get_patient_alarm_history,
    group_consecutive_alarms
)


def _format_alarm_range(start, end, count) -> str:
    """Formatea la fecha de un evento de alarma.

    Un solo registro -> fecha y hora puntual. Varios consecutivos -> rango
    "de tal hora a tal hora" (mostrando ambas fechas solo si cruzan de día).
    """
    if count <= 1:
        return start.strftime("%d/%m/%Y %H:%M")
    if start.date() == end.date():
        return f"{start.strftime('%d/%m/%Y')} {start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
    return f"{start.strftime('%d/%m/%Y %H:%M')} - {end.strftime('%d/%m/%Y %H:%M')}"
import pandas as pd
from src.dash_app.figures import (
    create_overlaid_figure, create_subplot_figure, create_temperature_alarm_figure,
    calculate_stats, create_baseline_figure, create_trend_figure,
    create_gauge_figure, create_heatmap_figure
)
from src.dash_app.pages.patient_monitor import create_patient_monitor_layout
from src.dash_app.pages.dashboard import (
    create_dashboard_layout, create_alerts_panel, create_patients_table,
    create_no_data_panel
)
from src.analytics import get_patient_analysis, get_clean_series
from src.config import ANALYSIS_METRICS


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
        no_data_patients = [p for p in all_patients if p.get("no_data_alert")]

        # Create components: panel de "sin datos" (si hay) + alertas de valor
        sections = []
        nd_panel = create_no_data_panel(no_data_patients)
        if nd_panel:
            sections.append(nd_panel)
        sections.append(create_alerts_panel(patients_with_alerts))
        alerts_panel = html.Div(sections)
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
        ], className="text-white", style={"backgroundColor": "#6f6f6f", "border": "none"})

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
            alarm_metric = alarm_context.get("metric_key")
            if alarm_metric == "temperature":
                default_metrics = [
                    "temperature",
                    "heart_rate", "blood_oxygen_saturation",
                    "systolic_blood_pressure", "diastolic_blood_pressure",
                ]
            else:
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
        if not patient_id or not date_start or not date_end:
            return {}, html.Div("Selecciona paciente y fechas", className="bg-dark text-white")

        # Hidden graph used for warning states
        hidden_graph = {
            "data": [],
            "layout": {"template": "plotly_dark", "height": 1, "paper_bgcolor": "rgba(0,0,0,0)",
                        "plot_bgcolor": "rgba(0,0,0,0)", "margin": {"t": 0, "b": 0, "l": 0, "r": 0},
                        "xaxis": {"visible": False}, "yaxis": {"visible": False},
                        "modebar": {"bgcolor": "rgba(0,0,0,0)", "orientation": "v", "activecolor": "rgba(0,0,0,0)", "color": "rgba(0,0,0,0)"}}
        }

        if not metrics:
            warning = html.Div(
                html.Div(
                    "\u26a0\ufe0f No hay métricas seleccionadas. "
                    "Selecciona al menos una métrica para visualizar en el gráfico.",
                    className="text-center text-white p-3",
                    style={"maxWidth": "500px", "backgroundColor": "#082e53",
                           "border": "1px solid #375a7f", "borderRadius": "4px"},
                ),
                style={"display": "flex", "alignItems": "center", "justifyContent": "center", "height": "65vh"},
            )
            return hidden_graph, warning

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
        if alarm and alarm.metric_key == "temperature":
            fig = create_temperature_alarm_figure(data_dict, alarm=alarm)
        elif view_mode == "overlay":
            fig = create_overlaid_figure(data_dict, alarm=alarm)
        else:
            fig = create_subplot_figure(data_dict, alarm=alarm)

        # Calcular estadisticas
        stats = calculate_stats(data_dict)
        if not stats:
            return fig, html.Div()

        stats_content = html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H6(s["metric"], className="mb-2", style={"fontWeight": "bold", "fontSize": "1.05rem"}),
                    html.P(f"Min: {s['min']:.1f} {s['unit']}", className="mb-1 small"),
                    html.P(f"Max: {s['max']:.1f} {s['unit']}", className="mb-1 small"),
                    html.P(f"Prom: {s['avg']:.1f} {s['unit']}", className="mb-0 small")
                ], className="p-2")
            ], className="text-white", style={"backgroundColor": "#6f6f6f", "border": "none", "width": "155px"})
            for s in stats
        ], className="d-flex flex-wrap gap-2")

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

        # Agrupar alarmas consecutivas (misma métrica+tipo) en un solo evento.
        groups = group_consecutive_alarms(alarms)

        rows = []
        for i, g in enumerate(groups):
            badge_color = "danger" if g["alert_type"] == AlertType.HIGH else "warning"
            fecha = _format_alarm_range(g["start"], g["end"], g["count"])
            # Si el evento abarca varias horas, indicar la cantidad de alarmas.
            if g["count"] > 1:
                fecha_cell = html.Td([
                    html.Div(fecha),
                    html.Small(f"{g['count']} alarmas", className="text-muted"),
                ])
            else:
                fecha_cell = html.Td(fecha)

            rows.append(html.Tr([
                fecha_cell,
                html.Td(g["metric_name"]),
                html.Td(f"{g['extreme_value']:.1f} {g['unit']}"),
                html.Td(html.Span(g["alert_type"].display_name, className=f"badge bg-{badge_color}")),
                html.Td(dbc.Button(
                    "Ver",
                    id={"type": "alarm-row-btn", "index": i},
                    color="outline-light",
                    size="sm",
                ))
            ]))

        # Store de contextos (uno por evento, en orden de fila) para el botón "Ver".
        alarm_store = dcc.Store(
            id="alarm-list-store",
            data=[g["context"] for g in groups]
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
                f"{len(groups)} evento(s) ({len(alarms)} alarma(s)) en las ultimas {weeks} semanas"
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

    # ==================== DESCARGA DE INFORMES ====================
    @app.callback(
        Output("download-report-monitor", "data"),
        Input("download-report-monitor-btn", "n_clicks"),
        State("report-format-monitor", "value"),
        State("patient-dropdown", "value"),
        State("date-start", "date"),
        State("date-end", "date"),
        State("time-start", "value"),
        State("time-end", "value"),
        State("metrics-checklist", "value"),
        prevent_initial_call=True
    )
    def download_patient_report(n_clicks, fmt, patient_id, date_start, date_end,
                                time_start, time_end, metrics):
        if not n_clicks or not patient_id or not date_start or not date_end or not metrics:
            raise PreventUpdate
        # Misma validación de rango que update_graph.
        if date_start > date_end or (date_start == date_end and time_start >= time_end):
            raise PreventUpdate

        from src import reports  # import perezoso: baja la RAM de arranque en la Pi

        base = f"informe_{patient_id}_{date_start}_{date_end}"
        if fmt == "csv":
            df = reports.build_patient_csv(patient_id, metrics, date_start, date_end,
                                           time_start, time_end)
            # BOM UTF-8 para que Excel muestre bien los acentos.
            csv_str = "\ufeff" + df.to_csv(index=False)
            return dict(content=csv_str, filename=f"{base}.csv", type="text/csv")

        pdf_bytes = reports.build_patient_pdf(patient_id, metrics, date_start, date_end,
                                              time_start, time_end)
        return dcc.send_bytes(lambda buf: buf.write(pdf_bytes), f"{base}.pdf")

    @app.callback(
        Output("download-report-summary", "data"),
        Input("download-report-summary-btn", "n_clicks"),
        State("report-format-summary", "value"),
        prevent_initial_call=True
    )
    def download_summary_report(n_clicks, fmt):
        if not n_clicks:
            raise PreventUpdate

        from src import reports  # import perezoso

        base = f"resumen_pacientes_{datetime.now().strftime('%Y-%m-%d')}"
        if fmt == "csv":
            df = reports.build_summary_csv()
            csv_str = "\ufeff" + df.to_csv(index=False)  # BOM para Excel
            return dict(content=csv_str, filename=f"{base}.csv", type="text/csv")

        pdf_bytes = reports.build_summary_pdf()
        return dcc.send_bytes(lambda buf: buf.write(pdf_bytes), f"{base}.pdf")

    # ============= ANÁLISIS MÁS PROFUNDO (dentro de Monitor Paciente) =============
    @app.callback(
        Output("deep-analysis-collapse", "is_open"),
        Input("deep-analysis-btn", "n_clicks"),
        State("deep-analysis-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_deep_analysis(n_clicks, is_open):
        return not is_open

    @app.callback(
        Output("deep-analysis-content", "children"),
        Input("deep-analysis-collapse", "is_open"),
        Input("patient-dropdown", "value"),
        prevent_initial_call=True,
    )
    def update_deep_analysis(is_open, patient_id):
        # Solo calcula cuando la sección está abierta (evita trabajo si está oculta).
        if not is_open:
            raise PreventUpdate
        if not patient_id:
            return dbc.Alert("Seleccioná un paciente.", color="secondary", className="text-center")

        analysis = get_patient_analysis(patient_id)
        info = get_patient_info(patient_id)
        if not analysis or not info:
            return dbc.Alert("Sin análisis disponible para este paciente.",
                             color="secondary", className="text-center")

        imei = str(info["imei"])
        gauge_children = []
        trend_children = []
        heatmap_children = []
        for m in ANALYSIS_METRICS:
            baseline = analysis["baselines"][m]
            full = get_clean_series(imei, m)  # serie completa limpia (cacheada)

            # --- Gauge: valor actual vs banda usual (overall p10–p90) ---
            latest = float(full["value"].iloc[-1]) if not full.empty else None
            axis = None
            if not full.empty:
                amin = float(full["value"].quantile(0.02))
                amax = float(full["value"].quantile(0.98))
                if latest is not None:
                    amin, amax = min(amin, latest), max(amax, latest)
                if amax > amin:
                    axis = (amin, amax)
            band = baseline["overall"] if baseline.get("available") else None
            gauge_children.append(
                dbc.Col(dcc.Graph(figure=create_gauge_figure(m, latest, band, axis),
                                  config={"displayModeBar": False, "responsive": True}), md=4)
            )

            # --- Tendencia semanal ---
            trend_children.append(
                dbc.Col(dcc.Graph(figure=create_trend_figure(analysis["trends"][m], m),
                                  config={"displayModeBar": False, "responsive": True}),
                        md=4, className="mb-2")
            )

            # --- Mapa de calor día × hora (últimos 30 días) ---
            heatmap_children.append(
                dcc.Graph(figure=create_heatmap_figure(full, m),
                          config={"displayModeBar": False, "responsive": True}, className="mb-3")
            )

        return html.Div([
            html.H5("Estado actual (valor vs su rango usual)", className="mb-2 mt-2"),
            dbc.Row(gauge_children),

            html.H5("Tendencias semanales (alerta temprana)", className="mt-3 mb-2"),
            dbc.Row(trend_children),

            html.H5("Patrón por hora y día (últimos 30 días)", className="mt-3 mb-2"),
            *heatmap_children,
        ])
