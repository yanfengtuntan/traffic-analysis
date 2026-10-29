"""Scan the raw traffic files using only the Python standard library.

This script is intentionally dependency-free so that it can be used before the
project environment is installed.  It prints a JSON report to stdout and never
modifies the source data.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data_raw" / "data"

DATASETS = {
    "Milano": {
        "csv": "milano_traffic_nid.csv",
        "geojson": "milano.geojson",
        "geo_key": "NIL",
    },
    "Trentino": {
        "csv": "trentino_traffic_nid.csv",
        "geojson": "trento.geojson",
        "geo_key": "NAME_3",
    },
    "ZTE": {
        "csv": "zte_4g_down.region.csv",
        "geojson": "zte_4g_down.traffic.geojson",
        "geo_key": "unique_id",
    },
}


def scan_csv(path: Path) -> dict:
    timestamp_format = "%Y-%m-%d %H:%M:%S"
    rows = 0
    bad_width_rows = 0
    bad_timestamps = 0
    timestamps: list[datetime] = []
    missing_values = 0
    nonnumeric_values = 0
    nonfinite_values = 0
    zero_values = 0
    negative_values = 0
    numeric_values = 0
    value_sum = 0.0
    minimum = math.inf
    maximum = -math.inf

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        regions = header[1:]
        for row in reader:
            rows += 1
            if len(row) != len(header):
                bad_width_rows += 1
            try:
                timestamps.append(datetime.strptime(row[0], timestamp_format))
            except (IndexError, ValueError):
                bad_timestamps += 1

            for raw in row[1:]:
                if raw.strip() == "":
                    missing_values += 1
                    continue
                try:
                    value = float(raw)
                except ValueError:
                    nonnumeric_values += 1
                    continue
                if not math.isfinite(value):
                    nonfinite_values += 1
                    continue
                numeric_values += 1
                value_sum += value
                minimum = min(minimum, value)
                maximum = max(maximum, value)
                if value == 0:
                    zero_values += 1
                elif value < 0:
                    negative_values += 1

    timestamp_counts = Counter(timestamps)
    duplicate_timestamps = sum(count - 1 for count in timestamp_counts.values())
    deltas = Counter(
        int((later - earlier).total_seconds())
        for earlier, later in zip(timestamps, timestamps[1:])
    )
    positive_deltas = [seconds for seconds in deltas if seconds > 0]
    expected_interval = min(positive_deltas) if positive_deltas else None
    missing_time_steps = 0
    if expected_interval:
        for seconds, count in deltas.items():
            if seconds > expected_interval and seconds % expected_interval == 0:
                missing_time_steps += (seconds // expected_interval - 1) * count

    return {
        "file": path.name,
        "encoding": "UTF-8 (utf-8-sig decoder)",
        "timestamp_column": header[0],
        "region_count": len(regions),
        "region_names_unique": len(set(regions)) == len(regions),
        "duplicate_region_names": sorted(
            name for name, count in Counter(regions).items() if count > 1
        ),
        "row_count": rows,
        "expected_cells": rows * len(regions),
        "bad_width_rows": bad_width_rows,
        "bad_timestamps": bad_timestamps,
        "start": min(timestamps).isoformat(sep=" ") if timestamps else None,
        "end": max(timestamps).isoformat(sep=" ") if timestamps else None,
        "chronological": timestamps == sorted(timestamps),
        "duplicate_timestamps": duplicate_timestamps,
        "interval_seconds_counts": dict(sorted(deltas.items())),
        "expected_interval_seconds": expected_interval,
        "missing_time_steps": missing_time_steps,
        "missing_values": missing_values,
        "nonnumeric_values": nonnumeric_values,
        "nonfinite_values": nonfinite_values,
        "zero_values": zero_values,
        "negative_values": negative_values,
        "numeric_values": numeric_values,
        "minimum": None if numeric_values == 0 else minimum,
        "maximum": None if numeric_values == 0 else maximum,
        "mean": None if numeric_values == 0 else value_sum / numeric_values,
        "regions": regions,
    }


def walk_coordinates(value, xs: list[float], ys: list[float]) -> None:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        xs.append(float(value[0]))
        ys.append(float(value[1]))
        return
    if isinstance(value, list):
        for item in value:
            walk_coordinates(item, xs, ys)


def scan_geojson(path: Path, key: str) -> dict:
    with path.open("r", encoding="utf-8-sig") as handle:
        document = json.load(handle)

    features = document.get("features", [])
    geometry_types = Counter()
    property_keys: set[str] = set()
    ids: list[str] = []
    missing_geometry = 0
    missing_key = 0
    xs: list[float] = []
    ys: list[float] = []

    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            missing_geometry += 1
        else:
            geometry_types[geometry.get("type")] += 1
            walk_coordinates(geometry.get("coordinates"), xs, ys)
        properties = feature.get("properties") or {}
        property_keys.update(properties)
        if properties.get(key) is None:
            missing_key += 1
        else:
            ids.append(str(properties[key]))

    id_counts = Counter(ids)
    return {
        "file": path.name,
        "document_type": document.get("type"),
        "feature_count": len(features),
        "crs": document.get("crs"),
        "geometry_types": dict(sorted(geometry_types.items())),
        "missing_geometry": missing_geometry,
        "property_keys": sorted(property_keys),
        "match_key": key,
        "missing_match_key": missing_key,
        "duplicate_match_keys": sorted(
            item for item, count in id_counts.items() if count > 1
        ),
        "bbox": [min(xs), min(ys), max(xs), max(ys)] if xs and ys else None,
        "ids": ids,
    }


def main() -> None:
    report = {"project_root": str(PROJECT_ROOT), "datasets": {}}
    for dataset_name, paths in DATASETS.items():
        csv_report = scan_csv(DATA_DIR / paths["csv"])
        geo_report = scan_geojson(DATA_DIR / paths["geojson"], paths["geo_key"])
        csv_regions = set(csv_report.pop("regions"))
        geo_regions = set(geo_report.pop("ids"))
        report["datasets"][dataset_name] = {
            "csv": csv_report,
            "geojson": geo_report,
            "mapping": {
                "exact_match_count": len(csv_regions & geo_regions),
                "csv_only_count": len(csv_regions - geo_regions),
                "csv_only": sorted(csv_regions - geo_regions),
                "geojson_only_count": len(geo_regions - csv_regions),
                "geojson_only": sorted(geo_regions - csv_regions),
            },
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
