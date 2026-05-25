#ORM 模型（与数据库schema.sql表对应）

from sqlalchemy import Column, Integer, Float, DateTime, String
from sqlalchemy.sql import func
from .session import Base

class PostureRecord(Base):
    __tablename__ = "posture_records"   # 与 schema.sql 中的表名一致

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    head_angle = Column(Float, nullable=True)
    shoulder_diff = Column(Float, nullable=True)
    hunchback_score = Column(Float, nullable=True)
    body_tilt = Column(Float, nullable=True)
    round_shoulder = Column(Float, nullable=True)
    posture_label = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())