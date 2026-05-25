#上传接口
#接收坐姿数据（/api/v1/data/upload）

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db import models
from ..schemas.posture import PostureCreate

router = APIRouter()

@router.post("/upload")
def upload_posture_data(record: PostureCreate, db: Session = Depends(get_db)):
    # 将 Pydantic 模型转换为 ORM 模型
    db_record = models.PostureRecord(**record.dict(exclude={"timestamp"}))

    # 若提供 timestamp，则手动赋值
    if record.timestamp:
        db_record.created_at = record.timestamp

    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return {"status": "success", "id": db_record.id}