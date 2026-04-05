from __future__ import annotations
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.config import METRICS


def _add_alarm_marker(fig: go.Figure, alarm_marker: dict | None, row: int | None = None) -> None:
    """Add an alarm marker to a figure."""
    if not alarm_marker:
        return
    cfg = METRICS[alarm_marker["metric_key"]]
    kwargs = dict(
        x=[alarm_marker["datetime"]],
        y=[alarm_marker["value"]],
        mode="markers+text",
        marker=dict(size=14, color="red", symbol="x", line=dict(width=2, color="white")),
        text=[f"Alarma: {alarm_marker['value']:.1f} {cfg['unit']}"],
        textposition="top center",
        textfont=dict(color="red", size=12),
        name="Alarma",
        showlegend=False,
        hovertemplate=f"ALARMA<br>{cfg['name']}: %{{y:.1f}} {cfg['unit']}<extra></extra>"
    )
    if row is not None:
        fig.add_trace(go.Scatter(**kwargs), row=row, col=1)
    else:
        fig.add_trace(go.Scatter(**kwargs))


def create_overlaid_figure(data_dict: dict, alarm_marker: dict | None = None) -> go.Figure:
    """Crea figura con métricas superpuestas."""
    fig = go.Figure()

    for metric, df in data_dict.items():
        if df.empty:
            continue
        cfg = METRICS[metric]
        fig.add_trace(go.Scatter(
            x=df["record_datetime"],
            y=df["value"],
            name=cfg["name"],
            line=dict(color=cfg["color"], width=2),
            hovertemplate=f"{cfg['name']}: %{{y:.1f}} {cfg['unit']}<extra></extra>"
        ))

    _add_alarm_marker(fig, alarm_marker)

    fig.update_layout(
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60),
        xaxis_title="Fecha/Hora",
        yaxis_title="Valor"
    )

    return fig


def create_subplot_figure(data_dict: dict, alarm_marker: dict | None = None) -> go.Figure:
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
                y=df["value"],
                name=cfg["name"],
                line=dict(color=cfg["color"], width=2)
            ),
            row=i, col=1
        )
        fig.update_yaxes(title_text=cfg["unit"], row=i, col=1)

        # Add alarm marker to the matching subplot
        if alarm_marker and alarm_marker["metric_key"] == metric:
            _add_alarm_marker(fig, alarm_marker, row=i)

    fig.update_layout(
        template="plotly_dark",
        height=200 * n,
        showlegend=False,
        margin=dict(l=60, r=20, t=40, b=40)
    )

    return fig


def calculate_stats(data_dict: dict) -> list[dict]:
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
