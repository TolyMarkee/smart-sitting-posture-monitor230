# 模型管理器：保存、加载、版本管理

import os
import pickle
import json
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def save_model(model, name: str, metadata: dict = None) -> str:
    """
    保存模型到磁盘

    Args:
        model: 任意 Python 对象（sklearn model、keras model 等）
        name: 模型名称（如 "kmeans"、"xgboost"）
        metadata: 额外元数据（超参、训练时间等）

    Returns:
        str: 模型文件路径
    """
    version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{version}.pkl"
    filepath = os.path.join(MODEL_DIR, filename)

    with open(filepath, "wb") as f:
        pickle.dump(model, f)

    # 保存元数据
    if metadata:
        meta_path = filepath.replace(".pkl", ".json")
        meta_data = {
            "name": name,
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            **metadata,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)

    # 更新 latest 软链
    latest_path = os.path.join(MODEL_DIR, f"{name}_latest.pkl")
    with open(filepath, "rb") as src:
        with open(latest_path, "wb") as dst:
            dst.write(src.read())

    return filepath


def load_model(name: str):
    """
    加载最新版本的模型

    Args:
        name: 模型名称

    Returns:
        model 或 None
    """
    latest_path = os.path.join(MODEL_DIR, f"{name}_latest.pkl")
    if not os.path.exists(latest_path):
        # 尝试找最近版本
        files = sorted(
            [f for f in os.listdir(MODEL_DIR) if f.startswith(name) and f.endswith(".pkl") and "latest" not in f],
            reverse=True,
        )
        if not files:
            return None
        latest_path = os.path.join(MODEL_DIR, files[0])

    try:
        with open(latest_path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def model_exists(name: str) -> bool:
    """检查模型是否已存在"""
    return load_model(name) is not None


def list_models() -> list:
    """列出所有已保存的模型"""
    models = []
    for f in os.listdir(MODEL_DIR):
        if f.endswith(".pkl"):
            filepath = os.path.join(MODEL_DIR, f)
            size_kb = os.path.getsize(filepath) / 1024
            models.append({
                "filename": f,
                "size_kb": round(size_kb, 1),
            })
    return models
