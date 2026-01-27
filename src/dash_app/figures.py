import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.config import METRICS


def create_overlaid_figure(data_dict):
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

    fig.update_layout(
        template="plotly_dark",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=20, t=40, b=60),
        xaxis_title="Fecha/Hora",
        yaxis_title="Valor"
    )

    return fig


def create_subplot_figure(data_dict):
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

    fig.update_layout(
        template="plotly_dark",
        height=200 * n,
        showlegend=False,
        margin=dict(l=60, r=20, t=40, b=40)
    )

    return fig


def calculate_stats(data_dict):
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
