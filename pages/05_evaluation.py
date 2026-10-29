from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.experiment_store import comparison_signature, load_experiments, load_predictions


st.title("📊 评估与对比")
st.caption("只比较数据集、区域、测试区间、输入/输出长度和预测方式完全一致的实验。")

try:
    experiments = load_experiments()
except ValueError as error:
    st.error(str(error))
    st.stop()

if not experiments:
    st.info("还没有保存的实验。请先进入“预测算法”运行持久性基线或线性回归。")
    st.stop()

selected_id = st.selectbox(
    "选择参考实验",
    options=[str(record["experiment_id"]) for record in reversed(experiments)],
    format_func=lambda experiment_id: next(
        f"{record['created_at']} · {record['algorithm']} · {record['dataset_key']} / {record['region']}"
        for record in experiments
        if record["experiment_id"] == experiment_id
    ),
)
selected = next(record for record in experiments if record["experiment_id"] == selected_id)
signature = comparison_signature(selected)
comparable = [record for record in experiments if comparison_signature(record) == signature]

metric_columns = st.columns(3)
metric_columns[0].metric("已保存实验", f"{len(experiments):,}")
metric_columns[1].metric("当前可公平比较", f"{len(comparable):,}")
metric_columns[2].metric("测试样本", f"{int(selected['test_samples']):,}")

comparison = pd.DataFrame(
    [
        {
            "实验编号": record["experiment_id"],
            "算法": record["algorithm"],
            "测试 MAE": record["test_mae"],
            "测试 RMSE": record["test_rmse"],
            "拟合秒数": record["fit_seconds"],
            "预测秒数": record["predict_seconds"],
            "创建时间": record["created_at"],
        }
        for record in comparable
    ]
).sort_values("测试 RMSE")
comparison_view = comparison.style.format(
    {
        "测试 MAE": "{:,.0f}",
        "测试 RMSE": "{:,.0f}",
        "拟合秒数": "{:.4f}",
        "预测秒数": "{:.4f}",
    }
)
st.dataframe(comparison_view, width="stretch", hide_index=True)

metric_chart = go.Figure()
metric_chart.add_trace(go.Bar(x=comparison["算法"], y=comparison["测试 MAE"], name="MAE"))
metric_chart.add_trace(go.Bar(x=comparison["算法"], y=comparison["测试 RMSE"], name="RMSE"))
metric_chart.update_layout(
    title="公平条件下的模型指标",
    barmode="group",
    xaxis_title="算法",
    yaxis_title="原始尺度误差",
    height=390,
    margin={"l": 20, "r": 20, "t": 55, "b": 20},
)
st.plotly_chart(metric_chart, width="stretch", config={"displaylogo": False})

try:
    predictions = load_predictions(selected)
except FileNotFoundError as error:
    st.error(str(error))
    st.stop()

horizon = st.selectbox("预测步", sorted(predictions["horizon"].unique()))
horizon_data = predictions[predictions["horizon"] == horizon]
curve = go.Figure()
curve.add_trace(
    go.Scatter(
        x=horizon_data["target_timestamp"],
        y=horizon_data["actual"],
        name="真实值",
        mode="lines",
        line={"color": "#0F766E", "width": 2},
    )
)
curve.add_trace(
    go.Scatter(
        x=horizon_data["target_timestamp"],
        y=horizon_data["predicted"],
        name="预测值",
        mode="lines",
        line={"color": "#D97706", "width": 1.7},
    )
)
curve.update_layout(
    title=f"实验 {selected_id} · 第 {horizon} 预测步",
    xaxis_title="目标时间",
    yaxis_title="流量值",
    hovermode="x unified",
    height=420,
    margin={"l": 20, "r": 20, "t": 55, "b": 20},
)
st.plotly_chart(curve, width="stretch", config={"displaylogo": False})

error_chart = go.Figure(
    go.Bar(
        x=horizon_data["target_timestamp"],
        y=horizon_data["error"],
        marker_color="#C2410C",
        name="预测误差",
    )
)
error_chart.update_layout(
    title="预测误差（预测值 − 真实值）",
    xaxis_title="目标时间",
    yaxis_title="误差",
    height=330,
    margin={"l": 20, "r": 20, "t": 55, "b": 20},
)
st.plotly_chart(error_chart, width="stretch", config={"displaylogo": False})

download_columns = st.columns(2)
download_columns[0].download_button(
    "导出公平比较表",
    data=comparison.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"comparison_{selected_id}.csv",
    mime="text/csv",
    width="stretch",
)
download_columns[1].download_button(
    "导出该实验预测明细",
    data=predictions.to_csv(index=False).encode("utf-8-sig"),
    file_name=str(selected["predictions_file"]),
    mime="text/csv",
    width="stretch",
)

st.caption("所有指标均在逆缩放后的原始尺度计算。ZTE 含零值，因此当前不展示普通 MAPE。")
