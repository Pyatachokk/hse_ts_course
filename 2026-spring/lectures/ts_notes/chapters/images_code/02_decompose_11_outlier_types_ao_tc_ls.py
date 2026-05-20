#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


OUTPUT_NAME = "02_decompose_11_outlier_types_ao_tc_ls.png"


def add_effect_fill(
    fig: go.Figure,
    x: np.ndarray,
    base: np.ndarray,
    observed: np.ndarray,
    row: int,
    col: int,
    name: str,
) -> None:
    fig.add_trace(
        go.Scatter(
            x=np.r_[x, x[::-1]],
            y=np.r_[observed, base[::-1]],
            mode="lines",
            line=dict(width=0),
            fill="toself",
            fillcolor="rgba(196, 106, 29, 0.20)",
            hoverinfo="skip",
            name=name,
            showlegend=col == 1,
        ),
        row=row,
        col=col,
    )


def add_panel(
    fig: go.Figure,
    x: np.ndarray,
    base: np.ndarray,
    observed: np.ndarray,
    effect: np.ndarray,
    col: int,
    event: int,
) -> None:
    add_effect_fill(fig, x, base, observed, 1, col, "Эффект выброса")

    fig.add_trace(
        go.Scatter(
            x=x,
            y=base,
            mode="lines",
            line=dict(color="#8c96a6", width=2.0, dash="dot"),
            name="Ряд без выброса",
            showlegend=col == 1,
            hovertemplate="t=%{x}<br>База %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=observed,
            mode="lines",
            line=dict(color="#1f5f8b", width=2.7),
            name="Наблюдаемый ряд",
            showlegend=col == 1,
            hovertemplate="t=%{x}<br>Ряд %{y:.2f}<extra></extra>",
        ),
        row=1,
        col=col,
    )

    marker_index = int(np.argmax(np.abs(effect)))
    fig.add_trace(
        go.Scatter(
            x=[x[marker_index]],
            y=[observed[marker_index]],
            mode="markers",
            marker=dict(
                size=13,
                color="#b42318",
                line=dict(color="white", width=2),
                symbol="circle",
            ),
            name="Начало события",
            showlegend=col == 1,
            hovertemplate="Начало события<br>t=%{x}<br>%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=col,
    )

    fig.add_vline(
        x=event,
        line=dict(color="#b42318", width=1.4, dash="dash"),
        row=1,
        col=col,
    )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    x = np.arange(1, 41)
    event = 18
    base = 10 + 0.045 * x + 0.33 * np.sin(2 * np.pi * x / 18 - 0.4)

    ao_effect = np.zeros_like(x, dtype=float)
    ao_effect[event - 1] = 2.3

    tc_effect = np.zeros_like(x, dtype=float)
    decay = 0.72
    tc_effect[event - 1 :] = 2.25 * decay ** np.arange(x.size - event + 1)

    ls_effect = np.zeros_like(x, dtype=float)
    ls_effect[event - 1 :] = 1.75

    panels = [
        (
            base + ao_effect,
            ao_effect,
            "AO: одна точка",
        ),
        (
            base + tc_effect,
            tc_effect,
            "TC: затухающий шок",
        ),
        (
            base + ls_effect,
            ls_effect,
            "LS: новый уровень",
        ),
    ]

    fig = make_subplots(
        rows=1,
        cols=3,
        shared_yaxes=True,
        horizontal_spacing=0.055,
        subplot_titles=[panel[2] for panel in panels],
    )

    for col, (observed, effect, _) in enumerate(panels, start=1):
        add_panel(
            fig=fig,
            x=x,
            base=base,
            observed=observed,
            effect=effect,
            col=col,
            event=event,
        )

    fig.update_layout(
        template="plotly_white",
        width=1200,
        height=560,
        margin=dict(l=70, r=28, t=105, b=72),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.15,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        font=dict(family="Arial, sans-serif", size=15, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_annotations(font=dict(size=15, color="#243746"))

    for col in range(1, 4):
        fig.update_xaxes(
            title_text="Время",
            range=[1, 40],
            dtick=8,
            title_font=dict(size=15),
            tickfont=dict(size=12),
            gridcolor="#edf0f4",
            zeroline=False,
            row=1,
            col=col,
        )
        fig.update_yaxes(
            range=[9.2, 14.4],
            gridcolor="#edf0f4",
            zeroline=False,
            tickfont=dict(size=12),
            row=1,
            col=col,
        )

    fig.update_yaxes(title_text="Значение ряда", title_font=dict(size=15), row=1, col=1)

    pio.write_image(fig, output_path, width=1200, height=560, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
