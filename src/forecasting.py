from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from time import perf_counter
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor


@dataclass(frozen=True)
class ForecastSpec:
    dataset_key: str
    region: str
    interval_minutes: int
    input_length: int
    output_length: int
    train_end: pd.Timestamp
    validation_end: pd.Timestamp

    @property
    def input_duration(self) -> timedelta:
        return timedelta(minutes=self.input_length * self.interval_minutes)

    @property
    def output_duration(self) -> timedelta:
        return timedelta(minutes=self.output_length * self.interval_minutes)


@dataclass
class WindowSplit:
    X: np.ndarray
    y: np.ndarray
    target_times: np.ndarray
    input_end_times: np.ndarray

    @property
    def samples(self) -> int:
        return int(self.X.shape[0])


@dataclass
class WindowedData:
    train: WindowSplit
    validation: WindowSplit
    test: WindowSplit
    scaler: StandardScaler
    split_positions: tuple[int, int]
    scaled_series: np.ndarray
    timestamps: np.ndarray


@dataclass
class ModelResult:
    model_name: str
    parameters: dict[str, object]
    validation_predictions: np.ndarray
    test_predictions: np.ndarray
    validation_metrics: dict[str, float]
    test_metrics: dict[str, float]
    fit_seconds: float
    predict_seconds: float
    prediction_mode: str
    training_history: pd.DataFrame | None = None


def default_split_bounds(index: pd.DatetimeIndex, dataset_key: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    if len(index) < 10:
        raise ValueError("时间点太少，无法划分训练、验证和测试集。")
    if dataset_key == "ZTE" and len(index) >= 29 * 96:
        train_end_position = 20 * 96 - 1
        validation_end_position = (20 + 4) * 96 - 1
    else:
        train_end_position = max(int(len(index) * 0.70) - 1, 0)
        validation_end_position = max(int(len(index) * 0.85) - 1, train_end_position + 1)
    validation_end_position = min(validation_end_position, len(index) - 2)
    return index[train_end_position], index[validation_end_position]


def spec_to_dict(spec: ForecastSpec) -> dict[str, object]:
    return {
        "dataset_key": spec.dataset_key,
        "region": spec.region,
        "interval_minutes": spec.interval_minutes,
        "input_length": spec.input_length,
        "output_length": spec.output_length,
        "train_end": spec.train_end.isoformat(),
        "validation_end": spec.validation_end.isoformat(),
    }


def spec_from_dict(value: dict[str, object]) -> ForecastSpec:
    return ForecastSpec(
        dataset_key=str(value["dataset_key"]),
        region=str(value["region"]),
        interval_minutes=int(value["interval_minutes"]),
        input_length=int(value["input_length"]),
        output_length=int(value["output_length"]),
        train_end=pd.Timestamp(value["train_end"]),
        validation_end=pd.Timestamp(value["validation_end"]),
    )


def _window_split(
    scaled_values: np.ndarray,
    timestamps: np.ndarray,
    input_length: int,
    output_length: int,
    target_start: int,
    target_end: int,
) -> WindowSplit:
    first_target = max(target_start, input_length)
    last_target = target_end - output_length + 1
    X: list[np.ndarray] = []
    y: list[np.ndarray] = []
    target_times: list[np.ndarray] = []
    input_end_times: list[np.datetime64] = []
    for target_position in range(first_target, last_target + 1):
        X.append(scaled_values[target_position - input_length : target_position])
        y.append(scaled_values[target_position : target_position + output_length])
        target_times.append(timestamps[target_position : target_position + output_length])
        input_end_times.append(timestamps[target_position - 1])

    if not X:
        return WindowSplit(
            X=np.empty((0, input_length), dtype=float),
            y=np.empty((0, output_length), dtype=float),
            target_times=np.empty((0, output_length), dtype="datetime64[ns]"),
            input_end_times=np.empty((0,), dtype="datetime64[ns]"),
        )
    return WindowSplit(
        X=np.asarray(X, dtype=float),
        y=np.asarray(y, dtype=float),
        target_times=np.asarray(target_times),
        input_end_times=np.asarray(input_end_times),
    )


def build_windowed_data(series: pd.Series, spec: ForecastSpec) -> WindowedData:
    if spec.input_length < 1 or spec.output_length < 1:
        raise ValueError("输入长度和输出长度必须至少为 1。")
    if series.empty:
        raise ValueError("区域序列为空。")
    if not series.index.is_monotonic_increasing or series.index.has_duplicates:
        raise ValueError("时间索引必须严格递增且不能重复。")
    if series.isna().any():
        raise ValueError("当前区域含缺失值，需先处理后才能构建窗口。")

    index = pd.DatetimeIndex(series.index)
    train_end_position = int(index.searchsorted(spec.train_end, side="right") - 1)
    validation_end_position = int(index.searchsorted(spec.validation_end, side="right") - 1)
    if train_end_position < 0 or validation_end_position <= train_end_position:
        raise ValueError("训练截止时间必须早于验证截止时间。")
    if validation_end_position >= len(index) - 1:
        raise ValueError("验证截止时间之后必须保留测试数据。")

    raw_values = series.to_numpy(dtype=float)
    scaler = StandardScaler()
    scaler.fit(raw_values[: train_end_position + 1].reshape(-1, 1))
    scaled_values = scaler.transform(raw_values.reshape(-1, 1)).ravel()
    timestamps = index.to_numpy()

    train = _window_split(
        scaled_values,
        timestamps,
        spec.input_length,
        spec.output_length,
        target_start=spec.input_length,
        target_end=train_end_position,
    )
    validation = _window_split(
        scaled_values,
        timestamps,
        spec.input_length,
        spec.output_length,
        target_start=train_end_position + 1,
        target_end=validation_end_position,
    )
    test = _window_split(
        scaled_values,
        timestamps,
        spec.input_length,
        spec.output_length,
        target_start=validation_end_position + 1,
        target_end=len(index) - 1,
    )
    if train.samples == 0 or validation.samples == 0 or test.samples == 0:
        raise ValueError(
            "当前划分无法为训练、验证和测试集都生成样本，请缩短窗口或调整截止时间。"
        )
    return WindowedData(
        train=train,
        validation=validation,
        test=test,
        scaler=scaler,
        split_positions=(train_end_position, validation_end_position),
        scaled_series=scaled_values,
        timestamps=timestamps,
    )


def inverse_targets(values: np.ndarray, scaler: StandardScaler) -> np.ndarray:
    shape = values.shape
    return scaler.inverse_transform(values.reshape(-1, 1)).reshape(shape)


def regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    actual_flat = np.asarray(actual, dtype=float).ravel()
    predicted_flat = np.asarray(predicted, dtype=float).ravel()
    return {
        "mae": float(mean_absolute_error(actual_flat, predicted_flat)),
        "rmse": float(np.sqrt(mean_squared_error(actual_flat, predicted_flat))),
    }


def _run_arima(
    data: WindowedData,
    parameters: dict[str, object],
) -> tuple[np.ndarray, np.ndarray, float, float]:
    from statsmodels.tsa.arima.model import ARIMA

    order = (
        int(parameters.get("p", 2)),
        int(parameters.get("d", 0)),
        int(parameters.get("q", 1)),
    )
    train_end, validation_end = data.split_positions
    fit_start = perf_counter()
    fitted = ARIMA(
        data.scaled_series[: train_end + 1],
        order=order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit()
    fit_seconds = perf_counter() - fit_start

    prediction_start = perf_counter()

    def rolling_segment(state, start: int, end: int, expected_samples: int):
        forecasts: list[np.ndarray] = []
        last_origin = end - data.test.y.shape[1] + 1
        for position in range(start, end + 1):
            if position <= last_origin:
                forecasts.append(np.asarray(state.forecast(steps=data.test.y.shape[1]), dtype=float))
            state = state.extend([data.scaled_series[position]])
        values = np.asarray(forecasts, dtype=float)
        if len(values) != expected_samples:
            raise RuntimeError("ARIMA 滚动预测样本数与窗口定义不一致。")
        return state, values

    fitted, validation_scaled = rolling_segment(
        fitted,
        train_end + 1,
        validation_end,
        data.validation.samples,
    )
    _, test_scaled = rolling_segment(
        fitted,
        validation_end + 1,
        len(data.scaled_series) - 1,
        data.test.samples,
    )
    predict_seconds = perf_counter() - prediction_start
    return validation_scaled, test_scaled, fit_seconds, predict_seconds


def run_model(
    data: WindowedData,
    model_name: str,
    parameters: dict[str, object] | None = None,
    epoch_callback: Callable[[int, int, float, float], None] | None = None,
) -> ModelResult:
    parameters = dict(parameters or {})
    training_history: pd.DataFrame | None = None
    prediction_mode = "direct_multi_output_sliding_window"
    fit_start = perf_counter()
    if model_name == "持久性基线":
        validation_scaled = np.repeat(data.validation.X[:, -1:], data.validation.y.shape[1], axis=1)
        test_scaled = np.repeat(data.test.X[:, -1:], data.test.y.shape[1], axis=1)
        fit_seconds = perf_counter() - fit_start
        predict_seconds = 0.0
    elif model_name == "ARIMA":
        validation_scaled, test_scaled, fit_seconds, predict_seconds = _run_arima(data, parameters)
        prediction_mode = "rolling_origin_arima_state_update"
    elif model_name in {"MLP", "1D CNN", "LSTM", "GRU"}:
        from src.neural_models import train_neural_model

        output = train_neural_model(
            model_name=model_name,
            train_X=data.train.X,
            train_y=data.train.y,
            validation_X=data.validation.X,
            validation_y=data.validation.y,
            test_X=data.test.X,
            parameters=parameters,
            epoch_callback=epoch_callback,
        )
        validation_scaled = output.validation_predictions
        test_scaled = output.test_predictions
        fit_seconds = output.fit_seconds
        predict_seconds = output.predict_seconds
        training_history = output.history
    else:
        model = None
        if model_name == "线性回归":
            model = LinearRegression(
                fit_intercept=bool(parameters.get("fit_intercept", True)),
                positive=bool(parameters.get("positive", False)),
            )
        elif model_name == "KNN 回归":
            model = KNeighborsRegressor(
                n_neighbors=int(parameters.get("n_neighbors", 5)),
                weights=str(parameters.get("weights", "distance")),
                p=int(parameters.get("p", 2)),
            )
        elif model_name == "SVR":
            model = MultiOutputRegressor(
                SVR(
                    C=float(parameters.get("C", 10.0)),
                    epsilon=float(parameters.get("epsilon", 0.1)),
                    kernel=str(parameters.get("kernel", "rbf")),
                    gamma=str(parameters.get("gamma", "scale")),
                ),
                n_jobs=-1,
            )
        elif model_name == "决策树":
            depth = int(parameters.get("max_depth", 0))
            model = DecisionTreeRegressor(
                max_depth=None if depth == 0 else depth,
                min_samples_leaf=int(parameters.get("min_samples_leaf", 2)),
                random_state=42,
            )
        elif model_name == "随机森林":
            depth = int(parameters.get("max_depth", 0))
            model = RandomForestRegressor(
                n_estimators=int(parameters.get("n_estimators", 100)),
                max_depth=None if depth == 0 else depth,
                min_samples_leaf=int(parameters.get("min_samples_leaf", 1)),
                n_jobs=-1,
                random_state=42,
            )
        elif model_name == "Extra Trees":
            depth = int(parameters.get("max_depth", 0))
            model = ExtraTreesRegressor(
                n_estimators=int(parameters.get("n_estimators", 100)),
                max_depth=None if depth == 0 else depth,
                min_samples_leaf=int(parameters.get("min_samples_leaf", 1)),
                n_jobs=-1,
                random_state=42,
            )
        elif model_name == "梯度提升":
            model = MultiOutputRegressor(
                GradientBoostingRegressor(
                    n_estimators=int(parameters.get("n_estimators", 100)),
                    learning_rate=float(parameters.get("learning_rate", 0.05)),
                    max_depth=int(parameters.get("max_depth", 3)),
                    min_samples_leaf=int(parameters.get("min_samples_leaf", 2)),
                    random_state=42,
                ),
                n_jobs=-1,
            )
        else:
            raise ValueError(f"当前阶段尚未接入算法：{model_name}")

        if model is None:
            raise RuntimeError("模型创建失败。")
        model.fit(data.train.X, data.train.y)
        fit_seconds = perf_counter() - fit_start
        predict_start = perf_counter()
        validation_scaled = model.predict(data.validation.X)
        test_scaled = model.predict(data.test.X)
        predict_seconds = perf_counter() - predict_start

    validation_actual = inverse_targets(data.validation.y, data.scaler)
    test_actual = inverse_targets(data.test.y, data.scaler)
    validation_predictions = inverse_targets(validation_scaled, data.scaler)
    test_predictions = inverse_targets(test_scaled, data.scaler)
    return ModelResult(
        model_name=model_name,
        parameters=parameters,
        validation_predictions=validation_predictions,
        test_predictions=test_predictions,
        validation_metrics=regression_metrics(validation_actual, validation_predictions),
        test_metrics=regression_metrics(test_actual, test_predictions),
        fit_seconds=fit_seconds,
        predict_seconds=predict_seconds,
        prediction_mode=prediction_mode,
        training_history=training_history,
    )


def split_summary(
    series: pd.Series,
    data: WindowedData,
    interval_minutes: int,
) -> pd.DataFrame:
    train_end, validation_end = data.split_positions
    segments = [
        ("训练集", 0, train_end, data.train.samples),
        ("验证集", train_end + 1, validation_end, data.validation.samples),
        ("测试集", validation_end + 1, len(series) - 1, data.test.samples),
    ]
    rows = []
    for label, start, end, samples in segments:
        points = end - start + 1
        rows.append(
            {
                "数据段": label,
                "开始时间": series.index[start],
                "结束时间": series.index[end],
                "时间点数": points,
                "实际时长": str(timedelta(minutes=points * interval_minutes)),
                "可用样本数": samples,
            }
        )
    return pd.DataFrame(rows)


def first_sample_preview(
    series: pd.Series,
    split: WindowSplit,
    scaler: StandardScaler,
) -> pd.DataFrame:
    input_values = inverse_targets(split.X[:1], scaler).ravel()
    output_values = inverse_targets(split.y[:1], scaler).ravel()
    input_end = pd.Timestamp(split.input_end_times[0])
    input_times = series.index[series.index.get_loc(input_end) - len(input_values) + 1 : series.index.get_loc(input_end) + 1]
    rows = [
        {"部分": "输入", "时间": timestamp, "流量值": value}
        for timestamp, value in zip(input_times, input_values)
    ]
    rows.extend(
        {"部分": "目标", "时间": pd.Timestamp(timestamp), "流量值": value}
        for timestamp, value in zip(split.target_times[0], output_values)
    )
    return pd.DataFrame(rows)

