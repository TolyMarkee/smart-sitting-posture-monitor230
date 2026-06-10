# 定时任务：每日聚合统计

import asyncio
from datetime import datetime, date, timedelta
from ..db.session import SessionLocal
from ..db.crud import (
    get_records_by_time_range,
    upsert_daily_stat,
)
from ..core.data_preprocess import preprocess_pipeline, aggregate_daily
from ..utils.logger import logger


async def aggregate_yesterday():
    """将昨天的数据聚合写入 daily_stats 表"""
    yesterday = date.today() - timedelta(days=1)
    start = datetime.combine(yesterday, datetime.min.time())
    end = datetime.combine(yesterday, datetime.max.time())

    db = SessionLocal()
    try:
        # 获取昨天的所有记录
        records = get_records_by_time_range(db, user_id=1, start=start, end=end, limit=100000)

        if not records:
            logger.info(f"[Scheduler] {yesterday} 无数据，跳过聚合")
            return

        df = preprocess_pipeline(records)
        daily = aggregate_daily(df)

        if daily.empty:
            return

        row = daily.iloc[0]
        stat_data = {
            "user_id": 1,
            "stat_date": yesterday,
            "avg_head_angle": round(float(row["avg_head_angle"]), 4),
            "avg_shoulder_diff": round(float(row["avg_shoulder_diff"]), 4),
            "avg_hunchback_score": round(float(row["avg_hunchback_score"]), 4),
            "avg_body_tilt": round(float(row["avg_body_tilt"]), 4),
            "avg_round_shoulder": round(float(row["avg_round_shoulder"]), 4),
            "record_count": int(row["record_count"]),
            "bad_posture_ratio": round(float(row["bad_posture_ratio"]), 4),
        }
        upsert_daily_stat(db, stat_data)
        logger.info(f"[Scheduler] {yesterday} 聚合完成: {int(row['record_count'])} 条记录")

    except Exception as e:
        logger.error(f"[Scheduler] {yesterday} 聚合失败: {e}")
    finally:
        db.close()


async def clean_old_tasks():
    """清理过期的未完成每日任务"""
    from ..db.session import SessionLocal
    from ..db import models
    from datetime import date as dt_date, datetime as dt

    db = SessionLocal()
    try:
        today_start = dt.combine(dt_date.today(), dt.min.time())
        deleted = db.query(models.UserTask).filter(
            models.UserTask.task_type == "daily",
            models.UserTask.created_at < today_start,
        ).delete()
        db.commit()
        if deleted > 0:
            logger.info(f"[Scheduler] 清理了 {deleted} 条过期任务")
    except Exception as e:
        logger.error(f"[Scheduler] 清理任务失败: {e}")
        db.rollback()
    finally:
        db.close()


async def run_scheduler():
    """后台定时任务循环 — 每天凌晨执行聚合 + 清理过期任务"""
    logger.info("[Scheduler] 定时任务已启动，每天凌晨 1:00 执行")

    while True:
        now = datetime.now()
        next_run = now.replace(hour=1, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run += timedelta(days=1)
        wait_seconds = (next_run - now).total_seconds()
        logger.info(f"[Scheduler] 下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S')} ({wait_seconds/3600:.1f}h)")
        await asyncio.sleep(wait_seconds)

        await clean_old_tasks()
        await aggregate_yesterday()
