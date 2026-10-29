from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import DATASETS
from src.data_loader import load_traffic
from src.experiment_store import predictions_frame, save_experiment
from src.forecasting import (
    ForecastSpec,
    build_windowed_data,
    default_split_bounds,
    run_model,
    spec_from_dict,
    spec_to_dict,
)


def default_spec() -> ForecastSpec:
    dataset_key = "ZTE"
    config = DATASETS[dataset_key]
    frame = load_traffic(dataset_key)
    train_end, validation_end = default_split_bounds(frame.index, dataset_key)
    return ForecastSpec(
        dataset_key=dataset_key,
        region=config.default_region,
        interval_minutes=config.interval_minutes,
        input_length=96,
        output_length=4,
        train_end=train_end,
        validation_end=validation_end,
    )


st.title("🧠 预测算法")
st.caption("已接入 12 种可训练算法和持久性基线；每次运行都会执行真实拟合、预测与保存。")

saved_config = st.session_state.get("forecast_config")
spec = spec_from_dict(saved_config) if saved_config else default_spec()
config = DATASETS[spec.dataset_key]
traffic = load_traffic(spec.dataset_key)

if not saved_config:
    st.warning("尚未从“预测数据构建”保存配置，当前使用 ZTE 的 24 小时输入、1 小时输出默认配置。")

configuration = pd.DataFrame(
    [
        {
            "数据集": config.label,
            "区域": spec.region,
            "输入长度": spec.input_length,
            "输出长度": spec.output_length,
            "训练截止": spec.train_end,
            "验证截止": spec.validation_end,
            "测试截止": traffic.index[-1],
        }
    ]
)
st.dataframe(configuration, width="stretch", hide_index=True)

algorithm = st.selectbox(
    "算法",
    [
        "线性回归",
        "KNN 回归",
        "SVR",
        "决策树",
        "随机森林",
        "Extra Trees",
        "梯度提升",
        "ARIMA",
        "MLP",
        "1D CNN",
        "LSTM",
        "GRU",
        "持久性基线",
    ],
)
parameters: dict[str, object] = {}
if algorithm == "线性回归":
    parameter_columns = st.columns(2)
    parameters["fit_intercept"] = parameter_columns[0].checkbox("拟合截距", value=True)
    parameters["positive"] = parameter_columns[1].checkbox("限制系数非负", value=False)
elif algorithm == "KNN 回归":
    parameter_columns = st.columns(3)
    parameters["n_neighbors"] = parameter_columns[0].slider("邻居数量", 1, 50, 5)
    parameters["weights"] = parameter_columns[1].selectbox("权重", ["distance", "uniform"])
    parameters["p"] = parameter_columns[2].selectbox("距离阶数 p", [2, 1], format_func=lambda value: "欧氏距离" if value == 2 else "曼哈顿距离")
elif algorithm == "SVR":
    parameter_columns = st.columns(3)
    parameters["C"] = parameter_columns[0].number_input("惩罚系数 C", min_value=0.01, value=10.0, step=1.0)
    parameters["epsilon"] = parameter_columns[1].number_input("epsilon", min_value=0.0, value=0.1, step=0.05)
    parameters["kernel"] = parameter_columns[2].selectbox("核函数", ["rbf", "linear", "poly"])
    parameters["gamma"] = "scale"
elif algorithm == "决策树":
    parameter_columns = st.columns(2)
    parameters["max_depth"] = parameter_columns[0].slider("最大深度（0 为不限）", 0, 50, 12)
    parameters["min_samples_leaf"] = parameter_columns[1].slider("叶节点最小样本数", 1, 30, 2)
elif algorithm in {"随机森林", "Extra Trees"}:
    parameter_columns = st.columns(3)
    parameters["n_estimators"] = parameter_columns[0].slider("树数量", 50, 500, 100, step=50)
    parameters["max_depth"] = parameter_columns[1].slider("最大深度（0 为不限）", 0, 50, 18)
    parameters["min_samples_leaf"] = parameter_columns[2].slider("叶节点最小样本数", 1, 20, 1)
elif algorithm == "梯度提升":
    parameter_columns = st.columns(4)
    parameters["n_estimators"] = parameter_columns[0].slider("迭代树数量", 50, 500, 100, step=50)
    parameters["learning_rate"] = parameter_columns[1].number_input("学习率", min_value=0.001, max_value=1.0, value=0.05, step=0.01, format="%.3f")
    parameters["max_depth"] = parameter_columns[2].slider("单树最大深度", 1, 10, 3)
    parameters["min_samples_leaf"] = parameter_columns[3].slider("叶节点最小样本数", 1, 20, 2)
elif algorithm == "ARIMA":
    parameter_columns = st.columns(3)
    parameters["p"] = parameter_columns[0].slider("AR 阶数 p", 0, 8, 2)
    parameters["d"] = parameter_columns[1].slider("差分阶数 d", 0, 2, 0)
    parameters["q"] = parameter_columns[2].slider("MA 阶数 q", 0, 8, 1)
    st.caption("ARIMA 使用训练段拟合初始状态，并在验证/测试阶段按真实时间顺序更新状态后进行滚动多步预测；评估页不会把它与直接多输出模型混为同一预测方式。")
elif algorithm in {"MLP", "1D CNN", "LSTM", "GRU"}:
    parameter_columns = st.columns(4)
    parameters["epochs"] = parameter_columns[0].slider("最大训练轮数", 5, 200, 30, step=5)
    parameters["batch_size"] = parameter_columns[1].selectbox("批大小", [32, 64, 128, 256], index=1)
    parameters["hidden_size"] = parameter_columns[2].selectbox("隐藏维度", [16, 32, 64, 128, 256], index=2)
    parameters["learning_rate"] = parameter_columns[3].number_input("学习率", min_value=0.0001, max_value=0.1, value=0.001, step=0.0005, format="%.4f")
    detail_columns = st.columns(3)
    parameters["dropout"] = detail_columns[0].slider("Dropout", 0.0, 0.5, 0.1, step=0.05)
    parameters["patience"] = detail_columns[1].slider("早停耐心轮数（0 为关闭）", 0, 30, 5)
    if algorithm == "1D CNN":
        parameters["kernel_size"] = detail_columns[2].selectbox("卷积核大小", [3, 5, 7])
    elif algorithm in {"LSTM", "GRU"}:
        parameters["num_layers"] = detail_columns[2].slider("循环层数", 1, 3, 1)
    else:
        detail_columns[2].caption("MLP 使用两层全连接隐藏层。")
    st.caption("神经网络固定在 CPU 上运行，并逐轮显示训练损失和验证损失；保存验证损失最优的模型状态。")
else:
    st.caption("持久性基线把输入窗口最后一个真实值重复为未来各步预测。它不进行参数训练。")

if st.button("开始真实训练与预测", type="primary", width="stretch"):
    neural_algorithms = {"MLP", "1D CNN", "LSTM", "GRU"}
    loss_rows: list[dict[str, float | int]] = []
    epoch_message = st.empty()
    epoch_progress = st.empty()
    loss_chart = st.empty()

    def report_epoch(epoch: int, total: int, training_loss: float, validation_loss: float) -> None:
        loss_rows.append(
            {"epoch": epoch, "训练损失": training_loss, "验证损失": validation_loss}
        )
        epoch_message.caption(
            f"第 {epoch}/{total} 轮 · 训练损失 {training_loss:.6f} · 验证损失 {validation_loss:.6f}"
        )
        epoch_progress.progress(epoch / total, text=f"神经网络训练：{epoch}/{total}")
        history_frame = pd.DataFrame(loss_rows).set_index("epoch")
        loss_chart.line_chart(history_frame, x_label="训练轮次", y_label="MSE 损失")

    with st.status("实验执行中……", expanded=True) as status:
        st.write("1/5 正在构建滑动窗口，并仅用训练集拟合缩放器。")
        data = build_windowed_data(traffic[spec.region], spec)
        st.write(f"2/5 训练样本 {data.train.samples:,} 个，开始拟合 {algorithm}。")
        result = run_model(
            data,
            algorithm,
            parameters,
            epoch_callback=report_epoch if algorithm in neural_algorithms else None,
        )
        st.write("3/5 正在验证集和测试集上执行预测。")
        st.write("4/5 正在原始尺度上计算 MAE 与 RMSE。")
        record = save_experiment(spec, traffic.index, data, result)
        st.write("5/5 预测明细和实验元数据已保存到项目内 artifacts/experiments。")
        status.update(label="实验完成", state="complete", expanded=False)

    metric_columns = st.columns(4)
    metric_columns[0].metric("验证 MAE", f"{result.validation_metrics['mae']:,.2f}")
    metric_columns[1].metric("验证 RMSE", f"{result.validation_metrics['rmse']:,.2f}")
    metric_columns[2].metric("测试 MAE", f"{result.test_metrics['mae']:,.2f}")
    metric_columns[3].metric("测试 RMSE", f"{result.test_metrics['rmse']:,.2f}")
    st.caption(
        f"拟合耗时 {result.fit_seconds:.3f} 秒；预测耗时 {result.predict_seconds:.3f} 秒；实验编号 {record['experiment_id']}。"
    )
    if result.training_history is not None:
        with st.expander("逐轮训练记录", expanded=False):
            st.dataframe(result.training_history, width="stretch", hide_index=True)

    predictions = predictions_frame(data, result)
    first_horizon = predictions[predictions["horizon"] == 1]
    curve = go.Figure()
    curve.add_trace(
        go.Scatter(
            x=first_horizon["target_timestamp"],
            y=first_horizon["actual"],
            mode="lines",
            name="真实值",
            line={"color": "#0F766E", "width": 2},
        )
    )
    curve.add_trace(
        go.Scatter(
            x=first_horizon["target_timestamp"],
            y=first_horizon["predicted"],
            mode="lines",
            name="预测值",
            line={"color": "#D97706", "width": 1.7},
        )
    )
    curve.update_layout(
        title="测试集：第 1 预测步",
        xaxis_title="目标时间",
        yaxis_title="流量值",
        hovermode="x unified",
        height=420,
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
    )
    st.plotly_chart(curve, width="stretch", config={"displaylogo": False})
    st.success("实验已持久保存。进入“评估与对比”可查看预测明细和公平比较。")

st.divider()
with st.expander("算法覆盖说明"):
    st.write("已接入：线性回归、KNN、SVR、决策树、随机森林、Extra Trees、梯度提升、ARIMA、MLP、1D CNN、LSTM、GRU，以及持久性基线。")


