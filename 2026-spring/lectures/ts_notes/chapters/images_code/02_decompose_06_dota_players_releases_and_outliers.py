#!/usr/bin/env python3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL


OUTPUT_NAME = "02_decompose_06_dota_players_releases_and_outliers.png"
DATA_RELATIVE_PATH = Path("2025-spring/homeworks/hw2/dota_players.xlsx")


def find_repo_root(script_dir: Path) -> Path:
    for parent in script_dir.parents:
        if (parent / DATA_RELATIVE_PATH).exists():
            return parent
    raise FileNotFoundError(f"Cannot find {DATA_RELATIVE_PATH}")


def load_daily_players(repo_root: Path) -> pd.Series:
    data = pd.read_excel(repo_root / DATA_RELATIVE_PATH, parse_dates=["DateTime"])
    data = data.sort_values("DateTime").set_index("DateTime")
    daily = data["Players"].resample("1D").max()
    return daily.loc["2024-01-01":"2025-02-13"]


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = find_repo_root(script_dir)
    images_dir = script_dir.parent / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    output_path = images_dir / OUTPUT_NAME

    daily = load_daily_players(repo_root)
    result = STL(daily, period=7, robust=True).fit()
    trend = result.trend
    seasonal = result.seasonal
    resid = result.resid

    releases = [
        ("2024-04-18", "Crownfall Act I", 1015000),
        ("2024-05-22", "7.36 и Act II", 965000),
        ("2024-07-09", "Crownfall Act III", 1015000),
        ("2024-08-23", "Ringmaster", 965000),
        ("2024-11-07", "Kez и Act IV", 1015000),
        ("2025-02-06", "Финал Crownfall", 965000),
    ]
    outliers = [
        ("2024-04-21", "Всплеск\nпосле Act I"),
        ("2024-05-23", "Пик\nпосле 7.36"),
        ("2024-07-10", "Всплеск\nAct III"),
        ("2024-11-08", "Kez / Act IV"),
        ("2024-12-31", "Календарный\nпровал"),
    ]

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.50, 0.22, 0.28],
        subplot_titles=[
            "Дневной максимум и сглаженный тренд",
            "Недельная сезонность",
            "Остатки после удаления недельной сезонности и тренда",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=daily.index,
            y=daily,
            mode="lines",
            line=dict(color="#8c96a6", width=1.4),
            name="Дневной максимум",
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:.0f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=trend.index,
            y=trend,
            mode="lines",
            line=dict(color="#1f5f8b", width=3.0),
            name="Тренд STL",
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:.0f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=seasonal.index,
            y=seasonal,
            mode="lines",
            line=dict(color="#c46a1d", width=1.9),
            name="Недельная сезонность",
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=resid.index,
            y=resid,
            mode="lines",
            line=dict(color="#596275", width=1.7),
            name="Остаток",
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:.0f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    for date_text, label, y_position in releases:
        date = pd.Timestamp(date_text)
        fig.add_vline(
            x=date,
            line_width=1.2,
            line_dash="dot",
            line_color="#b45f3c",
            row=1,
            col=1,
        )
        fig.add_annotation(
            x=date,
            y=y_position,
            text=label,
            showarrow=False,
            xanchor="center",
            yanchor="middle",
            font=dict(size=10, color="#8f432b"),
            bgcolor="rgba(255,255,255,0.90)",
            bordercolor="rgba(180,95,60,0.30)",
            borderpad=2,
            row=1,
            col=1,
        )

    outlier_dates = [pd.Timestamp(date_text) for date_text, _ in outliers]
    outlier_values = [resid.loc[date] for date in outlier_dates]
    fig.add_trace(
        go.Scatter(
            x=outlier_dates,
            y=outlier_values,
            mode="markers",
            marker=dict(color="#c43b3b", size=8, line=dict(color="white", width=1.2)),
            name="Выбросы",
            hovertemplate="%{x|%d.%m.%Y}<br>%{y:.0f}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    annotation_offsets = {
        "2024-04-21": (40, -42),
        "2024-05-23": (52, -46),
        "2024-07-10": (50, -44),
        "2024-11-08": (52, -38),
        "2024-12-31": (-58, -54),
    }
    for date_text, label in outliers:
        date = pd.Timestamp(date_text)
        ax, ay = annotation_offsets[date_text]
        fig.add_annotation(
            x=date,
            y=resid.loc[date],
            text=label,
            showarrow=True,
            arrowhead=2,
            ax=ax,
            ay=ay,
            font=dict(size=11, color="#c43b3b"),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor="rgba(196,59,59,0.35)",
            borderpad=3,
            arrowcolor="#c43b3b",
            row=3,
            col=1,
        )

    fig.add_hline(y=0, line_width=1.1, line_color="#c6cbd3", row=2, col=1)
    fig.add_hline(y=0, line_width=1.1, line_color="#c6cbd3", row=3, col=1)
    fig.update_layout(
        template="plotly_white",
        width=1100,
        height=880,
        margin=dict(l=78, r=28, t=72, b=58),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="right", x=1),
        font=dict(family="Arial, sans-serif", size=15, color="#243746"),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_annotations(font=dict(size=15, color="#243746"))

    fig.update_yaxes(
        title_text="Игроки",
        gridcolor="#edf0f4",
        tickformat="~s",
        range=[520000, 1040000],
        row=1,
        col=1,
    )
    fig.update_yaxes(
        title_text="Эффект",
        gridcolor="#edf0f4",
        zeroline=True,
        zerolinecolor="#c6cbd3",
        tickformat="~s",
        row=2,
        col=1,
    )
    fig.update_yaxes(
        title_text="Остаток",
        gridcolor="#edf0f4",
        zeroline=True,
        zerolinecolor="#c6cbd3",
        tickformat="~s",
        row=3,
        col=1,
    )
    fig.update_xaxes(
        title_text="Дата",
        tickformat="%m.%Y",
        gridcolor="#edf0f4",
        range=[pd.Timestamp("2024-01-01"), pd.Timestamp("2025-02-20")],
        row=3,
        col=1,
    )
    fig.update_xaxes(showticklabels=False, gridcolor="#edf0f4", row=1, col=1)
    fig.update_xaxes(showticklabels=False, gridcolor="#edf0f4", row=2, col=1)

    pio.write_image(fig, output_path, width=1100, height=880, scale=2)
    print(f"Saved {output_path}")


if __name__ == "__main__":
    main()
