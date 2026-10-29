from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src.config import DATASETS, DatasetConfig


@st.cache_data(show_spinner=False)
def load_traffic(dataset_key: str) -> pd.DataFrame:
    """Load one dataset as a timestamp-indexed wide table."""
    config = DATASETS[dataset_key]
    frame = pd.read_csv(config.csv_path, encoding="utf-8-sig")
    timestamp_column = frame.columns[0]
    frame = frame.rename(columns={timestamp_column: "timestamp"})
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="raise")
    frame.columns = [str(column) for column in frame.columns]
    frame = frame.set_index("timestamp").sort_index()
    if frame.index.has_duplicates:
        raise ValueError(f"{config.label} 存在重复时间戳。")
    return frame


@st.cache_data(show_spinner=False)
def load_geojson(dataset_key: str) -> dict:
    config = DATASETS[dataset_key]
    with config.geojson_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def build_region_labels(config: DatasetConfig, geojson: dict) -> dict[str, str]:
    """Return stable region-id to human-friendly label mappings."""
    labels: dict[str, str] = {}
    for feature in geojson.get("features", []):
        properties = feature.get("properties") or {}
        region_id = properties.get(config.geo_key)
        if region_id is None:
            continue
        region_id = str(region_id)
        display_name = str(properties.get("name") or region_id)
        if display_name == region_id:
            labels[region_id] = region_id
        else:
            labels[region_id] = f"{display_name}（{region_id}）"
    return labels


def dataset_metrics(frame: pd.DataFrame, config: DatasetConfig) -> dict[str, object]:
    return {
        "regions": frame.shape[1],
        "time_points": frame.shape[0],
        "start": frame.index.min(),
        "end": frame.index.max(),
        "interval_minutes": config.interval_minutes,
    }

