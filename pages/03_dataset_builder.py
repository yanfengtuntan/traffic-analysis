from datetime import timedelta

import streamlit as st

from src.config import DATASETS
from src.data_loader import build_region_labels, load_geojson, load_traffic
from src.forecasting import (
    ForecastSpec,
    build_windowed_data,
    default_split_bounds,
    first_sample_preview,
    spec_to_dict,
    split_summary,
)


def format_duration(minutes: int) -> str:
    duration = timedelta(minutes=minutes)
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes_left = remainder // 60
    parts = []
    if days:
        parts.append(f"{days} 天")
    if hours:
        parts.append(f"{hours} 小时")
    if minutes_left:
        parts.append(f"{minutes_left} 分钟")
    return " ".join(parts) or "0 分钟"


st.title("🪟 预测数据构建")
st.caption("按时间顺序划分数据，缩放器只在训练段拟合，再通过滑动窗口生成监督学习样本。")

dataset_key = st.selectbox(
    "数据集",
    options=list(DATASETS),
    format_func=lambda key: DATASETS[key].label,
)
config = DATASETS[dataset_key]
traffic = load_traffic(dataset_key)
geojson = load_geojson(dataset_key)
labels = build_region_labels(config, geojson)

default_region_index = list(traffic.columns).index(config.default_region) if config.default_region in traffic.columns else 0
region = st.selectbox(
    "区域",
    options=list(traffic.columns),
    index=default_region_index,
    format_func=lambda region_id: labels.get(str(region_id), str(region_id)),
)

default_input = 96 if dataset_key == "ZTE" else 144
left, right = st.columns(2)
with left:
    input_length = int(
        st.number_input("输入长度（时间点）", min_value=1, max_value=1000, value=default_input, step=1)
    )
with right:
    output_length = int(
        st.number_input("输出长度（时间点）", min_value=1, max_value=200, value=4, step=1)
    )

duration_columns = st.columns(2)
duration_columns[0].metric("输入实际时长", format_duration(input_length * config.interval_minutes))
duration_columns[1].metric("输出实际时长", format_duration(output_length * config.interval_minutes))

default_train_end, default_validation_end = default_split_bounds(traffic.index, dataset_key)
train_end, validation_end = st.slider(
    "拖动两个节点：训练截止时间 / 验证截止时间",
    min_value=traffic.index[min(input_length + output_length, len(traffic.index) - 3)].to_pydatetime(),
    max_value=traffic.index[-2].to_pydatetime(),
    value=(default_train_end.to_pydatetime(), default_validation_end.to_pydatetime()),
    step=timedelta(minutes=config.interval_minutes),
    format="YYYY-MM-DD HH:mm",
    key=f"split_{dataset_key}",
)

spec = ForecastSpec(
    dataset_key=dataset_key,
    region=str(region),
    interval_minutes=config.interval_minutes,
    input_length=input_length,
    output_length=output_length,
    train_end=train_end,
    validation_end=validation_end,
)

try:
    windowed = build_windowed_data(traffic[region], spec)
except ValueError as error:
    st.error(str(error))
    st.stop()

st.subheader("划分与样本数量")
summary = split_summary(traffic[region], windowed, config.interval_minutes)
st.dataframe(summary, width="stretch", hide_index=True)
st.caption(
    "验证集和测试集的输入窗口可以使用其起点之前的已知历史值，但预测目标严格落在各自数据段内；任何测试目标都不会进入训练。"
)

preview_split_name = st.radio("预览样本", ["训练集", "验证集", "测试集"], horizontal=True)
preview_split = {
    "训练集": windowed.train,
    "验证集": windowed.validation,
    "测试集": windowed.test,
}[preview_split_name]
preview = first_sample_preview(traffic[region], preview_split, windowed.scaler)
st.dataframe(preview, width="stretch", height=320, hide_index=True)

if st.button("保存此预测配置", type="primary", width="stretch"):
    st.session_state["forecast_config"] = spec_to_dict(spec)
    st.success("配置已保存。请从左侧进入“预测算法”运行基线或线性回归。")


