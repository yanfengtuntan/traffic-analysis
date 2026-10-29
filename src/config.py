from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data_raw" / "data"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
PROJECT_NAME = "区域电信流量分析与预测平台"
PROJECT_AUTHOR = "李睿惜"
COURSE_NAME = "人工智能课程 Final Project"


@dataclass(frozen=True)
class DatasetConfig:
    key: str
    label: str
    csv_file: str
    geojson_file: str
    geo_key: str
    interval_minutes: int
    center_lat: float
    center_lon: float
    zoom: float
    default_region: str

    @property
    def csv_path(self) -> Path:
        return DATA_DIR / self.csv_file

    @property
    def geojson_path(self) -> Path:
        return DATA_DIR / self.geojson_file


DATASETS: dict[str, DatasetConfig] = {
    "ZTE": DatasetConfig(
        key="ZTE",
        label="ZTE（济南）",
        csv_file="zte_4g_down.region.csv",
        geojson_file="zte_4g_down.traffic.geojson",
        geo_key="unique_id",
        interval_minutes=15,
        center_lat=36.7645,
        center_lon=117.0929,
        zoom=7.4,
        default_region="370102001",
    ),
    "Milano": DatasetConfig(
        key="Milano",
        label="Milano（米兰）",
        csv_file="milano_traffic_nid.csv",
        geojson_file="milano.geojson",
        geo_key="NIL",
        interval_minutes=10,
        center_lat=45.4613,
        center_lon=9.1593,
        zoom=10.0,
        default_region="DUOMO",
    ),
    "Trentino": DatasetConfig(
        key="Trentino",
        label="Trentino（特伦蒂诺）",
        csv_file="trentino_traffic_nid.csv",
        geojson_file="trento.geojson",
        geo_key="NAME_3",
        interval_minutes=10,
        center_lat=46.1038,
        center_lon=11.2084,
        zoom=7.5,
        default_region="Trento",
    ),
}


AGGREGATIONS = {
    "平均值": "mean",
    "总和": "sum",
    "最大值": "max",
}

