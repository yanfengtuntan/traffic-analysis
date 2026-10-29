from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from src.config import DatasetConfig


CLUSTER_COLORS = [
    "#0F766E",
    "#D97706",
    "#2563EB",
    "#9333EA",
    "#DC2626",
    "#65A30D",
    "#0891B2",
    "#DB2777",
    "#7C3AED",
    "#475569",
]


def aggregate_map_values(frame: pd.DataFrame, method: str) -> pd.Series:
    if frame.empty:
        raise ValueError("当前时间范围没有数据。")
    if method == "mean":
        return frame.mean(axis=0)
    if method == "sum":
        return frame.sum(axis=0)
    if method == "max":
        return frame.max(axis=0)
    raise ValueError(f"不支持的聚合方式：{method}")


def choropleth_map(
    geojson: dict,
    config: DatasetConfig,
    values: pd.Series,
    labels: dict[str, str],
    aggregation_label: str,
) -> go.Figure:
    values = values.copy()
    values.index = values.index.astype(str)
    geo_ids = {
        str((feature.get("properties") or {}).get(config.geo_key))
        for feature in geojson.get("features", [])
        if (feature.get("properties") or {}).get(config.geo_key) is not None
    }
    no_data_ids = sorted(geo_ids - set(values.index))

    figure = go.Figure()
    if no_data_ids:
        figure.add_trace(
            go.Choroplethmap(
                geojson=geojson,
                featureidkey=f"properties.{config.geo_key}",
                locations=no_data_ids,
                z=[0] * len(no_data_ids),
                text=[labels.get(region_id, region_id) for region_id in no_data_ids],
                colorscale=[[0, "#D1D5DB"], [1, "#D1D5DB"]],
                showscale=False,
                marker={"opacity": 0.75, "line": {"width": 0.8, "color": "white"}},
                name="无数据",
                hovertemplate="%{text}<br>无流量数据<extra></extra>",
            )
        )

    figure.add_trace(
        go.Choroplethmap(
            geojson=geojson,
            featureidkey=f"properties.{config.geo_key}",
            locations=list(values.index),
            z=list(values.values),
            text=[labels.get(region_id, region_id) for region_id in values.index],
            colorscale="Tealgrn",
            colorbar={"title": "流量值", "thickness": 14},
            marker={"opacity": 0.78, "line": {"width": 0.6, "color": "white"}},
            name="有数据区域",
            hovertemplate="%{text}<br>流量值：%{z:,.2f}<extra></extra>",
        )
    )
    figure.update_layout(
        title=f"空间分布（{aggregation_label}）",
        map={
            "style": "carto-positron",
            "center": {"lat": config.center_lat, "lon": config.center_lon},
            "zoom": config.zoom,
        },
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        height=560,
        legend={"orientation": "h", "y": 0.01, "x": 0.01},
    )
    return figure


def cluster_choropleth_map(
    geojson: dict,
    config: DatasetConfig,
    assignments: pd.Series,
    labels: dict[str, str],
) -> go.Figure:
    from src.clustering import cluster_display_name

    assignments = assignments.copy()
    assignments.index = assignments.index.astype(str)
    geo_ids = {
        str((feature.get("properties") or {}).get(config.geo_key))
        for feature in geojson.get("features", [])
        if (feature.get("properties") or {}).get(config.geo_key) is not None
    }
    no_data_ids = sorted(geo_ids - set(assignments.index))
    cluster_values = sorted(int(value) for value in assignments.unique())
    cluster_codes = {cluster: position for position, cluster in enumerate(cluster_values)}
    z = [cluster_codes[int(value)] for value in assignments.values]
    count = len(cluster_values)
    colors = ["#6B7280" if cluster == -1 else CLUSTER_COLORS[cluster_codes[cluster] % len(CLUSTER_COLORS)] for cluster in cluster_values]
    colorscale: list[list[object]] = []
    if count == 1:
        colorscale = [[0, colors[0]], [1, colors[0]]]
    else:
        for position, color in enumerate(colors):
            lower = max(0.0, (position - 0.5) / (count - 1))
            upper = min(1.0, (position + 0.5) / (count - 1))
            colorscale.extend([[lower, color], [upper, color]])

    figure = go.Figure()
    if no_data_ids:
        figure.add_trace(
            go.Choroplethmap(
                geojson=geojson,
                featureidkey=f"properties.{config.geo_key}",
                locations=no_data_ids,
                z=[0] * len(no_data_ids),
                text=[labels.get(region_id, region_id) for region_id in no_data_ids],
                colorscale=[[0, "#D1D5DB"], [1, "#D1D5DB"]],
                showscale=False,
                marker={"opacity": 0.75, "line": {"width": 0.8, "color": "white"}},
                name="无数据",
                hovertemplate="%{text}<br>无流量数据<extra></extra>",
            )
        )

    cluster_names = [cluster_display_name(int(value)) for value in assignments.values]
    figure.add_trace(
        go.Choroplethmap(
            geojson=geojson,
            featureidkey=f"properties.{config.geo_key}",
            locations=list(assignments.index),
            z=z,
            zmin=0,
            zmax=max(count - 1, 1),
            text=[labels.get(region_id, region_id) for region_id in assignments.index],
            customdata=cluster_names,
            colorscale=colorscale,
            colorbar={
                "title": "聚类",
                "tickvals": list(range(count)),
                "ticktext": [cluster_display_name(cluster) for cluster in cluster_values],
                "thickness": 14,
            },
            marker={"opacity": 0.82, "line": {"width": 0.65, "color": "white"}},
            hovertemplate="%{text}<br>%{customdata}<extra></extra>",
            name="聚类区域",
        )
    )
    figure.update_layout(
        title="区域时间模式聚类地图",
        map={
            "style": "carto-positron",
            "center": {"lat": config.center_lat, "lon": config.center_lon},
            "zoom": config.zoom,
        },
        margin={"l": 0, "r": 0, "t": 50, "b": 0},
        height=560,
        legend={"orientation": "h", "y": 0.01, "x": 0.01},
    )
    return figure

