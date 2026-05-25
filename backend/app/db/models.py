"""
ORM 数据模型（对应 database/schema.sql 中的每张表）

每个 Python 类 = 数据库中的一张表
每个类属性 = 表中的一个列
SQLAlchemy 会自动把 Python 对象操作翻译成 SQL 语句
"""

from sqlalchemy import Column, Integer, Float, DateTime, String, Boolean, Date, Text
from sqlalchemy.sql import func
from .session import Base


# ============================================================
# 用户表
# role 字段说明:
#   "super_admin" = 超级管理员（可管理所有用户包括其他管理员，可发公告）
#   "admin"       = 普通管理员（可查看所有用户数据，不可管理其他管理员）
#   "user"        = 普通用户（只能查看自己的数据）
# ============================================================
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username      = Column(String(50), nullable=False, unique=True, comment="用户名")
    email         = Column(String(100), nullable=False, unique=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="bcrypt 哈希")
    nickname      = Column(String(50), nullable=True, comment="显示昵称")
    phone         = Column(String(20), nullable=True, comment="手机号")
    avatar_url    = Column(String(255), nullable=True, comment="头像URL")
    role          = Column(String(20), nullable=False, default="user", comment="super_admin/admin/user")
    points        = Column(Integer, nullable=False, default=0, comment="用户积分")
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# 系统公告表
# ============================================================
class Announcement(Base):
    __tablename__ = "announcements"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title      = Column(String(200), nullable=False, comment="公告标题")
    content    = Column(Text, nullable=False, comment="公告内容")
    created_by = Column(Integer, nullable=False, comment="发布者ID")
    is_active  = Column(Boolean, nullable=False, default=True, comment="是否展示")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# 每日任务表
# ============================================================
class UserTask(Base):
    __tablename__ = "user_tasks"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id     = Column(Integer, nullable=False, index=True)
    title       = Column(String(200), nullable=False, comment="任务名称")
    description = Column(String(500), nullable=True, comment="任务描述")
    task_type   = Column(String(50), nullable=False, default="daily", comment="daily/weekly/achievement")
    points      = Column(Integer, nullable=False, default=10, comment="完成奖励积分")
    status      = Column(String(20), nullable=False, default="pending", comment="pending/done")
    done_at     = Column(DateTime(timezone=True), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# 坐姿记录表
# 每条记录 = K230 板端上传的一次坐姿检测结果
# 5 项指标通过几何算法从 YOLOv8-Pose 的 17 个关键点计算得出
# ============================================================
class PostureRecord(Base):
    __tablename__ = "posture_records"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id         = Column(Integer, nullable=False, index=True, comment="所属用户ID")
    head_angle      = Column(Float, nullable=True, comment="头部前倾角度（度），耳朵-肩膀中点连线与垂直轴夹角")
    shoulder_diff   = Column(Float, nullable=True, comment="高低肩比例 = 高度差/肩宽")
    hunchback_score = Column(Float, nullable=True, comment="驼背前倾比例 = 鼻子-肩膀水平偏移/垂直距离")
    body_tilt       = Column(Float, nullable=True, comment="身体倾斜角度（度）")
    round_shoulder  = Column(Float, nullable=True, comment="圆肩比例 = 肩肘中点偏移/肩宽")
    posture_label   = Column(String(50), nullable=True, comment="综合标签: normal/mild/moderate/severe")
    confidence      = Column(Float, nullable=True, comment="YOLOv8-Pose 检测置信度")
    created_at      = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# 每日统计表
# 由定时任务(scheduler.py)每天凌晨1点自动聚合昨天的数据
# ============================================================
class DailyStat(Base):
    __tablename__ = "daily_stats"

    id                  = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id             = Column(Integer, nullable=False)
    stat_date           = Column(Date, nullable=False, comment="统计日期")
    avg_head_angle      = Column(Float, nullable=True, comment="当日头部前倾角度均值")
    avg_shoulder_diff   = Column(Float, nullable=True)
    avg_hunchback_score = Column(Float, nullable=True)
    avg_body_tilt       = Column(Float, nullable=True)
    avg_round_shoulder  = Column(Float, nullable=True)
    record_count        = Column(Integer, nullable=False, default=0)
    bad_posture_ratio   = Column(Float, nullable=True, comment="不良坐姿占比(0~1)")
    worst_label         = Column(String(50), nullable=True, comment="当日最严重坐姿标签")
    created_at          = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# 聊天记录表
# 保存用户与智能客服(AI)的对话历史
# 用户每次发送消息 + AI回复 = 一对记录
# ============================================================
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id    = Column(Integer, nullable=False, index=True, comment="所属用户ID")
    role       = Column(String(20), nullable=False, comment="角色: user(用户发的) / assistant(AI回的)")
    content    = Column(Text, nullable=False, comment="消息内容")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
