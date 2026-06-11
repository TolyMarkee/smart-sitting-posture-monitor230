# 数据预处理：清洗、异常检测、聚合

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Optional


# 指标列名（与 PostureRecord ORM 字段对应）
METRIC_COLUMNS = [
    "head_angle",
    "shoulder_diff",
    "hunchback_score",
    "body_tilt",
    "round_shoulder",
]


def records_to_dataframe(records: list) -> pd.DataFrame:
    """
    将 ORM 查询结果转为 Pandas DataFrame

    Args:
        records: PostureRecord ORM 对象列表

    Returns:
        DataFrame，包含 created_at 和 5 项指标列
    """
    if not records:
        return pd.DataFrame(columns=["created_at"] + METRIC_COLUMNS)

    data = []
    for r in records:
        data.append({
            "created_at": r.created_at,
            "head_angle": r.head_angle,
            "shoulder_diff": r.shoulder_diff,
            "hunchback_score": r.hunchback_score,
            "body_tilt": r.body_tilt,
            "round_shoulder": r.round_shoulder,
        })

    df = pd.DataFrame(data)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df = df.sort_values("created_at").reset_index(drop=True)
    return df


# 各指标的物理有效范围（超出直接丢弃）
VALID_RANGES = {
    "head_angle":      (0.0, 80.0),     # 0~80°
    "shoulder_diff":   (0.0, 0.4),      # 比例 0~0.4（>0.4为明显误判）
    "hunchback_score": (0.0, 0.9),      # 比例 0~0.9
    "body_tilt":       (0.0, 40.0),     # 0~40°
    "round_shoulder":  (0.0, 0.8),      # 比例 0~0.8
}


def remove_outliers(df: pd.DataFrame, n_std: float = 3.0) -> pd.DataFrame:
    """
    去除异常值：先硬边界过滤 → 再 Z-score 统计过滤

    Args:
        df: 原始 DataFrame
        n_std: Z-score 阈值，超过此值的视为异常

    Returns:
        清洗后的 DataFrame
    """
    if df.empty:
        return df

    # 第一层：硬边界过滤 — 物理上不可能的值直接丢弃
    mask = pd.Series(True, index=df.index)
    rejected = {k: 0 for k in VALID_RANGES}
    for col, (vmin, vmax) in VALID_RANGES.items():
        if col in df.columns:
            col_mask = (df[col] >= vmin) & (df[col] <= vmax)
            rejected[col] = (~col_mask).sum()
            mask &= col_mask

    total_rejected = sum(rejected.values())
    if total_rejected > 0:
        import logging
        logging.warning(f"[Preprocess] 硬边界过滤: 丢弃 {total_rejected} 条异常记录 {rejected}")

    df = df[mask].copy()

    if df.empty:
        return df

    # 第二层：Z-score 统计过滤
    mask2 = pd.Series(True, index=df.index)
    for col in METRIC_COLUMNS:
        if col in df.columns and df[col].notna().any():
            z = np.abs((df[col] - df[col].mean()) / (df[col].std() + 1e-9))
            mask2 &= z < n_std

    return df[mask2].copy()


def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """用前向填充 + 后向填充处理缺失值"""
    for col in METRIC_COLUMNS:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()
    return df


def aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """按天聚合：返回每日均值 + 记录数 + 不良占比"""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date"] = df["created_at"].dt.date

    agg = df.groupby("date").agg(
        avg_head_angle=("head_angle", "mean"),
        avg_shoulder_diff=("shoulder_diff", "mean"),
        avg_hunchback_score=("hunchback_score", "mean"),
        avg_body_tilt=("body_tilt", "mean"),
        avg_round_shoulder=("round_shoulder", "mean"),
        record_count=("head_angle", "count"),
    ).reset_index()

    # 不良坐姿占比（头部前倾 > 40 或 驼背 > 0.3）
    df["bad"] = (df["head_angle"] > 40) | (df["hunchback_score"] > 0.3)
    bad_ratio = df.groupby("date")["bad"].mean().reset_index()
    bad_ratio.columns = ["date", "bad_posture_ratio"]
    agg = agg.merge(bad_ratio, on="date", how="left")
    agg["bad_posture_ratio"] = agg["bad_posture_ratio"].fillna(0)

    return agg


def aggregate_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """按周聚合"""
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["week"] = df["created_at"].dt.isocalendar().week.astype(int)
    df["year"] = df["created_at"].dt.isocalendar().year.astype(int)

    agg = df.groupby(["year", "week"]).agg(
        avg_head_angle=("head_angle", "mean"),
        avg_shoulder_diff=("shoulder_diff", "mean"),
        avg_hunchback_score=("hunchback_score", "mean"),
        avg_body_tilt=("body_tilt", "mean"),
        avg_round_shoulder=("round_shoulder", "mean"),
        record_count=("head_angle", "count"),
    ).reset_index()

    df["bad"] = (df["head_angle"] > 40) | (df["hunchback_score"] > 0.3)
    bad_ratio = df.groupby(["year", "week"])["bad"].mean().reset_index()
    bad_ratio.columns = ["year", "week", "bad_posture_ratio"]
    agg = agg.merge(bad_ratio, on=["year", "week"], how="left")
    agg["bad_posture_ratio"] = agg["bad_posture_ratio"].fillna(0)

    return agg


def preprocess_pipeline(records: list) -> pd.DataFrame:
    """
    完整预处理流水线：
    ORM 列表 → DataFrame → 去异常 → 填充缺失 → 返回清洗后数据
    """
    df = records_to_dataframe(records)
    df = remove_outliers(df)
    df = fill_missing(df)
    return df
