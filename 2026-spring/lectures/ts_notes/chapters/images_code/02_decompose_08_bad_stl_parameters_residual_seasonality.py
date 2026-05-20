#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL


OUTPUT_NAME = "02_decompose_08_bad_stl_parameters_residual_seasonality.png"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    rng = np.random.default_rng(24)
    t = np.arange(144)
    index = pd.date_range("2013-01-01", periods=t.size, freq="MS")
    trend = 18 + 0.035 * t + 0.8 * np.sin(2 * np.pi * t / 96 - 0.5)
    amplitude = 1.1 + 0.25 * np.sin(2 * np.pi * t / 72)
    seasonal = amplitude * (
        np.sin(2 * np.pi * t / 12 - 0.8)
        + 0.32 * np.sin(4 * np.pi * t / 12 + 0.5)
    )
    noise = rng.normal(0, 0.18, size=t.size)
    observed = pd.Series(trend + seasonal + noise, index=index)

    correct = STL(observed, period=12, seasonal=13, trend=25, robust=True).fit()
    wrong = STL(observed, period=6, seasonal=7, trend=25, robust=True).fit()

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.34, 0.32, 0.34],
        subplot_titles=[
            "Исходный ряд с годовой сезонностью",
            "Оценка сезонности: правильный период и ошибочный период",
            "Остатки после декомпозиции",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=observed.index,
            y=observed,
            mode="lines",
            line=dict(color="#596275", width=1.7),
            name="Ряд",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=observed.index,
            y=trend,
            mode="lines",
            line=dict(color="#1f5f8b", width=2.8),
            name="Истинный тренд",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=observed.index,
            y=seasonal,
            mode="lines",
            line=dict(color="#8c96a6", width=2.0, dash="dot"),
            name="Истинная сезонность",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=correct.seasonal.index,
            y=correct.seasonal,
            mode="lines",
            line=dict(color="#2f80ed", width=2.4),
            name="m=12",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=wrong.seasonal.index,
            y=wrong.seasonal,
            mode="lines",
            line=dict(color="#c46a1d", width=2.4),
            name="m=6",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=correct.resid.index,
            y=correct.resid,
            mode="lines",
            line=dict(color="#2f80ed", width=2.0),
            name="Остаток: m=12",
            showlegend=False,
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=wrong.resid.index,
            y=wrong.resid,
            mode="lines",
            line=dict(color="#c46a1d", width=2.0),
            name="Остаток: m=6",
            showlegend=False,
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.add_hline(y=0, line_width=1, line_color="#c6cbd3", row=2, col=1)
    fig.add_hline(y=0, line_width=1, line_color="#c6cbd3", row=3, col=1)

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=760,
        margin=dict(l=76, r=34, t=104, b=58),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.065,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
        font=dict(family="Arial, sans-serif", size=16, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    fig.update_annotations(font=dict(size=16, color="#243746"))
    fig.update_xaxes(
        title_text="Время",
        title_font=dict(size=17),
        tickfont=dict(size=12),
        gridcolor="#edf0f4",
        row=3,
        col=1,
    )

    for row in range(1, 4):
        fig.update_yaxes(
            zeroline=True,
            zerolinecolor="#c6cbd3",
            gridcolor="#edf0f4",
            tickfont=dict(size=12),
            row=row,
            col=1,
        )

    fig.update_yaxes(title_text="Значение", row=1, col=1)
    fig.update_yaxes(title_text="Эффект", row=2, col=1)
    fig.update_yaxes(title_text="Остаток", row=3, col=1)

    pio.write_image(fig, output_path, width=1100, height=760, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
