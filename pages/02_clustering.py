from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.clustering import cluster_display_name, run_clustering
from src.config import DATASETS
from src.data_loader import build_region_labels, load_geojson, load_traffic
from src.maps import CLUSTER_COLORS, cluster_choropleth_map


st.title("🧩 聚类分析")
st.caption("根据区域的标准化时间模式识别相似区域；不同数据集始终分别聚类。")

with st.sidebar:
    st.subheader("聚类条件")
    dataset_key = st.selectbox(
        "数据集",
        options=list(DATASETS),
        format_func=lambda key: DATASETS[key].label,
    )

config = DATASETS[dataset_key]
traffic = load_traffic(dataset_key)
geojson = load_geojson(dataset_key)
labels = build_region_labels(config, geojson)

with st.sidebar:
    start_time, end_time = st.slider(
        "用于聚类的时间范围",
        min_value=traffic.index.min().to_pydatetime(),
        max_value=traffic.index.max().to_pydatetime(),
        value=(traffic.index.min().to_pydatetime(), traffic.index.max().to_pydatetime()),
        step=timedelta(minutes=config.interval_minutes),
        format="YYYY-MM-DD HH:mm",
        key=f"cluster_range_{dataset_key}",
    )
    feature_mode = st.selectbox("时间模式特征", ["日内模式", "周内小时模式"])
    algorithm = st.selectbox("聚类算法", ["K-means", "DBSCAN"])
    n_clusters = 4
    eps = 3.0
    min_samples = 5
    if algorithm == "K-means":
        n_clusters = st.slider("聚类数量 K", 2, 10, 4)
    else:
        eps = st.number_input("邻域半径 eps", min_value=0.1, max_value=30.0, value=3.0, step=0.1)
        min_samples = int(st.number_input("最小样本数", min_value=2, max_value=50, value=5, step=1))
    run_clicked = st.button("运行真实聚类", type="primary", width="stretch")

st.info(
    "聚类只描述流量曲线形状，例如“模式簇 1”。没有真实功能区标签时，不会直接宣称某一簇就是办公区或居住区。"
)

if not run_clicked:
    st.markdown("调整左侧参数后点击 **运行真实聚类**。日内模式关注一天内的形状，周内小时模式同时保留星期差异。")
    st.stop()

selected = traffic.loc[(traffic.index >= start_time) & (traffic.index <= end_time)]
with st.status("聚类执行中……", expanded=True) as status:
    st.write("正在按区域聚合时间模式。")
    st.write("正在对每个区域自身的模式做均值—标准差标准化，以比较形状而非绝对量级。")
    result = run_clustering(
        selected,
        feature_mode=feature_mode,
        algorithm=algorithm,
        n_clusters=n_clusters,
        eps=eps,
        min_samples=min_samples,
    )
    st.write("正在计算二维投影、代表曲线和聚类地图。")
    status.update(label="聚类完成", state="complete", expanded=False)

cluster_counts = result.assignments.value_counts().sort_index()
non_noise_clusters = len([cluster for cluster in cluster_counts.index if int(cluster) != -1])
noise_count = int(cluster_counts.get(-1, 0))
metric_columns = st.columns(4)
metric_columns[0].metric("区域数", f"{len(result.assignments):,}")
metric_columns[1].metric("有效聚类数", f"{non_noise_clusters:,}")
metric_columns[2].metric("噪声区域", f"{noise_count:,}")
metric_columns[3].metric(
    "轮廓系数",
    "不可计算" if result.silhouette is None else f"{result.silhouette:.3f}",
    help="越接近 1，簇内越紧密且簇间越分离；DBSCAN 计算时排除噪声点。",
)
st.caption(f"真实执行耗时：{result.elapsed_seconds:.3f} 秒。")

map_tab, profile_tab, scatter_tab, table_tab = st.tabs(["聚类地图", "代表曲线", "二维分布", "区域明细"])
with map_tab:
    st.plotly_chart(
        cluster_choropleth_map(geojson, config, result.assignments, labels),
        width="stretch",
        config={"displaylogo": False},
    )
    no_data_count = len(geojson.get("features", [])) - len(result.assignments)
    if no_data_count > 0:
        st.caption(f"灰色区域为 GeoJSON 中没有 CSV 流量数据的 {no_data_count} 个区域。")

with profile_tab:
    profile_figure = go.Figure()
    for color_index, (cluster, values) in enumerate(result.representative_profiles.iterrows()):
        color = "#6B7280" if int(cluster) == -1 else CLUSTER_COLORS[color_index % len(CLUSTER_COLORS)]
        profile_figure.add_trace(
            go.Scatter(
                x=result.profile_labels,
                y=values.values,
                mode="lines",
                name=cluster_display_name(int(cluster)),
                line={"width": 2.2, "color": color},
            )
        )
    profile_figure.update_layout(
        title=f"各簇代表曲线 · {feature_mode}",
        xaxis_title="时间槽",
        yaxis_title="区域内标准化流量",
        hovermode="x unified",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    st.plotly_chart(profile_figure, width="stretch", config={"displaylogo": False})

with scatter_tab:
    scatter_figure = go.Figure()
    for color_index, cluster in enumerate(sorted(result.embedding["聚类"].unique())):
        subset = result.embedding[result.embedding["聚类"] == cluster]
        color = "#6B7280" if int(cluster) == -1 else CLUSTER_COLORS[color_index % len(CLUSTER_COLORS)]
        scatter_figure.add_trace(
            go.Scatter(
                x=subset["主成分 1"],
                y=subset["主成分 2"],
                text=[labels.get(region, region) for region in subset["区域"]],
                mode="markers",
                name=cluster_display_name(int(cluster)),
                marker={"size": 9, "opacity": 0.78, "color": color},
                hovertemplate="%{text}<br>PC1=%{x:.2f}<br>PC2=%{y:.2f}<extra></extra>",
            )
        )
    scatter_figure.update_layout(
        title="PCA 二维投影（仅用于展示）",
        xaxis_title="主成分 1",
        yaxis_title="主成分 2",
        height=430,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    st.plotly_chart(scatter_figure, width="stretch", config={"displaylogo": False})

with table_tab:
    details = pd.DataFrame(
        {
            "区域编码/名称": result.assignments.index,
            "区域显示名": [labels.get(region, region) for region in result.assignments.index],
            "聚类编号": result.assignments.values,
            "模式描述": [cluster_display_name(int(value)) for value in result.assignments.values],
        }
    ).sort_values(["聚类编号", "区域编码/名称"])
    st.dataframe(details, width="stretch", hide_index=True)
    st.download_button(
        "导出聚类结果（CSV）",
        data=details.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"clusters_{dataset_key}_{algorithm}.csv",
        mime="text/csv",
    )

