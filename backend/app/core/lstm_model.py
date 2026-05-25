# LSTM 时序预测模型

import numpy as np
import pandas as pd
from .data_preprocess import preprocess_pipeline, METRIC_COLUMNS
from .model_manager import save_model, load_model


# 尝试导入 TensorFlow，不可用时降级
try:
    import tensorflow as tf

    HAS_TF = True
except ImportError:
    HAS_TF = False


def _create_sequences(data: np.ndarray, seq_len: int = 20) -> tuple:
    """将时间序列转换为监督学习格式"""
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i: i + seq_len])
        y.append(data[i + seq_len])
    return np.array(X), np.array(y)


def train_lstm(records: list, seq_len: int = 20, epochs: int = 30) -> dict:
    """
    训练 LSTM 时序预测模型

    Args:
        records: 坐姿记录列表（需按时间排序）
        seq_len: 输入序列长度
        epochs: 训练轮数

    Returns:
        dict: 训练结果
    """
    if not HAS_TF:
        return {
            "error": "TensorFlow 未安装，请执行: pip install tensorflow==2.15.0",
            "fallback": "使用移动平均进行预测",
        }

    df = preprocess_pipeline(records)
    if df.empty or len(df) < seq_len + 10:
        return {"error": f"数据量不足：需要至少 {seq_len + 10} 条记录，当前 {len(df)} 条"}

    # 提取特征
    data = df[METRIC_COLUMNS].values.astype(np.float32)

    # 标准化
    mean = data.mean(axis=0)
    std = data.std(axis=0) + 1e-9
    data_norm = (data - mean) / std

    # 构建序列
    X, y = _create_sequences(data_norm, seq_len)

    if len(X) < 5:
        return {"error": f"训练样本不足：{len(X)} 个"}

    # 划分训练/验证集
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    # 构建模型
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, activation="tanh", return_sequences=True,
                             input_shape=(seq_len, len(METRIC_COLUMNS))),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.LSTM(32, activation="tanh"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(len(METRIC_COLUMNS)),
    ])

    model.compile(optimizer="adam", loss="mse")
    model.fit(X_train, y_train, validation_data=(X_val, y_val),
              epochs=epochs, batch_size=16, verbose=0)

    # 验证集损失
    val_loss = model.evaluate(X_val, y_val, verbose=0)

    # 保存
    model_path = save_model(
        {"lstm": model, "mean": mean, "std": std, "seq_len": seq_len},
        "lstm",
        {"seq_len": seq_len, "n_samples": len(df), "val_loss": float(val_loss)},
    )

    return {
        "model_path": model_path,
        "n_samples": len(df),
        "seq_len": seq_len,
        "val_loss": round(float(val_loss), 6),
    }


def predict_future(records: list, steps: int = 24) -> dict:
    """
    预测未来 N 步的坐姿趋势

    Args:
        records: 历史记录
        steps: 预测步数（默认 24 步，如每 5 分钟一条 = 预测 2 小时）

    Returns:
        dict: 预测结果
    """
    df = preprocess_pipeline(records)
    if df.empty:
        return {"error": "无有效数据"}

    data = df[METRIC_COLUMNS].values.astype(np.float32)

    model_data = load_model("lstm")

    if model_data is None or not HAS_TF:
        # 回退：移动平均
        last_values = data[-1]
        hist_avg = data[-20:].mean(axis=0) if len(data) >= 20 else data.mean(axis=0)
        predictions = []
        for i in range(steps):
            alpha = min(1.0, (i + 1) / steps)
            pred = last_values * (1 - alpha) + hist_avg * alpha
            predictions.append(pred.tolist())
        pred_array = np.array(predictions)
    else:
        lstm = model_data["lstm"]
        mean = model_data["mean"]
        std = model_data["std"]
        seq_len = model_data["seq_len"]

        # 取最后 seq_len 条作为输入
        last_seq = data[-seq_len:]
        last_seq_norm = (last_seq - mean) / std

        predictions = []
        current_seq = last_seq_norm.copy()

        for _ in range(steps):
            inp = current_seq[-seq_len:].reshape(1, seq_len, -1)
            pred_norm = lstm.predict(inp, verbose=0)[0]
            predictions.append(pred_norm.tolist())

            # 滑动窗口：去掉第一条，加入预测值
            current_seq = np.vstack([current_seq[1:], pred_norm.reshape(1, -1)])

        pred_array = np.array(predictions) * std + mean

    return {
        "steps": steps,
        "metrics": METRIC_COLUMNS,
        "predictions": [
            {
                "step": i,
                "head_angle": round(float(pred_array[i][0]), 2),
                "shoulder_diff": round(float(pred_array[i][1]), 4),
                "hunchback_score": round(float(pred_array[i][2]), 4),
                "body_tilt": round(float(pred_array[i][3]), 2),
                "round_shoulder": round(float(pred_array[i][4]), 4),
            }
            for i in range(steps)
        ],
    }
