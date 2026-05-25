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
    timestamp: Optional[datetime] = None   # 若上传则使用，要不就是后端自动生成