from dash import callback, Output, Input, html
import dash_bootstrap_components as dbc
from datetime import datetime
import sys
sys.path.insert(0, "/home/pato/Documents/src/ongoing/ro/Pacientes")
from src.data_loader import get_patient_info, get_filtered_data, load_all_data
from src.dash_app.figures import create_overlaid_figure, create_subplot_figure, calculate_stats


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
                html.P(f"Género: {info['genre'] or 'N/D'}", className="mb-1"),
                html.P(f"Edad: {age} años", className="mb-1"),
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
            return {}, html.Div("Selecciona paciente, fechas y métricas", className="bg-dark text-white")

        info = get_patient_info(patient_id)
        if not info:
            return {}, html.Div("Paciente no encontrado", className="text-danger")

        imei = info["imei"]

        # Obtener datos para cada métrica
        data_dict = {}
        for metric in metrics:
            df = get_filtered_data(imei, metric, date_start, date_end, time_start, time_end)
            data_dict[metric] = df

        # Verificar si hay datos
        total_points = sum(len(df) for df in data_dict.values())
        if total_points == 0:
            return {}, html.Div("Sin datos para el rango seleccionado", className="text-warning")

        # Generar figura según modo
        if view_mode == "overlay":
            fig = create_overlaid_figure(data_dict)
        else:
            fig = create_subplot_figure(data_dict)

        # Calcular estadísticas
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
