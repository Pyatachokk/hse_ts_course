#!/usr/bin/env python3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


OUTPUT_NAME = "02_decompose_09_mstl_seasonal_overlap.png"


def month_end_window(date: pd.Timestamp) -> bool:
    month_end = date + pd.offsets.MonthEnd(0)
    days_to_end = (month_end - date).days
    return 0 <= days_to_end <= 2


def add_overlap_windows(fig: go.Figure, dates: pd.DatetimeIndex, mask: np.ndarray) -> None:
    starts = []
    ends = []
    in_window = False
    current_start = None

    for i, active in enumerate(mask):
        if active and not in_window:
            current_start = dates[i] - pd.Timedelta(hours=12)
            in_window = True
        if in_window and (not active or i == len(mask) - 1):
            end_index = i if active and i == len(mask) - 1 else i - 1
            starts.append(current_start)
            ends.append(dates[end_index] + pd.Timedelta(hours=12))
            in_window = False

    for start, end in zip(starts, ends):
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="#f1c40f",
            opacity=0.18,
            line_width=0,
            layer="below",
            row=1,
            col=1,
        )
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="#f1c40f",
            opacity=0.18,
            line_width=0,
            layer="below",
            row=2,
            col=1,
        )


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    dates = pd.date_range("2024-02-15", "2024-04-14", freq="D")
    is_weekend = dates.weekday >= 5
    is_month_end = np.array([month_end_window(date) for date in dates])

    weekly = np.where(is_weekend, 1.0, 0.0)
    monthly = np.where(is_month_end, 1.35, 0.0)
    total = weekly + monthly
    overlap = is_weekend & is_month_end

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.13,
        row_heights=[0.53, 0.47],
        subplot_titles=[
            "Два календарных эффекта по отдельности",
            "В сумме совпадение выглядит как один сильный всплеск",
        ],
    )

    add_overlap_windows(fig, dates, overlap)

    common_hover = "%{x|%d.%m.%Y}<br>эффект: %{y:.2f}<extra></extra>"

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=weekly,
            mode="lines",
            line=dict(color="#2f80ed", width=2.8, shape="hv"),
            name="Конец недели",
            hovertemplate=common_hover,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=monthly,
            mode="lines",
            line=dict(color="#c46a1d", width=2.8, shape="hv"),
            name="Конец месяца",
            hovertemplate=common_hover,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=total,
            mode="lines",
            line=dict(color="#243746", width=3.0, shape="hv"),
            name="Сумма эффектов",
            hovertemplate=common_hover,
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=dates[overlap],
            y=total[overlap],
            mode="markers",
            marker=dict(
                color="#d62728",
                size=8,
                line=dict(color="white", width=1.4),
            ),
            name="Наложение",
            hovertemplate="%{x|%d.%m.%Y}<br>оба цикла активны<extra></extra>",
        ),
        row=2,
        col=1,
    )

    for date in pd.to_datetime(["2024-02-29", "2024-03-31"]):
        fig.add_vline(
            x=date,
            line_width=1.1,
            line_dash="dot",
            line_color="#8c96a6",
            row=1,
            col=1,
        )
        fig.add_vline(
            x=date,
            line_width=1.1,
            line_dash="dot",
            line_color="#8c96a6",
            row=2,
            col=1,
        )

    fig.add_annotation(
        x=pd.Timestamp("2024-04-04"),
        y=2.55,
        text="оба цикла активны",
        showarrow=False,
        font=dict(size=14, color="#8a3b12"),
        bgcolor="rgba(255,255,255,0.88)",
        bordercolor="#e7c7a6",
        borderwidth=1,
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_white",
        width=1050,
        height=560,
        margin=dict(l=76, r=34, t=92, b=64),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.055,
            xanchor="center",
            x=0.5,
            font=dict(size=13),
        ),
        font=dict(family="Arial, sans-serif", size=15, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )

    fig.update_annotations(font=dict(size=16, color="#243746"))
    fig.update_xaxes(
        title_text="Дата",
        tickformat="%d.%m",
        dtick=7 * 24 * 60 * 60 * 1000,
        title_font=dict(size=16),
        tickfont=dict(size=12),
        gridcolor="#edf0f4",
        row=2,
        col=1,
    )
    fig.update_xaxes(
        tickformat="%d.%m",
        dtick=7 * 24 * 60 * 60 * 1000,
        tickfont=dict(size=12),
        gridcolor="#edf0f4",
        row=1,
        col=1,
    )

    for row in (1, 2):
        fig.update_yaxes(
            title_text="Сезонный эффект",
            range=[-0.12, 2.85 if row == 2 else 1.55],
            tickvals=[0, 1, 1.35, 2.35] if row == 2 else [0, 1, 1.35],
            zeroline=True,
            zerolinecolor="#c6cbd3",
            gridcolor="#edf0f4",
            title_font=dict(size=16),
            tickfont=dict(size=12),
            row=row,
            col=1,
        )

    pio.write_image(fig, output_path, width=1050, height=560, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
