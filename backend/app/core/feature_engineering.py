# 特征工程：滑动窗口、差分特征、统计特征

import pandas as pd
import numpy as np

METRIC_COLUMNS = [
    "head_angle",
    "shoulder_diff",
    "hunchback_score",
    "body_tilt",
    "round_shoulder",
]


def sliding_window_features(df: pd.DataFrame, windows: list = None) -> pd.DataFrame:
    """
    为每个指标列添加滑动窗口统计特征

    Args:
        df: 清洗后的 DataFrame（需含 created_at 和 5 项指标）
        windows: 窗口大小列表，默认 [3, 5, 10]

    Returns:
        添加了窗口特征的 DataFrame
    """
    if windows is None:
        windows = [3, 5, 10]

    df = df.copy()

    for col in METRIC_COLUMNS:
        if col not in df.columns:
            continue

        for w in windows:
            # 滑动均值
            df[f"{col}_mean_{w}"] = df[col].rolling(window=w, min_periods=1).mean()
            # 滑动标准差
            df[f"{col}_std_{w}"] = df[col].rolling(window=w, min_periods=1).std().fillna(0)
            # 滑动最大/最小值
            df[f"{col}_max_{w}"] = df[col].rolling(window=w, min_periods=1).max()
            df[f"{col}_min_{w}"] = df[col].rolling(window=w, min_periods=1).min()

    return df


def diff_features(df: pd.DataFrame, lags: list = None) -> pd.DataFrame:
    """
    差分特征：一阶差分、多阶滞后

    Args:
        df: DataFrame
        lags: 滞后阶数列表，默认 [1, 3, 5]

    Returns:
        添加了差分特征的 DataFrame
    """
    if lags is None:
        lags = [1, 3, 5]

    df = df.copy()

    for col in METRIC_COLUMNS:
        if col not in df.columns:
            continue

        # 一阶差分
        df[f"{col}_diff_1"] = df[col].diff().fillna(0)

        for lag in lags:
            # 多阶差分
            df[f"{col}_diff_{lag}"] = df[col].diff(periods=lag).fillna(0)
            # 变化率
            df[f"{col}_pct_{lag}"] = df[col].pct_change(periods=lag).fillna(0).clip(-1, 1)

    return df


def statistical_features(df: pd.DataFrame) -> dict:
    """
    计算整体统计特征（用于模型输入）

    Returns:
        dict: 各项均值的字典
    """
    if df.empty:
        return {}

    stats = {}
    for col in METRIC_COLUMNS:
        if col in df.columns and df[col].notna().any():
            stats[f"{col}_mean"] = float(df[col].mean())
            stats[f"{col}_std"] = float(df[col].std())
            stats[f"{col}_max"] = float(df[col].max())
            stats[f"{col}_min"] = float(df[col].min())
            stats[f"{col}_median"] = float(df[col].median())

    # 不良占比
    bad_mask = (df["head_angle"] > 40) | (df["hunchback_score"] > 0.3)
    stats["bad_posture_ratio"] = float(bad_mask.mean())

    # 趋势（最近 10 条 vs 全部平均）
    if len(df) >= 10:
        recent = df.tail(10)
        for col in METRIC_COLUMNS:
            if col in df.columns:
                stats[f"{col}_trend"] = float(recent[col].mean() - df[col].mean())
    else:
        for col in METRIC_COLUMNS:
            stats[f"{col}_trend"] = 0.0

    return stats


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    完整特征工程流水线：滑动窗口 + 差分 + 统计
    """
    df = sliding_window_features(df)
    df = diff_features(df)
    # 统计特征不加入 DataFrame（返回的是 dict，供模型使用）
    return df
