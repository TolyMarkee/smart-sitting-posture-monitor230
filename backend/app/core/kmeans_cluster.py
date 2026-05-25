# K-Means 坐姿模式聚类

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from .data_preprocess import preprocess_pipeline, METRIC_COLUMNS
from .model_manager import save_model, load_model


# 聚类标签中文名
CLUSTER_NAMES = {
    0: "标准坐姿型",
    1: "头部前倾型",
    2: "驼背含胸型",
    3: "高低肩型",
    4: "身体倾斜型",
}


def prepare_features(records: list) -> np.ndarray:
    """
    从数据库记录提取聚类特征矩阵

    Args:
        records: PostureRecord ORM 对象列表

    Returns:
        (N, 5) numpy 数组
    """
    df = preprocess_pipeline(records)
    if df.empty:
        return np.array([]).reshape(0, 5)

    # 只取5项核心指标
    available_cols = [c for c in METRIC_COLUMNS if c in df.columns]
    if len(available_cols) < 3:
        return np.array([]).reshape(0, len(available_cols))

    return df[available_cols].values


def _py_int(v):
    """numpy int64 → Python int（避免 JSON 序列化报错）"""
    return int(v) if hasattr(v, '__int__') else v

def _py_float(v):
    """numpy float64 → Python float"""
    return float(v) if hasattr(v, '__float__') else v


def find_optimal_k(X: np.ndarray, max_k: int = 6) -> int:
    """
    用肘部法则找最佳 K 值

    Args:
        X: 特征矩阵
        max_k: 最大 K 值

    Returns:
        int: 推荐的 K 值
    """
    if len(X) < 10:
        return min(2, len(X))

    max_k = min(max_k, len(X) - 1, 6)

    inertias = []
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X)
        inertias.append(km.inertia_)

    # 计算二阶差分找拐点
    if len(inertias) < 3:
        return 3

    diffs = np.diff(inertias)
    diffs2 = np.diff(diffs)
    elbow = _py_int(np.argmax(diffs2)) + 2

    return max(2, min(elbow + 1, max_k))


def train_kmeans(records: list, k: int = None) -> dict:
    """
    训练 K-Means 聚类模型

    Args:
        records: 坐姿记录列表
        k: 聚类数（None 则自动确定）

    Returns:
        dict: 训练结果（模型、聚类中心、标签分布等）
    """
    X = prepare_features(records)

    if len(X) < 10:
        return {"error": f"数据量不足：仅有 {len(X)} 条记录，至少需要 10 条"}

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 确定 K 值
    if k is None:
        k = _py_int(find_optimal_k(X_scaled))
    else:
        k = int(k)

    # 训练
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    # 保存模型
    model_path = save_model(
        {"kmeans": km, "scaler": scaler, "k": k},
        "kmeans",
        {"k": k, "n_samples": len(X), "inertia": float(km.inertia_)},
    )

    # 统计分布
    unique, counts = np.unique(labels, return_counts=True)
    distribution = {_py_int(u): _py_int(c) for u, c in zip(unique, counts)}

    # 聚类中心（反标准化）
    centers_raw = scaler.inverse_transform(km.cluster_centers_)

    # 分析每个聚类中心的特征
    centers_info = []
    for i in range(k):
        center = centers_raw[i]
        profile = {}

        # 头部前倾（正常 < 40°）
        if center[0] > 45:
            profile["head_tendency"] = "头部明显前倾"
        elif center[0] > 30:
            profile["head_tendency"] = "头部轻微前倾"
        else:
            profile["head_tendency"] = "头部正常"

        # 高低肩（正常 < 0.05）
        if center[1] > 0.07:
            profile["shoulder_tendency"] = "高低肩明显"
        elif center[1] > 0.04:
            profile["shoulder_tendency"] = "肩部轻微不平"
        else:
            profile["shoulder_tendency"] = "肩部正常"

        # 驼背（正常 < 0.3）
        if center[2] > 0.5:
            profile["hunchback_tendency"] = "驼背严重"
        elif center[2] > 0.3:
            profile["hunchback_tendency"] = "轻微含胸"
        else:
            profile["hunchback_tendency"] = "背部正常"

        # 身体倾斜（正常 < 5°）
        if center[3] > 8:
            profile["tilt_tendency"] = "身体明显倾斜"
        elif center[3] > 5:
            profile["tilt_tendency"] = "身体轻微倾斜"
        else:
            profile["tilt_tendency"] = "体态端正"

        # 圆肩（正常 < 0.2）
        if center[4] > 0.3:
            profile["round_shoulder_tendency"] = "圆肩明显"
        elif center[4] > 0.2:
            profile["round_shoulder_tendency"] = "轻微圆肩"
        else:
            profile["round_shoulder_tendency"] = "肩部正常"

        label_name = CLUSTER_NAMES.get(i, f"坐姿模式{i+1}")
        cnt = distribution.get(i, 0)
        centers_info.append({
            "cluster_id": int(i),
            "label": label_name,
            "count": int(cnt),
            "percentage": round(float(cnt) / len(labels) * 100, 1),
            "center": {
                "head_angle": round(_py_float(center[0]), 2),
                "shoulder_diff": round(_py_float(center[1]), 4),
                "hunchback_score": round(_py_float(center[2]), 4),
                "body_tilt": round(_py_float(center[3]), 2),
                "round_shoulder": round(_py_float(center[4]), 4),
            },
            "profile": profile,
        })

    return {
        "k": int(k),
        "inertia": round(_py_float(km.inertia_), 2),
        "n_samples": int(len(X)),
        "distribution": {int(k_): int(v_) for k_, v_ in distribution.items()},
        "clusters": centers_info,
        "model_path": model_path,
    }


def predict_cluster(records: list, single_record: list = None) -> dict:
    """
    预测某条记录属于哪个聚类

    Args:
        records: 全部历史记录（用于加载 scaler）
        single_record: 单条记录 [head_angle, shoulder_diff, hunchback_score, body_tilt, round_shoulder]

    Returns:
        dict: 聚类 ID 和标签
    """
    model_data = load_model("kmeans")
    if model_data is None:
        return {"error": "模型未训练，请先调用训练接口"}

    km = model_data["kmeans"]
    scaler = model_data["scaler"]

    record_arr = np.array(single_record).reshape(1, -1)
    record_scaled = scaler.transform(record_arr)
    label = int(km.predict(record_scaled)[0])

    return {
        "cluster_id": label,
        "label": CLUSTER_NAMES.get(label, f"坐姿模式{label+1}"),
    }
