"""
边缘端数据上传模块
运行在 K230 庐山派板上，负责将坐姿分析结果上传到后端服务器

功能:
- HTTP POST 上传坐姿数据到后端 API
- 上传失败时本地缓存（JSON 文件）
- 网络恢复后自动重传缓存数据
- 缓存过期清理（超过7天的缓存自动删除）
"""

import os
import time
import gc
from datetime import datetime, timedelta

# K230 MicroPython 使用 ujson
try:
    import ujson as json
except ImportError:
    import json

# K230 MicroPython 的 urequests 库
try:
    import urequests as requests
except ImportError:
    # 本地测试时回退到标准 requests
    import requests


# ── 配置 ────────────────────────────────────────
# 注意：URL 中的 IP 需要是你后端服务器的实际 IP（K230 和 PC 在同一局域网内）
UPLOAD_URL = "http://192.168.1.100:8000/api/v1/data/upload"
CACHE_DIR = "/sdcard/examples/cache"           # K230 本地缓存目录
CACHE_EXPIRE_DAYS = 7                           # 缓存过期天数
UPLOAD_TIMEOUT = 5                               # 上传超时秒数
MAX_CACHE_SIZE = 500                             # 最多缓存条数（防止 SD 卡写满）


def ensure_cache_dir():
    """确保缓存目录存在"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        pass


def cache_filename():
    """生成缓存文件名（按小时分组）"""
    now = datetime.now()
    return f"sitting_cache_{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}.json"


def save_to_cache(record):
    """
    将上传失败的记录保存到本地缓存

    Args:
        record: dict，单条坐姿记录（已包含 timestamp）
    """
    ensure_cache_dir()
    filepath = f"{CACHE_DIR}/{cache_filename()}"

    # 读取已有缓存
    cached = []
    try:
        with open(filepath, "r") as f:
            cached = json.load(f)
    except Exception:
        pass

    # 限制缓存大小
    if len(cached) >= MAX_CACHE_SIZE:
        cached = cached[-MAX_CACHE_SIZE // 2:]

    cached.append(record)

    try:
        with open(filepath, "w") as f:
            json.dump(cached, f)
    except Exception as e:
        print(f"[Uploader] 缓存写入失败: {e}")


def upload_record(record):
    """
    上传单条记录到后端

    Args:
        record: dict，包含所有 PoseData 字段 + user_id

    Returns:
        bool: 上传成功返回 True，失败返回 False
    """
    try:
        resp = requests.post(UPLOAD_URL, json=record, timeout=UPLOAD_TIMEOUT)
        if resp.status_code == 200:
            resp.close()
            return True
        resp.close()
        return False
    except Exception as e:
        print(f"[Uploader] 上传失败: {e}")
        return False


def retry_cached_files():
    """
    遍历缓存目录，尝试重新上传失败的记录
    上传成功后删除对应的缓存文件
    """
    ensure_cache_dir()

    try:
        files = [f for f in os.listdir(CACHE_DIR) if f.startswith("sitting_cache_") and f.endswith(".json")]
    except Exception:
        return

    for filename in sorted(files):  # 按时间顺序重传
        filepath = f"{CACHE_DIR}/{filename}"
        try:
            with open(filepath, "r") as f:
                cached = json.load(f)
        except Exception:
            os.remove(filepath) if os.path.exists(filepath) else None
            continue

        if not cached:
            os.remove(filepath) if os.path.exists(filepath) else None
            continue

        # 逐条重传
        failed = []
        for record in cached:
            if upload_record(record):
                print(f"[Uploader] 缓存重传成功")
            else:
                failed.append(record)

        if failed:
            # 还有失败的，写回
            try:
                with open(filepath, "w") as f:
                    json.dump(failed, f)
            except Exception:
                pass
        else:
            os.remove(filepath) if os.path.exists(filepath) else None
            print(f"[Uploader] 缓存文件 {filename} 全部重传成功，已删除")


def clean_expired_cache():
    """清理过期的缓存文件"""
    ensure_cache_dir()

    try:
        files = [f for f in os.listdir(CACHE_DIR) if f.startswith("sitting_cache_") and f.endswith(".json")]
    except Exception:
        return

    cutoff = datetime.now() - timedelta(days=CACHE_EXPIRE_DAYS)
    removed = 0

    for filename in files:
        filepath = f"{CACHE_DIR}/{filename}"
        try:
            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat[8])  # st_mtime
            if mtime < cutoff:
                os.remove(filepath)
                removed += 1
        except Exception:
            pass

    if removed > 0:
        print(f"[Uploader] 清理了 {removed} 个过期缓存文件")


def upload(posture_issues, keypoints_summary, timestamp=None):
    """
    主上传接口 — 由 main.py 的推理循环调用

    Args:
        posture_issues: PostureAnalyzer.analyze() 返回的体态问题列表
                        每个元素为 dict: {type, name, severity, value, description}
        keypoints_summary: dict, 关键点数据摘要，包含各项指标的原始值:
                           {head_angle, shoulder_diff, hunchback_score,
                            body_tilt, round_shoulder, confidence}
        timestamp: str, ISO格式时间戳，默认用当前时间
    """
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    # 根据所有检测结果确定综合标签
    severities = [issue["severity"] for issue in posture_issues]
    severity_order = {"normal": 0, "mild": 1, "moderate": 2, "severe": 3}
    worst = "normal"
    for s in severities:
        if severity_order.get(s, 0) > severity_order.get(worst, 0):
            worst = s

    # 组合所有问题的描述
    posture_label = "normal" if not posture_issues else ";".join(
        f"{p['type']}:{p['severity']}" for p in posture_issues
    )

    record = {
        "user_id": 1,  # 默认用户，后期可配置
        "head_angle": round(keypoints_summary.get("head_angle", 0.0), 4),
        "shoulder_diff": round(keypoints_summary.get("shoulder_diff", 0.0), 4),
        "hunchback_score": round(keypoints_summary.get("hunchback_score", 0.0), 4),
        "body_tilt": round(keypoints_summary.get("body_tilt", 0.0), 4),
        "round_shoulder": round(keypoints_summary.get("round_shoulder", 0.0), 4),
        "posture_label": posture_label,
        "confidence": round(keypoints_summary.get("confidence", 0.0), 4),
        "timestamp": timestamp,
    }

    if not upload_record(record):
        # 上传失败，缓存到本地
        save_to_cache(record)

    gc.collect()  # K230 内存有限，及时回收
