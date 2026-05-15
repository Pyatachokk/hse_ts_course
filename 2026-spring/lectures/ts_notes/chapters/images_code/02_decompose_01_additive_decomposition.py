#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


OUTPUT_NAME = "02_decompose_01_additive_decomposition.png"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    rng = np.random.default_rng(8)
    t = np.arange(72)
    trend = 10 + 0.055 * t + 0.45 * np.sin(2 * np.pi * t / 60 - 0.8)
    seasonal = 0.9 * np.sin(2 * np.pi * t / 12 - 0.6) + 0.25 * np.sin(
        4 * np.pi * t / 12 + 0.8
    )
    residual = rng.normal(0, 0.22, size=t.size)
    observed = trend + seasonal + residual

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.055,
        row_heights=[0.34, 0.22, 0.22, 0.22],
        subplot_titles=[
            "Исходный ряд",
            "Тренд",
            "Сезонность",
            "Остаток",
        ],
    )

    traces = [
        (observed, "y_t", "#243746", 2.8),
        (trend, "t_t", "#2f80ed", 2.6),
        (seasonal, "s_t", "#c46a1d", 2.4),
        (residual, "e_t", "#596275", 2.0),
    ]

    for row, (values, name, color, width) in enumerate(traces, start=1):
        fig.add_trace(
            go.Scatter(
                x=t,
                y=values,
                mode="lines",
                name=name,
                line=dict(color=color, width=width),
                hovertemplate=f"{name}: %{{y:.2f}}<extra></extra>",
            ),
            row=row,
            col=1,
        )

    for boundary in range(12, 72, 12):
        fig.add_vline(
            x=boundary,
            line_width=1,
            line_dash="dot",
            line_color="#c6cbd3",
        )

    fig.add_annotation(
        x=0.985,
        y=1.035,
        xref="paper",
        yref="paper",
        text="y<sub>t</sub> = t<sub>t</sub> + s<sub>t</sub> + e<sub>t</sub>",
        showarrow=False,
        font=dict(size=21, color="#243746"),
        align="right",
    )

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=760,
        margin=dict(l=72, r=32, t=86, b=56),
        showlegend=False,
        font=dict(family="Arial, sans-serif", size=16, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    fig.update_annotations(font=dict(size=16, color="#243746"))
    fig.update_xaxes(
        title_text="Время",
        title_font=dict(size=17),
        tickfont=dict(size=13),
        gridcolor="#edf0f4",
        row=4,
        col=1,
    )

    for row in range(1, 5):
        fig.update_yaxes(
            zeroline=True,
            zerolinecolor="#c6cbd3",
            gridcolor="#edf0f4",
            tickfont=dict(size=12),
            row=row,
            col=1,
        )

    fig.update_yaxes(title_text="Значение", row=1, col=1)
    fig.update_yaxes(title_text="Уровень", row=2, col=1)
    fig.update_yaxes(title_text="Эффект", row=3, col=1)
    fig.update_yaxes(title_text="Шум", row=4, col=1)

    pio.write_image(fig, output_path, width=1100, height=760, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
