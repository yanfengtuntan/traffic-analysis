from __future__ import annotations

from datetime import timedelta

import streamlit as st

from src.charts import intraday_chart, line_chart, weekly_chart
from src.config import AGGREGATIONS, DATASETS
from src.data_loader import build_region_labels, dataset_metrics, load_geojson, load_traffic
from src.maps import aggregate_map_values, choropleth_map


def compact_value(value: float) -> str:
    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.1f}亿"
    if abs(value) >= 10_000:
        return f"{value / 10_000:.0f}万"
    return f"{value:,.2f}"


st.title("🗺️ 探索性分析")
st.caption("所有图表和地图都由当前选择的数据集、区域和时间范围实时计算。")

with st.sidebar:
    st.subheader("分析条件")
    dataset_key = st.selectbox(
        "数据集",
        options=list(DATASETS),
        format_func=lambda key: DATASETS[key].label,
    )

config = DATASETS[dataset_key]
with st.spinner(f"正在读取 {config.label}……"):
    traffic = load_traffic(dataset_key)
    geojson = load_geojson(dataset_key)
labels = build_region_labels(config, geojson)
metrics = dataset_metrics(traffic, config)

with st.sidebar:
    default_region_index = (
        list(traffic.columns).index(config.default_region)
        if config.default_region in traffic.columns
        else 0
    )
    region = st.selectbox(
        "区域",
        options=list(traffic.columns),
        index=default_region_index,
        format_func=lambda region_id: labels.get(str(region_id), str(region_id)),
    )
    default_start = max(traffic.index.min(), traffic.index.max() - timedelta(days=6, hours=23, minutes=45))
    start_time, end_time = st.slider(
        "分析时间范围",
        min_value=traffic.index.min().to_pydatetime(),
        max_value=traffic.index.max().to_pydatetime(),
        value=(default_start.to_pydatetime(), traffic.index.max().to_pydatetime()),
        step=timedelta(minutes=config.interval_minutes),
        format="YYYY-MM-DD HH:mm",
    )
    aggregation_label = st.selectbox("地图时段聚合", options=list(AGGREGATIONS))

selected = traffic.loc[(traffic.index >= start_time) & (traffic.index <= end_time)]
if selected.empty:
    st.error("当前时间范围没有数据，请重新选择。")
    st.stop()

region_series = selected[region]
map_values = aggregate_map_values(selected, AGGREGATIONS[aggregation_label])

metric_columns = st.columns(5)
metric_columns[0].metric("区域数", f"{metrics['regions']:,}")
metric_columns[1].metric("当前时间点", f"{len(selected):,}")
metric_columns[2].metric("采样间隔", f"{metrics['interval_minutes']} 分钟")
metric_columns[3].metric(
    "区域平均值",
    compact_value(float(region_series.mean())),
    help=f"精确值：{region_series.mean():,.2f}",
)
metric_columns[4].metric(
    "区域峰值",
    compact_value(float(region_series.max())),
    help=f"精确值：{region_series.max():,.2f}",
)

region_name = labels.get(str(region), str(region))
st.plotly_chart(
    line_chart(region_series, f"{region_name} · 流量时间曲线"),
    width="stretch",
    config={"displaylogo": False},
)

map_tab, pattern_tab, data_tab = st.tabs(["空间分布", "周期模式", "数据预览"])
with map_tab:
    st.caption(
        f"地图数值由所选 {len(selected):,} 个时间点重新计算；没有使用 GeoJSON 中的静态 mean_traffic。"
    )
    st.plotly_chart(
        choropleth_map(geojson, config, map_values, labels, aggregation_label),
        width="stretch",
        config={"displaylogo": False},
    )
    geo_region_count = len(geojson.get("features", []))
    no_data_count = max(geo_region_count - traffic.shape[1], 0)
    if no_data_count:
        st.info(f"地图中有 {no_data_count} 个无 CSV 流量数据的区域，已用灰色标识，未当作 0。")

with pattern_tab:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(intraday_chart(region_series), width="stretch", config={"displaylogo": False})
    with right:
        st.plotly_chart(weekly_chart(region_series), width="stretch", config={"displaylogo": False})

with data_tab:
    preview = region_series.rename("流量值").to_frame()
    st.dataframe(preview, width="stretch", height=390)
    st.download_button(
        "导出当前区域数据（CSV）",
        data=preview.to_csv(index=True).encode("utf-8-sig"),
        file_name=f"{dataset_key}_{region}_{start_time:%Y%m%d}_{end_time:%Y%m%d}.csv",
        mime="text/csv",
    )

