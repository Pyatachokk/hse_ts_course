#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio


OUTPUT_NAME = "02_decompose_02_bisquare_weight.png"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    u = np.linspace(-2.0, 2.0, 801)
    weight = np.where(np.abs(u) < 1.0, (1.0 - u**2) ** 2, 0.0)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=u,
            y=weight,
            mode="lines",
            line=dict(color="#1f5f8b", width=4),
            hovertemplate="u=%{x:.2f}<br>Вес=%{y:.2f}<extra></extra>",
            name="Вес",
        )
    )

    fig.add_vline(x=-1, line_width=1.5, line_dash="dash", line_color="#b8c0cc")
    fig.add_vline(x=1, line_width=1.5, line_dash="dash", line_color="#b8c0cc")
    fig.add_hline(y=0, line_width=1, line_color="#d6dbe3")
    fig.add_hline(y=1, line_width=1, line_dash="dot", line_color="#d6dbe3")

    fig.add_annotation(
        x=0,
        y=1.08,
        text="Максимальный вес",
        showarrow=False,
        font=dict(size=17, color="#243746"),
    )
    fig.add_annotation(
        x=1.36,
        y=0.12,
        text="Выбросы<br>почти не влияют",
        showarrow=False,
        font=dict(size=16, color="#596275"),
        align="center",
    )
    fig.add_annotation(
        x=-1.36,
        y=0.12,
        text="Выбросы<br>почти не влияют",
        showarrow=False,
        font=dict(size=16, color="#596275"),
        align="center",
    )

    fig.update_layout(
        template="plotly_white",
        width=760,
        height=460,
        margin=dict(l=66, r=28, t=34, b=62),
        showlegend=False,
        font=dict(family="Arial, sans-serif", size=17, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(
        title_text="Нормированный остаток u = eₜ / h",
        range=[-2, 2],
        tickvals=[-2, -1, 0, 1, 2],
        gridcolor="#edf0f4",
        zeroline=True,
        zerolinecolor="#aeb7c4",
    )
    fig.update_yaxes(
        title_text="Робастный вес",
        range=[-0.04, 1.16],
        tickvals=[0, 0.5, 1],
        gridcolor="#edf0f4",
        zeroline=False,
    )

    pio.write_image(fig, output_path, width=760, height=460, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
