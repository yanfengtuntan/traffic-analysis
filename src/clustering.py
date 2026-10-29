from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score


@dataclass
class ClusteringResult:
    assignments: pd.Series
    normalized_profiles: pd.DataFrame
    representative_profiles: pd.DataFrame
    embedding: pd.DataFrame
    silhouette: float | None
    elapsed_seconds: float
    profile_labels: list[str]


def temporal_profiles(frame: pd.DataFrame, feature_mode: str) -> tuple[pd.DataFrame, list[str]]:
    """Build region-by-time-slot profiles without mixing datasets."""
    if frame.empty:
        raise ValueError("当前时间范围没有数据。")
    if feature_mode == "日内模式":
        group_key = frame.index.hour * 60 + frame.index.minute
        profile = frame.groupby(group_key).mean().sort_index()
        labels = [f"{minute // 60:02d}:{minute % 60:02d}" for minute in profile.index]
    elif feature_mode == "周内小时模式":
        group_key = frame.index.dayofweek * 24 + frame.index.hour
        profile = frame.groupby(group_key).mean().reindex(range(168))
        if profile.isna().any().any():
            raise ValueError("所选时间范围不足以形成完整的周内小时模式，请扩大时间范围。")
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        labels = [f"{weekday_names[slot // 24]} {slot % 24:02d}:00" for slot in profile.index]
    else:
        raise ValueError(f"不支持的特征模式：{feature_mode}")

    region_profiles = profile.T.astype(float)
    values = region_profiles.to_numpy()
    row_means = values.mean(axis=1, keepdims=True)
    row_stds = values.std(axis=1, keepdims=True)
    row_stds[row_stds == 0] = 1.0
    normalized = (values - row_means) / row_stds
    return pd.DataFrame(normalized, index=region_profiles.index, columns=profile.index), labels


def run_clustering(
    frame: pd.DataFrame,
    feature_mode: str,
    algorithm: str,
    n_clusters: int = 4,
    eps: float = 3.0,
    min_samples: int = 5,
) -> ClusteringResult:
    start = perf_counter()
    normalized, profile_labels = temporal_profiles(frame, feature_mode)
    values = normalized.to_numpy()
    if algorithm == "K-means":
        if n_clusters < 2 or n_clusters >= len(normalized):
            raise ValueError("K 必须至少为 2，并且小于区域数量。")
        estimator = KMeans(n_clusters=n_clusters, n_init=20, random_state=42)
        raw_labels = estimator.fit_predict(values)
    elif algorithm == "DBSCAN":
        if eps <= 0 or min_samples < 2:
            raise ValueError("DBSCAN 的 eps 必须大于 0，最小样本数至少为 2。")
        estimator = DBSCAN(eps=eps, min_samples=min_samples)
        raw_labels = estimator.fit_predict(values)
    else:
        raise ValueError(f"不支持的聚类算法：{algorithm}")

    assignments = pd.Series(raw_labels, index=normalized.index.astype(str), name="cluster")
    normalized_for_grouping = normalized.copy()
    normalized_for_grouping.index = normalized_for_grouping.index.astype(str)
    representative_profiles = normalized_for_grouping.groupby(assignments).mean().sort_index()

    non_noise = raw_labels != -1
    non_noise_labels = raw_labels[non_noise]
    unique_non_noise = np.unique(non_noise_labels)
    silhouette: float | None = None
    if len(unique_non_noise) >= 2 and non_noise.sum() > len(unique_non_noise):
        silhouette = float(silhouette_score(values[non_noise], non_noise_labels))

    embedding_values = PCA(n_components=2).fit_transform(values)
    embedding = pd.DataFrame(
        {
            "区域": normalized.index.astype(str),
            "主成分 1": embedding_values[:, 0],
            "主成分 2": embedding_values[:, 1],
            "聚类": raw_labels,
        }
    )
    return ClusteringResult(
        assignments=assignments,
        normalized_profiles=normalized_for_grouping,
        representative_profiles=representative_profiles,
        embedding=embedding,
        silhouette=silhouette,
        elapsed_seconds=perf_counter() - start,
        profile_labels=profile_labels,
    )


def cluster_display_name(cluster: int) -> str:
    return "噪声点" if int(cluster) == -1 else f"模式簇 {int(cluster) + 1}"

