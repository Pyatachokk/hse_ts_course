import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.stattools import acf, pacf


COLORS = [
    '#4A6CF7', '#E4572E', '#17BEBB', '#FFC914', '#6A4C93',
    '#2E86DE', '#FF6B6B', '#1DD1A1', '#A55EEA'
]

LINE_STYLE_BASE = dict(width=4, shape='spline', smoothing=1.3)


def plot_ts(time_series_list, title_text, lags=30, show_ts=True, show_pacf=False,
            show_acf=False, show_diff=False, show_diff_pacf=False, show_diff_acf=False, one=False):
    if one:
        fig = go.Figure()

        for i, ts in enumerate(time_series_list):
            dt_r = ts['data']
            ts_name = ts['name']

            color = COLORS[i % len(COLORS)]

            if show_ts:
                fig.add_trace(go.Scatter(
                    x=dt_r.index,
                    y=dt_r,
                    mode='lines',
                    line={**LINE_STYLE_BASE, 'color': color},
                    name=ts_name
                ))

        fig.update_layout(
            title_text=title_text,
            width=1200,
            height=700,
            showlegend=True,
            legend=dict(
                x=0,
                y=1,
                orientation='h',
                bgcolor='rgba(255,255,255,0.5)',
                bordercolor='black',
                borderwidth=1
            )
        )

        fig.show()
        return

    analyses_count = sum([show_ts, show_pacf, show_acf, show_diff, show_diff_pacf, show_diff_acf])

    total_plots = analyses_count * len(time_series_list)
    subplot_titles = []
    for ts in time_series_list:
        name = ts['name']
        if show_ts: subplot_titles.append(f'Time Series: {name}')
        if show_pacf: subplot_titles.append(f'PACF: {name}')
        if show_acf: subplot_titles.append(f'ACF: {name}')
        if show_diff: subplot_titles.append(f'Difference: {name}')
        if show_diff_pacf: subplot_titles.append(f'Diff PACF: {name}')
        if show_diff_acf: subplot_titles.append(f'Diff ACF: {name}')

    fig = make_subplots(
        rows=total_plots,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=subplot_titles
    )

    current_row = 1

    for i, ts in enumerate(time_series_list):
        dt_r = ts['data']
        name = ts['name']
        color = COLORS[i % len(COLORS)]

        if show_ts:
            fig.add_trace(go.Scatter(
                x=dt_r.index,
                y=dt_r,
                mode='lines',
                line={**LINE_STYLE_BASE, 'color': color},
                name=f'TS: {name}'
            ), row=current_row, col=1)
            current_row += 1

        if show_pacf:
            pacf_values = pacf(dt_r, nlags=lags, method='ywmle')
            fig.add_trace(go.Scatter(
                x=list(range(len(pacf_values))),
                y=pacf_values,
                mode='lines',
                line=dict(width=3, color='#E4572E'),
                showlegend=False
            ), row=current_row, col=1)
            current_row += 1

        if show_acf:
            acf_values = acf(dt_r, nlags=lags, fft=True)
            fig.add_trace(go.Scatter(
                x=list(range(len(acf_values))),
                y=acf_values,
                mode='lines',
                line=dict(width=3, color='#17BEBB'),
                showlegend=False
            ), row=current_row, col=1)
            current_row += 1

        if show_diff:
            diff = dt_r.diff().dropna()
            fig.add_trace(go.Scatter(
                x=diff.index,
                y=diff,
                mode='lines',
                line=dict(width=4, shape='spline', smoothing=1.3, color='#2E86DE'),
                name=f'Diff: {name}'
            ), row=current_row, col=1)
            current_row += 1

        if show_diff_pacf and show_diff:
            diff_pacf_vals = pacf(diff, nlags=lags, method='ywmle')
            fig.add_trace(go.Scatter(
                x=list(range(len(diff_pacf_vals))),
                y=diff_pacf_vals,
                mode='lines',
                line=dict(width=3, color='#E4572E'),
                showlegend=False
            ), row=current_row, col=1)
            current_row += 1

        if show_diff_acf and show_diff:
            diff_acf_vals = acf(diff, nlags=lags, fft=True)
            fig.add_trace(go.Scatter(
                x=list(range(len(diff_acf_vals))),
                y=diff_acf_vals,
                mode='lines',
                line=dict(width=3, color='#17BEBB'),
                showlegend=False
            ), row=current_row, col=1)
            current_row += 1

    fig.update_layout(
        title_text=title_text,
        width=1200,
        height=260 * total_plots,
        showlegend=False,
        margin=dict(l=30, r=30, t=60, b=30)
    )

    fig.show()
