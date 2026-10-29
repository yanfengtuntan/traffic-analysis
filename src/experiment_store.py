from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from src.config import ARTIFACT_DIR
from src.forecasting import ForecastSpec, ModelResult, WindowedData, inverse_targets


EXPERIMENT_DIR = ARTIFACT_DIR / "experiments"
INDEX_PATH = EXPERIMENT_DIR / "index.jsonl"


def comparison_signature(record: dict[str, object]) -> tuple[object, ...]:
    return (
        record.get("dataset_key"),
        record.get("region"),
        record.get("test_start"),
        record.get("test_end"),
        record.get("input_length"),
        record.get("output_length"),
        record.get("prediction_mode"),
    )


def predictions_frame(data: WindowedData, result: ModelResult) -> pd.DataFrame:
    actual = inverse_targets(data.test.y, data.scaler)
    rows: list[dict[str, object]] = []
    for sample_index in range(data.test.samples):
        for horizon_index in range(data.test.y.shape[1]):
            rows.append(
                {
                    "sample": sample_index + 1,
                    "forecast_origin": pd.Timestamp(data.test.input_end_times[sample_index]),
                    "horizon": horizon_index + 1,
                    "target_timestamp": pd.Timestamp(data.test.target_times[sample_index, horizon_index]),
                    "actual": float(actual[sample_index, horizon_index]),
                    "predicted": float(result.test_predictions[sample_index, horizon_index]),
                    "error": float(result.test_predictions[sample_index, horizon_index] - actual[sample_index, horizon_index]),
                }
            )
    return pd.DataFrame(rows)


def save_experiment(
    spec: ForecastSpec,
    full_index: pd.DatetimeIndex,
    data: WindowedData,
    result: ModelResult,
) -> dict[str, object]:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    experiment_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    prediction_path = EXPERIMENT_DIR / f"{experiment_id}_predictions.csv"
    predictions = predictions_frame(data, result)
    predictions.to_csv(prediction_path, index=False, encoding="utf-8-sig")
    history_filename: str | None = None
    if result.training_history is not None:
        history_filename = f"{experiment_id}_training_history.csv"
        result.training_history.to_csv(
            EXPERIMENT_DIR / history_filename,
            index=False,
            encoding="utf-8-sig",
        )

    train_end_position, validation_end_position = data.split_positions
    record: dict[str, object] = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "dataset_key": spec.dataset_key,
        "region": spec.region,
        "train_start": full_index[0].isoformat(),
        "train_end": full_index[train_end_position].isoformat(),
        "validation_start": full_index[train_end_position + 1].isoformat(),
        "validation_end": full_index[validation_end_position].isoformat(),
        "test_start": full_index[validation_end_position + 1].isoformat(),
        "test_end": full_index[-1].isoformat(),
        "input_length": spec.input_length,
        "output_length": spec.output_length,
        "interval_minutes": spec.interval_minutes,
        "prediction_mode": result.prediction_mode,
        "algorithm": result.model_name,
        "parameters": result.parameters,
        "train_samples": data.train.samples,
        "validation_samples": data.validation.samples,
        "test_samples": data.test.samples,
        "fit_seconds": result.fit_seconds,
        "predict_seconds": result.predict_seconds,
        "validation_mae": result.validation_metrics["mae"],
        "validation_rmse": result.validation_metrics["rmse"],
        "test_mae": result.test_metrics["mae"],
        "test_rmse": result.test_metrics["rmse"],
        "predictions_file": prediction_path.name,
        "training_history_file": history_filename,
    }
    with INDEX_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_experiments() -> list[dict[str, object]]:
    if not INDEX_PATH.exists():
        return []
    records: list[dict[str, object]] = []
    with INDEX_PATH.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"实验索引第 {line_number} 行损坏：{error}") from error
    return records


def load_predictions(record: dict[str, object]) -> pd.DataFrame:
    filename = Path(str(record["predictions_file"])).name
    path = EXPERIMENT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"找不到预测明细：{filename}")
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame["forecast_origin"] = pd.to_datetime(frame["forecast_origin"])
    frame["target_timestamp"] = pd.to_datetime(frame["target_timestamp"])
    return frame

