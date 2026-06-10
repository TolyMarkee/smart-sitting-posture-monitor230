#请求数据校验模型

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PostureCreate(BaseModel):
    user_id: int
    head_angle: float
    shoulder_diff: float
    hunchback_score: float
    body_tilt: float
    round_shoulder: float
    posture_label: str
    confidence: float
    timestamp: Optional[datetime] = None
    keypoints: Optional[str] = None  # JSON: [[x,y,conf], ...] x17 个关键点