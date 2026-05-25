# ML 接口：聚类训练、健康评分、时序预测

import traceback
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db import crud

# 延迟导入 ML 模块（依赖缺失时给出友好提示）
_kmeans = None
_xgboost = None
_lstm = None

def _get_kmeans():
    global _kmeans
    if _kmeans is None:
        try:
            from ..core.kmeans_cluster import train_kmeans, predict_cluster
            _kmeans = (train_kmeans, predict_cluster)
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"K-Means 依赖缺失: {e}")
    return _kmeans

def _get_xgboost():
    global _xgboost
    if _xgboost is None:
        try:
            from ..core.xgboost_model import train_health_model, predict_health_score
            _xgboost = (train_health_model, predict_health_score)
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"XGBoost 依赖缺失: {e}")
    return _xgboost

def _get_lstm():
    global _lstm
    if _lstm is None:
        try:
            from ..core.lstm_model import train_lstm, predict_future
            _lstm = (train_lstm, predict_future)
        except ImportError as e:
            raise HTTPException(status_code=500, detail=f"LSTM 依赖缺失: {e}")
    return _lstm

router = APIRouter()


@router.post("/train-cluster")
def train_cluster(
    user_id: int = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    records = crud.get_records_by_time_range(db, user_id, start, end, limit=50000)

    train_kmeans_fn, _ = _get_kmeans()
    try:
        result = train_kmeans_fn(records)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"聚类训练失败: {e}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "success", **result}


@router.get("/cluster-result")
def get_cluster_result(
    user_id: int = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    records = crud.get_records_by_time_range(db, user_id, start, end, limit=50000)

    train_kmeans_fn, _ = _get_kmeans()
    try:
        result = train_kmeans_fn(records)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"聚类分析失败: {e}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "success", **result}


@router.post("/train-health-model")
def train_health(
    user_id: int = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    records = crud.get_records_by_time_range(db, user_id, start, end, limit=50000)

    train_fn = _get_xgboost()[0]
    try:
        result = train_fn(records)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"健康模型训练失败: {e}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "success", **result}


@router.post("/health-score")
def get_health_score(
    head_angle: float = Query(...),
    shoulder_diff: float = Query(...),
    hunchback_score: float = Query(...),
    body_tilt: float = Query(...),
    round_shoulder: float = Query(...),
):
    _, predict_fn = _get_xgboost()
    record = {
        "head_angle": head_angle,
        "shoulder_diff": shoulder_diff,
        "hunchback_score": hunchback_score,
        "body_tilt": body_tilt,
        "round_shoulder": round_shoulder,
    }
    try:
        return predict_fn(record)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train-lstm")
def train_forecast(
    user_id: int = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    records = crud.get_records_by_time_range(db, user_id, start, end, limit=50000)

    train_fn = _get_lstm()[0]
    try:
        result = train_fn(records)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"LSTM训练失败: {e}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "success", **result}


@router.get("/predict")
def get_prediction(
    user_id: int = Query(...),
    steps: int = Query(24),
    days: int = Query(7),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    records = crud.get_records_by_time_range(db, user_id, start, end, limit=50000)

    _, predict_fn = _get_lstm()
    try:
        result = predict_fn(records, steps)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"预测失败: {e}")

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "success", **result}


@router.get("/overall-report")
def get_overall_report(
    user_id: int = Query(...),
    days: int = Query(7),
    db: Session = Depends(get_db),
):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    records = crud.get_records_by_time_range(db, user_id, start, end, limit=50000)

    try:
        train_kmeans_fn, _ = _get_kmeans()
        cluster_result = train_kmeans_fn(records)
    except Exception as e:
        cluster_result = {"error": str(e)}

    train_health_fn, predict_health_fn = _get_xgboost()
    latest = crud.get_latest_record(db, user_id)
    health = None
    if latest:
        try:
            health = predict_health_fn({
                "head_angle": latest.head_angle or 0,
                "shoulder_diff": latest.shoulder_diff or 0,
                "hunchback_score": latest.hunchback_score or 0,
                "body_tilt": latest.body_tilt or 0,
                "round_shoulder": latest.round_shoulder or 0,
            })
        except Exception as e:
            health = {"score": 0, "grade": "错误", "error": str(e)}

    _, predict_fn = _get_lstm()
    try:
        forecast = predict_fn(records, steps=12)
    except Exception as e:
        forecast = {"error": str(e)}

    return {
        "status": "success",
        "cluster": cluster_result if "error" not in cluster_result else None,
        "health_score": health,
        "forecast": forecast if "error" not in forecast else None,
    }
