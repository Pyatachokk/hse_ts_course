#!/usr/bin/env python3
from io import StringIO
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import MSTL


OUTPUT_NAME = "02_decompose_04_victoria_electricity_mstl_decomposition.png"
DATA_URL = (
    "https://raw.githubusercontent.com/skforecast/skforecast-datasets/"
    "main/data/vic_electricity.csv"
)


def load_hourly_demand() -> pd.Series:
    with urlopen(DATA_URL, timeout=30) as response:
        csv_text = response.read().decode("utf-8")

    data = pd.read_csv(StringIO(csv_text), parse_dates=["Time"])
    data = data.set_index("Time").sort_index()
    return data["Demand"].resample("1h").mean()


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    hourly = load_hourly_demand().loc["2013-12-01":"2014-02-28"]
    result = MSTL(
        hourly,
        periods=(24, 24 * 7),
        stl_kwargs={"robust": True},
    ).fit()

    window = slice("2014-01-06", "2014-01-19")
    observed = hourly.loc[window]
    trend = result.trend.loc[window]
    daily = result.seasonal["seasonal_24"].loc[window]
    weekly = result.seasonal["seasonal_168"].loc[window]
    resid = result.resid.loc[window]

    components = [
        (observed, "Ряд", "#1f5f8b", "МВт·ч"),
        (trend, "Тренд", "#2f80ed", "МВт·ч"),
        (daily, "Суточная сезонность", "#c46a1d", "Эффект"),
        (weekly, "Недельная сезонность", "#6f58a8", "Эффект"),
        (resid, "Остаток", "#596275", "Ошибка"),
    ]

    fig = make_subplots(
        rows=len(components),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.045,
        row_heights=[0.26, 0.20, 0.18, 0.18, 0.18],
        subplot_titles=[name for _, name, _, _ in components],
    )

    for row, (values, name, color, _) in enumerate(components, start=1):
        fig.add_trace(
            go.Scatter(
                x=values.index,
                y=values,
                mode="lines",
                line=dict(color=color, width=2.2),
                name=name,
                hovertemplate="%{x|%d.%m %H:%M}<br>%{y:.0f}<extra></extra>",
            ),
            row=row,
            col=1,
        )

    for day_start in pd.date_range(observed.index.min().normalize(), observed.index.max().normalize(), freq="D"):
        fig.add_vline(x=day_start, line_width=0.6, line_color="#e2e7ef")

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=820,
        margin=dict(l=78, r=28, t=74, b=58),
        showlegend=False,
        font=dict(family="Arial, sans-serif", size=15, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_annotations(font=dict(size=16, color="#243746"))

    for row, (_, _, _, y_title) in enumerate(components, start=1):
        fig.update_yaxes(
            title_text=y_title,
            gridcolor="#edf0f4",
            zeroline=True,
            zerolinecolor="#c6cbd3",
            tickfont=dict(size=11),
            row=row,
            col=1,
        )

    fig.update_xaxes(
        title_text="Время",
        tickformat="%d.%m",
        dtick=24 * 60 * 60 * 1000,
        gridcolor="#edf0f4",
        row=len(components),
        col=1,
    )
    for row in range(1, len(components)):
        fig.update_xaxes(showticklabels=False, gridcolor="#edf0f4", row=row, col=1)

    pio.write_image(fig, output_path, width=1100, height=820, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
