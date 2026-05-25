"""
智能客服对话接口

工作流程:
  1. 前端发来用户消息 + user_id
  2. 后端从数据库拉取用户最新坐姿数据
  3. 将坐姿数据注入到系统提示词中
  4. 调用 DeepSeek API 获取 AI 回复
  5. 保存对话记录到 chat_history 表
  6. 返回 AI 回复给前端
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db import crud
from ..utils.llm_client import chat, build_posture_context

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = None
    user_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    posture_context: Optional[str] = None


@router.post("/message", response_model=ChatResponse)
async def chat_message(payload: ChatRequest, db: Session = Depends(get_db)):
    """智能客服对话（自动保存记录）"""
    try:
        # 1. 保存用户消息
        if payload.user_id:
            crud.save_chat_message(db, payload.user_id, "user", payload.message)

        # 2. 构建坐姿数据上下文
        posture_ctx = None
        if payload.user_id:
            posture_ctx = build_posture_context(db, payload.user_id)

        # 3. 调用大模型
        reply = await chat(payload.message, payload.history or [], posture_ctx)

        # 4. 保存 AI 回复
        if payload.user_id:
            crud.save_chat_message(db, payload.user_id, "assistant", reply)

        return ChatResponse(reply=reply, posture_context=posture_ctx)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI 服务异常: {str(e)}")


@router.get("/history")
def get_history(
    user_id: int,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """获取用户的聊天记录（页面加载时恢复对话）"""
    records = crud.get_chat_history(db, user_id, limit)
    return {
        "messages": [
            {
                "role": r.role,
                "content": r.content,
                "time": r.created_at.strftime("%H:%M:%S") if r.created_at else "",
            }
            for r in records
        ],
    }


@router.delete("/history")
def clear_history(
    user_id: int,
    db: Session = Depends(get_db),
):
    """清空聊天记录"""
    crud.clear_chat_history(db, user_id)
    return {"status": "success", "message": "聊天记录已清空"}
