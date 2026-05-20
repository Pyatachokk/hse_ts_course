#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio


OUTPUT_NAME = "02_decompose_07_loess_local_weighting.png"


def tricube_weights(x: np.ndarray, x0: float, bandwidth: float) -> np.ndarray:
    u = np.abs((x - x0) / bandwidth)
    return np.where(u < 1.0, (1.0 - u**3) ** 3, 0.0)


def exponential_weights(x: np.ndarray, x0: float, bandwidth: float) -> np.ndarray:
    return np.exp(-((x - x0) / bandwidth) ** 2)


def weighted_line(x: np.ndarray, y: np.ndarray, x0: float, bandwidth: float) -> tuple[float, float]:
    weights = exponential_weights(x, x0, bandwidth)
    design = np.column_stack([np.ones_like(x), x - x0])
    weighted_design = design * np.sqrt(weights)[:, None]
    weighted_y = y * np.sqrt(weights)
    beta, *_ = np.linalg.lstsq(weighted_design, weighted_y, rcond=None)
    return float(beta[0]), float(beta[1])


def loess_curve(x: np.ndarray, y: np.ndarray, bandwidth: float) -> np.ndarray:
    smoothed = np.empty_like(y)
    for index, x0 in enumerate(x):
        intercept, _ = weighted_line(x, y, float(x0), bandwidth)
        smoothed[index] = intercept
    return smoothed


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    rng = np.random.default_rng(7)
    x = np.linspace(0, 10, 70)
    signal = 0.45 * x + 1.2 * np.sin(0.9 * x) + 0.25 * np.cos(2.3 * x)
    y = signal + rng.normal(0, 0.48, size=x.size)

    x0 = 5.9
    bandwidth = 1.55
    weights = exponential_weights(x, x0, bandwidth)
    loess = loess_curve(x, y, bandwidth)
    local_intercept, local_slope = weighted_line(x, y, x0, bandwidth)

    visible_radius = 2.4 * bandwidth
    line_radius = 1.45 * bandwidth
    line_x = np.linspace(x0 - line_radius, x0 + line_radius, 80)
    local_line = local_intercept + local_slope * (line_x - x0)
    y0 = local_intercept

    fig = go.Figure()
    bands = 26
    band_edges = np.linspace(x0 - visible_radius, x0 + visible_radius, bands + 1)
    for left, right in zip(band_edges[:-1], band_edges[1:]):
        center = 0.5 * (left + right)
        opacity = 0.24 * float(exponential_weights(np.array([center]), x0, bandwidth)[0])
        fig.add_vrect(
            x0=left,
            x1=right,
            fillcolor="#f0c38a",
            opacity=opacity,
            layer="below",
            line_width=0,
        )
    fig.add_vline(x=x0, line_width=1.4, line_dash="dot", line_color="#b45f3c")

    inside = weights >= 0.08
    outside = ~inside
    marker_sizes = 7 + 22 * weights[inside]
    marker_opacity = 0.26 + 0.64 * weights[inside]

    fig.add_trace(
        go.Scatter(
            x=x[outside],
            y=y[outside],
            mode="markers",
            marker=dict(size=7, color="#9aa5b3", opacity=0.38),
            name="Вне окна",
            hovertemplate="x=%{x:.2f}<br>y=%{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x[inside],
            y=y[inside],
            mode="markers",
            marker=dict(
                size=marker_sizes,
                color="#c46a1d",
                opacity=marker_opacity,
                line=dict(color="white", width=1.2),
            ),
            name="Вес",
            hovertemplate="x=%{x:.2f}<br>y=%{y:.2f}<br>Вес=%{customdata:.2f}<extra></extra>",
            customdata=weights[inside],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=loess,
            mode="lines",
            line=dict(color="#1f5f8b", width=3.2),
            name="LOESS",
            hovertemplate="x=%{x:.2f}<br>LOESS=%{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=line_x,
            y=local_line,
            mode="lines",
            line=dict(color="#c43b3b", width=3.0),
            name="Локальная регрессия",
            hovertemplate="x=%{x:.2f}<br>Локальная линия=%{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[x0],
            y=[y0],
            mode="markers",
            marker=dict(size=13, color="#c43b3b", line=dict(color="white", width=2)),
            name="Значение в x₀",
            hovertemplate="x₀=%{x:.2f}<br>ŷ=%{y:.2f}<extra></extra>",
        )
    )

    fig.add_annotation(
        x=x0,
        y=y0 + 1.25,
        text="Точка x₀",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-44,
        font=dict(size=15, color="#b45f3c"),
        arrowcolor="#b45f3c",
        bgcolor="rgba(255,255,255,0.90)",
        borderpad=3,
    )
    fig.add_annotation(
        x=x0 - bandwidth * 1.08,
        y=float(np.percentile(y, 13)),
        text="Затухающая зона<br>взвешивания",
        showarrow=False,
        font=dict(size=16, color="#8f432b"),
        bgcolor="rgba(255,255,255,0.86)",
        bordercolor="rgba(180,95,60,0.25)",
        borderpad=4,
    )
    fig.add_annotation(
        x=x0 + bandwidth * 1.18,
        y=float(np.percentile(y, 79)),
        text="Экспоненциальное ядро:<br>вес плавно убывает",
        showarrow=False,
        align="center",
        font=dict(size=15, color="#243746"),
        bgcolor="rgba(255,255,255,0.88)",
        bordercolor="rgba(36,55,70,0.18)",
        borderpad=4,
    )

    fig.update_layout(
        template="plotly_white",
        width=980,
        height=600,
        margin=dict(l=70, r=34, t=34, b=68),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        font=dict(family="Arial, sans-serif", size=16, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(
        title_text="Время x",
        range=[-0.15, 10.15],
        gridcolor="#edf0f4",
        zeroline=False,
    )
    fig.update_yaxes(
        title_text="Наблюдение y",
        gridcolor="#edf0f4",
        zeroline=False,
    )

    pio.write_image(fig, output_path, width=980, height=620, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
