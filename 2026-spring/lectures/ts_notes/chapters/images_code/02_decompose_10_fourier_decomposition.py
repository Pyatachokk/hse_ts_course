#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


OUTPUT_NAME = "02_decompose_10_fourier_decomposition.png"


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    rng = np.random.default_rng(19)
    n_obs = 120
    t = np.arange(n_obs)
    index = pd.date_range("2015-01-01", periods=n_obs, freq="MS")

    trend = 42 + 0.13 * t + 1.7 * np.sin(2 * np.pi * t / 72 - 0.5)
    seasonal = (
        5.8 * np.sin(2 * np.pi * t / 12 - 0.7)
        + 2.0 * np.cos(4 * np.pi * t / 12 + 0.25)
    )
    noise = rng.normal(0, 0.85, size=n_obs)
    observed = trend + seasonal + noise

    trend_fit = np.polyval(np.polyfit(t, observed, deg=2), t)
    detrended = observed - trend_fit
    spectrum = np.fft.rfft(detrended)
    frequencies = np.fft.rfftfreq(n_obs, d=1)
    amplitudes = 2 * np.abs(spectrum) / n_obs
    amplitudes[0] = np.abs(spectrum[0]) / n_obs

    selected_periods = [12, 6]
    selected_frequencies = [1 / period for period in selected_periods]
    keep = np.zeros_like(spectrum, dtype=bool)
    for freq in selected_frequencies:
        keep[np.argmin(np.abs(frequencies - freq))] = True

    seasonal_spectrum = np.zeros_like(spectrum)
    seasonal_spectrum[keep] = spectrum[keep]
    seasonal_hat = np.fft.irfft(seasonal_spectrum, n=n_obs)
    residual = observed - trend_fit - seasonal_hat

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.16,
        row_heights=[0.32, 0.3, 0.38],
        subplot_titles=[
            "Исходный ряд: тренд, сезонность и шум",
            "Спектр DFT после удаления тренда",
            "Приближение сезонности выбранными гармониками",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=index,
            y=observed,
            mode="lines",
            line=dict(color="#596275", width=1.8),
            name="Ряд",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=index,
            y=trend_fit,
            mode="lines",
            line=dict(color="#1f5f8b", width=2.7),
            name="Оценка тренда",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    nonzero = frequencies > 0
    fig.add_trace(
        go.Bar(
            x=frequencies[nonzero],
            y=amplitudes[nonzero],
            marker=dict(color="#9aa8b8"),
            name="Амплитуда",
            hovertemplate="Частота %{x:.3f}<br>Амплитуда %{y:.2f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=selected_frequencies,
            y=[
                amplitudes[np.argmin(np.abs(frequencies - freq))]
                for freq in selected_frequencies
            ],
            mode="markers+text",
            marker=dict(color="#c44e52", size=11),
            text=["1/12", "1/6"],
            textposition="top center",
            textfont=dict(size=15, color="#7f1d1d"),
            name="Выбранные частоты",
            hovertemplate="Частота %{x:.3f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=index,
            y=detrended,
            mode="lines",
            line=dict(color="#b0b8c4", width=1.6, dash="dot"),
            name="Ряд без тренда",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=index,
            y=seasonal_hat,
            mode="lines",
            line=dict(color="#2f80ed", width=2.8),
            name="Fourier-сезонность",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=index,
            y=residual,
            mode="lines",
            line=dict(color="#c46a1d", width=1.6),
            name="Остаток",
            hovertemplate="%{x|%m.%Y}<br>%{y:.2f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.add_vline(
        x=1 / 12,
        line=dict(color="#c44e52", width=1.5, dash="dash"),
        row=2,
        col=1,
    )
    fig.add_vline(
        x=1 / 6,
        line=dict(color="#c44e52", width=1.5, dash="dash"),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_width=1, line_color="#c6cbd3", row=3, col=1)

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=940,
        margin=dict(l=78, r=34, t=110, b=72),
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
        bargap=0.08,
    )

    fig.update_annotations(font=dict(size=16, color="#243746"))
    fig.update_xaxes(
        title_text="Время",
        title_standoff=14,
        title_font=dict(size=16),
        tickfont=dict(size=12),
        gridcolor="#edf0f4",
        row=1,
        col=1,
    )
    fig.update_xaxes(
        title_text="Частота, циклов на наблюдение",
        range=[0, 0.22],
        title_standoff=14,
        title_font=dict(size=16),
        tickfont=dict(size=12),
        gridcolor="#edf0f4",
        row=2,
        col=1,
    )
    fig.update_xaxes(
        title_text="Время",
        title_standoff=14,
        title_font=dict(size=16),
        tickfont=dict(size=12),
        gridcolor="#edf0f4",
        row=3,
        col=1,
    )

    fig.update_yaxes(title_text="Значение", gridcolor="#edf0f4", row=1, col=1)
    fig.update_yaxes(title_text="Амплитуда", gridcolor="#edf0f4", row=2, col=1)
    fig.update_yaxes(title_text="Эффект", gridcolor="#edf0f4", row=3, col=1)

    for row in range(1, 4):
        fig.update_yaxes(
            zeroline=True,
            zerolinecolor="#c6cbd3",
            tickfont=dict(size=12),
            row=row,
            col=1,
        )

    pio.write_image(fig, output_path, width=1100, height=940, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
