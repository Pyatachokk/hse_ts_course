#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import MSTL


OUTPUT_NAME = "02_decompose_05_dota_players_stl_decomposition.png"
DATA_RELATIVE_PATH = Path("2025-spring/homeworks/hw2/dota_players.xlsx")


def find_repo_root(script_dir: Path) -> Path:
    for parent in script_dir.parents:
        if (parent / DATA_RELATIVE_PATH).exists():
            return parent
    raise FileNotFoundError(f"Cannot find {DATA_RELATIVE_PATH}")


def load_hourly_players(repo_root: Path) -> pd.Series:
    data = pd.read_excel(repo_root / DATA_RELATIVE_PATH, parse_dates=["DateTime"])
    data = data.sort_values("DateTime").set_index("DateTime")
    players = data["Players"].loc["2025-01-15 01:00":"2025-02-13 23:50"]
    return players.resample("1h").max().interpolate("time")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = find_repo_root(script_dir)
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    players = load_hourly_players(repo_root)
    result = MSTL(
        players,
        periods=(24, 24 * 7),
        stl_kwargs={"robust": True},
    ).fit()

    observed = players
    trend = result.trend
    daily = result.seasonal["seasonal_24"]
    weekly = result.seasonal["seasonal_168"]
    resid = result.resid
    largest_resid_time = resid.abs().idxmax()
    other_outliers = resid[resid.abs() > 40000].drop(index=largest_resid_time)

    components = [
        (observed, "Ряд: почасовой максимум", "#1f5f8b", "Игроки"),
        (trend, "Тренд", "#2f80ed", "Игроки"),
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

    fig.add_trace(
        go.Scatter(
            x=[largest_resid_time],
            y=[resid.loc[largest_resid_time]],
            mode="markers",
            marker=dict(color="#c43b3b", size=9, line=dict(color="white", width=1.5)),
            name="Финальный день FISSURE",
            hovertemplate="%{x|%d.%m %H:%M}<br>%{y:.0f}<extra></extra>",
        ),
        row=5,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=other_outliers.index,
            y=other_outliers,
            mode="markers",
            marker=dict(
                color="rgba(196,59,59,0.65)",
                size=6,
                line=dict(color="white", width=1.0),
            ),
            name="Другие выбросы",
            hovertemplate="%{x|%d.%m %H:%M}<br>%{y:.0f}<extra></extra>",
        ),
        row=5,
        col=1,
    )

    for day_start in pd.date_range(observed.index.min().normalize(), observed.index.max().normalize(), freq="D"):
        fig.add_vline(x=day_start, line_width=0.5, line_color="#e2e7ef")

    fig.add_annotation(
        x=largest_resid_time,
        y=resid.loc[largest_resid_time],
        text="Финальный день<br>FISSURE Playground",
        showarrow=True,
        arrowhead=2,
        ax=78,
        ay=-92,
        font=dict(size=12, color="#c43b3b"),
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor="rgba(196,59,59,0.35)",
        borderpad=3,
        arrowcolor="#c43b3b",
        row=5,
        col=1,
    )

    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=760,
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
        dtick=24 * 60 * 60 * 1000 * 4,
        gridcolor="#edf0f4",
        row=len(components),
        col=1,
    )
    for row in range(1, len(components)):
        fig.update_xaxes(showticklabels=False, gridcolor="#edf0f4", row=row, col=1)

    pio.write_image(fig, output_path, width=1100, height=760, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
