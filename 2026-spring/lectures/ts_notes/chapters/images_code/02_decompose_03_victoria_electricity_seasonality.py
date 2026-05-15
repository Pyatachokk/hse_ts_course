#!/usr/bin/env python3
from io import StringIO
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


OUTPUT_NAME = "02_decompose_03_victoria_electricity_seasonality.png"
DATA_URL = (
    "https://raw.githubusercontent.com/skforecast/skforecast-datasets/"
    "main/data/vic_electricity.csv"
)


def load_hourly_demand() -> pd.DataFrame:
    with urlopen(DATA_URL, timeout=30) as response:
        csv_text = response.read().decode("utf-8")

    data = pd.read_csv(StringIO(csv_text), parse_dates=["Time"])
    data = data.set_index("Time").sort_index()

    hourly = data[["Demand"]].resample("1h").mean()
    hourly["date"] = hourly.index.date
    hourly["weekday"] = hourly.index.dayofweek
    hourly["is_weekend"] = hourly["weekday"] >= 5
    return hourly


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    hourly = load_hourly_demand()
    window = hourly.loc["2014-01-06":"2014-01-19"].copy()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=window.index,
            y=window["Demand"],
            mode="lines",
            line=dict(color="#1f5f8b", width=2.4),
            name="Потребление",
            hovertemplate="%{x|%d.%m %H:%M}<br>%{y:.0f} МВт·ч<extra></extra>",
        )
    )

    weekend_dates = sorted(window.loc[window["is_weekend"], "date"].unique())
    for date_value in weekend_dates:
        start = pd.Timestamp(date_value, tz=window.index.tz)
        end = start + pd.Timedelta(days=1)
        fig.add_vrect(
            x0=start,
            x1=end,
            fillcolor="#f3d7ae",
            opacity=0.26,
            line_width=0,
            layer="below",
        )

    for day_start in pd.date_range(window.index.min().normalize(), window.index.max().normalize(), freq="D"):
        fig.add_vline(x=day_start, line_width=0.7, line_color="#d8dde6", layer="below")

    fig.add_annotation(
        x=window.index[33],
        y=window["Demand"].max() * 1.02,
        text="Суточный ритм: пики повторяются каждый день",
        showarrow=False,
        font=dict(size=18, color="#243746"),
        align="left",
    )
    fig.add_annotation(
        x=pd.Timestamp("2014-01-12", tz=window.index.tz),
        y=window["Demand"].min() * 0.96,
        text="Выходные",
        showarrow=False,
        font=dict(size=17, color="#7a4e13"),
        align="center",
    )

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=520,
        margin=dict(l=76, r=28, t=46, b=70),
        showlegend=False,
        font=dict(family="Arial, sans-serif", size=16, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(
        title_text="Время",
        tickformat="%d.%m",
        dtick=24 * 60 * 60 * 1000,
        gridcolor="#edf0f4",
        tickangle=0,
    )
    fig.update_yaxes(
        title_text="Потребление, МВт·ч",
        gridcolor="#edf0f4",
        zeroline=False,
    )

    pio.write_image(fig, output_path, width=1100, height=520, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
