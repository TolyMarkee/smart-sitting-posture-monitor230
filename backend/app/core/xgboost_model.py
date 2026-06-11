# XGBoost 健康评分模型

import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from .data_preprocess import preprocess_pipeline, METRIC_COLUMNS
from .model_manager import save_model, load_model


def _synthesize_health_score(df: pd.DataFrame) -> np.ndarray:
    """
    从指标合成健康评分标签（0-100分，100为最佳）
    用于无监督数据的训练目标值

    规则：
    - 头部前倾：正常 < 30° = 满分，每增加 1° 扣 1 分
    - 高低肩：正常 < 0.03 = 满分，每增加 0.01 扣 3 分
    - 驼背：正常 < 0.25 = 满分，每增加 0.05 扣 5 分
    - 身体倾斜：正常 < 3° = 满分，每增加 1° 扣 2 分
    - 圆肩：正常 < 0.15 = 满分，每增加 0.05 扣 5 分
    """
    scores = np.full(len(df), 100.0)

    penalty = 0

    # 头部前倾
    penalty += np.maximum(df["head_angle"].values - 30, 0) * 1.0
    # 高低肩
    penalty += np.maximum(df["shoulder_diff"].values - 0.03, 0) * 300
    # 驼背
    penalty += np.maximum(df["hunchback_score"].values - 0.25, 0) * 100
    # 身体倾斜
    penalty += np.maximum(df["body_tilt"].values - 3, 0) * 2.0
    # 圆肩
    penalty += np.maximum(df["round_shoulder"].values - 0.15, 0) * 100

    scores = np.clip(scores - penalty, 0, 100)
    return scores


def train_health_model(records: list) -> dict:
    """
    训练 XGBoost 健康评分模型

    Args:
        records: 坐姿记录列表

    Returns:
        dict: 训练结果
    """
    df = preprocess_pipeline(records)
    if df.empty or len(df) < 20:
        return {"error": f"数据量不足：仅有 {len(df)} 条记录，至少需要 20 条"}

    X = df[METRIC_COLUMNS].values
    y = _synthesize_health_score(df)

    model = XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X, y)

    # 特征重要性
    importance = dict(zip(METRIC_COLUMNS, model.feature_importances_))
    importance = {k: round(float(v), 4) for k, v in
                  sorted(importance.items(), key=lambda x: x[1], reverse=True)}

    # 保存模型
    model_path = save_model(
        model, "xgboost",
        {"n_samples": len(X), "r2_score": None},
    )

    return {
        "model_path": model_path,
        "n_samples": len(X),
        "feature_importance": importance,
    }


def predict_health_score(record: dict) -> dict:
    """
    预测单条记录的健康评分

    Args:
        record: {"head_angle": ..., "shoulder_diff": ..., ...}

    Returns:
        dict: 健康评分 + 各项扣分明细
    """
    # 输入验证：裁剪到物理有效范围
    head_angle = max(0, min(90, record.get("head_angle", 0) or 0))
    shoulder_diff = max(0, min(1, record.get("shoulder_diff", 0) or 0))
    hunchback_score = max(0, min(1, record.get("hunchback_score", 0) or 0))
    body_tilt = max(0, min(90, record.get("body_tilt", 0) or 0))
    round_shoulder = max(0, min(1, record.get("round_shoulder", 0) or 0))

    model = load_model("xgboost")

    # 特征向量
    features = np.array([[
        head_angle,
        shoulder_diff,
        hunchback_score,
        body_tilt,
        round_shoulder,
    ]])

    # 如果有模型用模型预测，否则用规则
    if model is not None:
        score = float(model.predict(features)[0])
        score = round(max(0, min(100, score)), 1)
    else:
        # 规则回退
        dummy_df = pd.DataFrame([record])
        score = round(float(_synthesize_health_score(dummy_df)[0]), 1)

    # 各项扣分明细（用裁剪后的值）
    detail = {}
    if head_angle > 30:
        detail["头部前倾"] = round((head_angle - 30) * 1.0, 1)
    if shoulder_diff > 0.03:
        detail["高低肩"] = round((shoulder_diff - 0.03) * 300, 1)
    if hunchback_score > 0.25:
        detail["驼背含胸"] = round((hunchback_score - 0.25) * 100, 1)
    if body_tilt > 3:
        detail["身体倾斜"] = round((body_tilt - 3) * 2.0, 1)
    if round_shoulder > 0.15:
        detail["圆肩"] = round((round_shoulder - 0.15) * 100, 1)

    # 评级
    if score >= 90:
        grade = "优秀"
    elif score >= 75:
        grade = "良好"
    elif score >= 60:
        grade = "一般"
    else:
        grade = "需要改善"

    return {
        "score": score,
        "grade": grade,
        "deductions": detail,
        "total_deduction": round(sum(detail.values()), 1) if detail else 0,
    }
