from __future__ import annotations
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.config import METRICS, Alarm


def _y_range(df) -> list | None:
    """Compute y-axis range from data with 5% padding above and below."""
    if df.empty:
        return None
    data_min = df["value"].min()
    data_max = df["value"].max()
    span = data_max - data_min
    if span == 0:
        span = abs(data_max) * 0.1 or 1
    padding = span * 0.15
    return [data_min - padding, data_max + padding]


def _add_alarm_marker(fig: go.Figure, alarm: Alarm, row: int | None = None) -> None:
    """Add an alarm marker to a figure."""
    kwargs = dict(
        x=[alarm.iso_date],
        y=[alarm.value],
        mode="markers+text",
        marker=dict(size=14, color="red", symbol="x", line=dict(width=2, color="white")),
        text=[f"Alarma: {alarm.value:.1f} {alarm.unit}"],
        textposition="top center",
        textfont=dict(color="red", size=12),
        name="Alarma",
        showlegend=False,
        hovertemplate=f"ALARMA<br>{alarm.metric_name}: %{{y:.1f}} {alarm.unit}<extra></extra>"
    )
    if row is not None:
        fig.add_trace(go.Scatter(**kwargs), row=row, col=1)
    else:
        fig.add_trace(go.Scatter(**kwargs))


def create_overlaid_figure(data_dict: dict, alarm: Alarm | None = None) -> go.Figure:
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

    if alarm:
        _add_alarm_marker(fig, alarm)

    layout_kwargs = dict(
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60),
        xaxis_title="Fecha/Hora",
        yaxis_title="Valor"
    )

    if len(data_dict) == 1:
        metric = next(iter(data_dict))
        cfg = METRICS[metric]
        y_range = _y_range(data_dict[metric])
        if y_range:
            layout_kwargs["yaxis_range"] = y_range
            layout_kwargs["yaxis_title"] = cfg["unit"]

    fig.update_layout(**layout_kwargs)

    return fig


def create_subplot_figure(data_dict: dict, alarm: Alarm | None = None) -> go.Figure:
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
        y_range = _y_range(df)
        yaxis_kwargs = dict(title_text=cfg["unit"], row=i, col=1)
        if y_range:
            yaxis_kwargs["range"] = y_range
        fig.update_yaxes(**yaxis_kwargs)

        if alarm and alarm.metric_key == metric:
            _add_alarm_marker(fig, alarm, row=i)

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
