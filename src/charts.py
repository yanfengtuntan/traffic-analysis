from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


TEAL = "#0F766E"
AMBER = "#D97706"


def line_chart(series: pd.Series, title: str) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            name="流量值",
            line={"color": TEAL, "width": 1.8},
            hovertemplate="时间：%{x|%Y-%m-%d %H:%M}<br>流量值：%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title="时间",
        yaxis_title="流量值",
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        hovermode="x unified",
        height=390,
    )
    return figure


def intraday_chart(series: pd.Series) -> go.Figure:
    minute_of_day = series.index.hour * 60 + series.index.minute
    profile = series.groupby(minute_of_day).mean()
    labels = [f"{minute // 60:02d}:{minute % 60:02d}" for minute in profile.index]
    figure = go.Figure(
        go.Scatter(
            x=labels,
            y=profile.values,
            mode="lines",
            line={"color": AMBER, "width": 2.2},
            hovertemplate="时刻：%{x}<br>平均流量值：%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="平均日内模式",
        xaxis_title="一天中的时刻",
        yaxis_title="平均流量值",
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        height=340,
    )
    return figure


def weekly_chart(series: pd.Series) -> go.Figure:
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    profile = series.groupby(series.index.dayofweek).mean().reindex(range(7))
    figure = go.Figure(
        go.Bar(
            x=weekday_names,
            y=profile.values,
            marker_color=TEAL,
            hovertemplate="%{x}<br>平均流量值：%{y:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title="平均每周模式",
        xaxis_title="星期",
        yaxis_title="平均流量值",
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        height=340,
    )
    return figure

