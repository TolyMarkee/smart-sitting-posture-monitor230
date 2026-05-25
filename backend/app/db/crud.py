# 数据库增删改查封装

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models


# ============================================
# 用户相关
# ============================================

def create_user(db: Session, username: str, email: str, password_hash: str) -> models.User:
    """创建用户"""
    user = models.User(username=username, email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    """根据ID查询用户"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """根据用户名查询用户"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """根据邮箱查询用户"""
    return db.query(models.User).filter(models.User.email == email).first()


def update_user(db: Session, user_id: int, updates: dict) -> Optional[models.User]:
    """更新用户信息（只更新提供的字段）"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    for key, value in updates.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def list_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """管理员接口：列出所有用户"""
    return db.query(models.User).offset(skip).limit(limit).all()


def count_users(db: Session) -> int:
    """管理员接口：统计用户总数"""
    return db.query(func.count(models.User.id)).scalar()


def delete_user(db: Session, user_id: int) -> bool:
    """管理员接口：删除用户"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


# ============================================
# 聊天记录相关
# ============================================

def save_chat_message(db: Session, user_id: int, role: str, content: str) -> models.ChatHistory:
    """保存一条聊天记录"""
    msg = models.ChatHistory(user_id=user_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_chat_history(db: Session, user_id: int, limit: int = 100) -> List[models.ChatHistory]:
    """获取用户最近的聊天记录"""
    return (
        db.query(models.ChatHistory)
        .filter(models.ChatHistory.user_id == user_id)
        .order_by(models.ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )


def clear_chat_history(db: Session, user_id: int):
    """清空用户聊天记录"""
    db.query(models.ChatHistory).filter(models.ChatHistory.user_id == user_id).delete()
    db.commit()


# ============================================
# 坐姿记录相关
# ============================================

def create_posture_record(db: Session, record_data: dict) -> models.PostureRecord:
    """创建一条坐姿记录"""
    record = models.PostureRecord(**record_data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_latest_record(db: Session, user_id: int) -> Optional[models.PostureRecord]:
    """获取用户最新一条记录"""
    return (
        db.query(models.PostureRecord)
        .filter(models.PostureRecord.user_id == user_id)
        .order_by(models.PostureRecord.created_at.desc())
        .first()
    )


def get_records_by_time_range(
    db: Session,
    user_id: int,
    start: datetime,
    end: datetime,
    limit: int = 1000,
    offset: int = 0,
) -> List[models.PostureRecord]:
    """按时间范围查询用户的坐姿记录"""
    return (
        db.query(models.PostureRecord)
        .filter(
            models.PostureRecord.user_id == user_id,
            models.PostureRecord.created_at >= start,
            models.PostureRecord.created_at <= end,
        )
        .order_by(models.PostureRecord.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_records_count_by_time_range(
    db: Session, user_id: int, start: datetime, end: datetime
) -> int:
    """统计时间范围内的记录数"""
    return (
        db.query(func.count(models.PostureRecord.id))
        .filter(
            models.PostureRecord.user_id == user_id,
            models.PostureRecord.created_at >= start,
            models.PostureRecord.created_at <= end,
        )
        .scalar()
    )


def get_daily_records(db: Session, user_id: int, day: date) -> List[models.PostureRecord]:
    """获取某天的所有记录"""
    start = datetime.combine(day, datetime.min.time())
    end = datetime.combine(day, datetime.max.time())
    return get_records_by_time_range(db, user_id, start, end)


# ============================================
# 每日统计相关
# ============================================

def upsert_daily_stat(db: Session, stat_data: dict) -> models.DailyStat:
    """创建或更新每日统计"""
    existing = (
        db.query(models.DailyStat)
        .filter(
            models.DailyStat.user_id == stat_data["user_id"],
            models.DailyStat.stat_date == stat_data["stat_date"],
        )
        .first()
    )
    if existing:
        for key, value in stat_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        stat = models.DailyStat(**stat_data)
        db.add(stat)
        db.commit()
        db.refresh(stat)
        return stat


def get_daily_stats_by_range(
    db: Session, user_id: int, start_date: date, end_date: date
) -> List[models.DailyStat]:
    """获取日期范围内的每日统计"""
    return (
        db.query(models.DailyStat)
        .filter(
            models.DailyStat.user_id == user_id,
            models.DailyStat.stat_date >= start_date,
            models.DailyStat.stat_date <= end_date,
        )
        .order_by(models.DailyStat.stat_date.asc())
        .all()
    )
