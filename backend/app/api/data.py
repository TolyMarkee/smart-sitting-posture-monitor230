# 数据接口：上传 + 历史查询 + 聚合统计

import os, json, httpx, asyncio
from datetime import datetime, date, timedelta
from typing import Optional
import random
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db import crud
from ..schemas.posture import PostureCreate
from ..core.data_preprocess import preprocess_pipeline, aggregate_daily
from ..api.ws import manager

router = APIRouter()


# ---- 为当前用户生成模拟数据 ----
@router.post("/generate-demo")
def generate_demo_data(
    user_id: int = Query(...),
    days: int = Query(7, le=30),
    records_per_hour: int = Query(120, le=500),
    db: Session = Depends(get_db),
):
    """为指定用户生成模拟坐姿数据（开发和测试用）"""
    import random
    import numpy as np
    from datetime import timedelta as td

    created = 0
    now = datetime.utcnow()
    for day_offset in range(days, 0, -1):
        base = now - td(days=day_offset)
        base = base.replace(hour=8, minute=0, second=0, microsecond=0)
        for minute in range(0, 480, 5):  # 8小时，每5分钟一条
            ts = base + td(minutes=minute)
            # 模拟坐姿逐渐变差
            fatigue = minute / 480.0  # 0→1
            record = {
                "head_angle": round(random.gauss(22 + fatigue * 15, 5), 2),
                "shoulder_diff": round(abs(random.gauss(0.02 + fatigue * 0.02, 0.01)), 4),
                "hunchback_score": round(abs(random.gauss(0.15 + fatigue * 0.2, 0.08)), 4),
                "body_tilt": round(abs(random.gauss(2.0 + fatigue * 4, 1.5)), 2),
                "round_shoulder": round(abs(random.gauss(0.08 + fatigue * 0.12, 0.05)), 4),
                "posture_label": "normal" if fatigue < 0.4 else ("mild" if fatigue < 0.7 else "moderate"),
                "confidence": round(random.uniform(0.7, 0.95), 4),
            }
            record["user_id"] = user_id
            record["created_at"] = ts
            try:
                crud.create_posture_record(db, record)
                created += 1
            except Exception:
                db.rollback()
    return {"status": "success", "created": created, "user_id": user_id, "days": days}


# ---- 天气代理（高德 API）----
@router.get("/weather")
def get_weather(
    city: str = Query(default="440100", description="城市编码（默认广州）"),
):
    """代理高德天气 API"""
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "settings.json"))
    amap_key = ""
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                amap_key = json.load(f).get("amap_key", "")
        except Exception:
            pass

    print(f"[Weather] settings_path={settings_path}, exists={os.path.exists(settings_path)}, key={'***' if amap_key else 'EMPTY'}")
    if not amap_key:
        return {
            "status": "demo",
            "city": "演示城市",
            "weather": "晴",
            "temperature": "26",
            "humidity": "55",
            "winddirection": "东南风",
            "reporttime": datetime.utcnow().isoformat(),
            "_hint": "请管理员在系统设置中配置高德API Key",
        }

    try:
        resp = httpx.get(
            "https://restapi.amap.com/v3/weather/weatherInfo",
            params={"key": amap_key, "city": city, "extensions": "base"},
            timeout=10,
        )
        data = resp.json()
        if data.get("status") == "1" and data.get("lives"):
            live = data["lives"][0]
            return {
                "status": "success",
                "city": live.get("city"),
                "weather": live.get("weather"),
                "temperature": live.get("temperature"),
                "humidity": live.get("humidity"),
                "winddirection": live.get("winddirection"),
                "reporttime": live.get("reporttime"),
            }
    except Exception:
        pass
    return {"status": "error", "message": "天气服务不可用"}


# ---- 城市查询（高德）----
@router.get("/city-lookup")
def city_lookup(name: str = Query(...)):
    """根据城市名模糊查询 adcode（返回匹配列表，用于联想搜索）"""
    settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "settings.json"))
    amap_key = ""
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                amap_key = json.load(f).get("amap_key", "")
        except Exception:
            pass

    if not amap_key:
        return {"status": "error", "message": "管理员未配置高德API Key"}

    try:
        resp = httpx.get(
            "https://restapi.amap.com/v3/config/district",
            params={"key": amap_key, "keywords": name, "subdistrict": 0, "offset": 10},
            timeout=10,
        )
        data = resp.json()
        results = []
        if data.get("districts"):
            for d in data["districts"]:
                # 只返回市级行政区
                if d.get("level") == "city" and d.get("adcode"):
                    results.append({"adcode": d["adcode"], "name": d["name"]})
            # 如果没找到市级结果，返回第一个有效结果
            if not results:
                for d in data["districts"]:
                    if d.get("adcode"):
                        results.append({"adcode": d["adcode"], "name": d["name"]})
        return {"status": "success", "cities": results[:10]}
    except Exception:
        pass
    return {"status": "error", "message": "城市查询失败"}


@router.post("/upload")
async def upload_posture_data(record: PostureCreate, db: Session = Depends(get_db)):
    """接收边缘端上传的单条坐姿数据，并通过 WebSocket 广播"""
    data = record.model_dump(exclude={"timestamp"})
    if record.timestamp:
        data["created_at"] = record.timestamp

    db_record = crud.create_posture_record(db, data)

    # 异步广播给所有 WebSocket 客户端（不阻塞 HTTP 响应）
    broadcast_data = {
        "type": "new_data",
        "payload": {
            "id": db_record.id,
            "user_id": db_record.user_id,
            "head_angle": db_record.head_angle,
            "shoulder_diff": db_record.shoulder_diff,
            "hunchback_score": db_record.hunchback_score,
            "body_tilt": db_record.body_tilt,
            "round_shoulder": db_record.round_shoulder,
            "posture_label": db_record.posture_label,
            "confidence": db_record.confidence,
            "keypoints": db_record.keypoints if db_record.keypoints else "[]",
            "created_at": db_record.created_at.isoformat(),
        }
    }
    asyncio.create_task(manager.broadcast(broadcast_data))

    return {"status": "success", "id": db_record.id}


@router.get("/latest")
def get_latest_record(user_id: int = Query(...), db: Session = Depends(get_db)):
    """获取用户最新一条坐姿记录"""
    record = crud.get_latest_record(db, user_id)
    if record is None:
        return {"status": "empty", "record": None}
    return {
        "status": "success",
        "record": {
            "id": record.id,
            "user_id": record.user_id,
            "head_angle": record.head_angle,
            "shoulder_diff": record.shoulder_diff,
            "hunchback_score": record.hunchback_score,
            "body_tilt": record.body_tilt,
            "round_shoulder": record.round_shoulder,
            "posture_label": record.posture_label,
            "confidence": record.confidence,
                "keypoints": record.keypoints,
            "created_at": record.created_at.isoformat(),
        },
    }


@router.get("/history")
def get_history_records(
    user_id: int = Query(...),
    start: Optional[str] = Query(None, description="开始时间 ISO 格式"),
    end: Optional[str] = Query(None, description="结束时间 ISO 格式"),
    limit: int = Query(500, le=2000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """按时间范围查询历史记录，默认最近7天"""
    if not start or not end:
        now = datetime.utcnow()
        end = end or now.isoformat()
        start = start or (now - timedelta(days=7)).isoformat()

    # 处理前端发来的各种 ISO 格式（含 Z / +00:00 / 无时区）
    def parse_iso(s: str) -> datetime:
        s = s.strip()
        # 去掉末尾 Z 替换为 +00:00
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            # 尝试去掉毫秒
            if "." in s:
                s = s[: s.index(".")]
                if s.endswith("+00:00") or s.endswith("-00:00"):
                    pass  # keep timezone
                dt = datetime.fromisoformat(s)
            else:
                raise HTTPException(status_code=400, detail=f"时间格式错误: {start}")
        # 去掉时区转为 naive datetime
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt

    start_dt = parse_iso(start)
    end_dt = parse_iso(end)

    records = crud.get_records_by_time_range(db, user_id, start_dt, end_dt, limit, offset)

    return {
        "status": "success",
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "head_angle": r.head_angle,
                "shoulder_diff": r.shoulder_diff,
                "hunchback_score": r.hunchback_score,
                "body_tilt": r.body_tilt,
                "round_shoulder": r.round_shoulder,
                "posture_label": r.posture_label,
                "confidence": r.confidence,
                    "keypoints": r.keypoints,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


@router.get("/daily-summary")
def get_daily_summary(
    user_id: int = Query(...),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """获取每日统计汇总（实时聚合）"""
    if not start_date or not end_date:
        today = date.today()
        end_date = end_date or today.isoformat()
        start_date = start_date or (today - timedelta(days=30)).isoformat()

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，使用 YYYY-MM-DD")

    # 实时从原始数据聚合（始终最新）
    start_dt = datetime.fromisoformat(start_date + "T00:00:00")
    end_dt = datetime.fromisoformat(end_date + "T23:59:59")
    records = crud.get_records_by_time_range(db, user_id, start_dt, end_dt, limit=50000)
    df = aggregate_daily(preprocess_pipeline(records))

    if df.empty:
        return {"status": "success", "count": 0, "stats": []}

    return {
        "status": "success",
        "count": len(df),
        "stats": [
            {
                "stat_date": str(row["date"]),
                "avg_head_angle": round(float(row["avg_head_angle"]), 4),
                "avg_shoulder_diff": round(float(row["avg_shoulder_diff"]), 4),
                "avg_hunchback_score": round(float(row["avg_hunchback_score"]), 4),
                "avg_body_tilt": round(float(row["avg_body_tilt"]), 4),
                "avg_round_shoulder": round(float(row["avg_round_shoulder"]), 4),
                "record_count": int(row["record_count"]),
                "bad_posture_ratio": round(float(row["bad_posture_ratio"]), 4),
            }
            for _, row in df.iterrows()
        ],
    }
