# FastAPI 入口

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 加载 .env 文件（优先级：backend/.env > 项目根 .env）
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv()

from .db.session import engine, SessionLocal, Base
from .db import models  # 确保所有 ORM 模型被加载
from .db import crud
from .db.crud import get_user_by_username, create_user
from .utils.security import hash_password
from sqlalchemy import text
import asyncio
from .api import data, auth, ml, chat, ws
from .services import video_proxy
from .utils.logger import logger
from .tasks.scheduler import run_scheduler


def migrate_tables():
    """自动迁移：给已有表添加新列（SQLAlchemy create_all 不支持 ALTER）"""
    with engine.connect() as conn:
        # users 表新增字段
        for col, col_def in [
            ("nickname", "VARCHAR(50) DEFAULT NULL"),
            ("phone", "VARCHAR(20) DEFAULT NULL"),
            ("avatar_url", "VARCHAR(255) DEFAULT NULL"),
            ("role", "VARCHAR(20) NOT NULL DEFAULT 'user'"),
            ("points", "INT NOT NULL DEFAULT 0"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_def}"))
            except Exception:
                pass  # 字段已存在则忽略
        # posture_records 新增字段
        for col, col_def in [
            ("keypoints", "TEXT NULL"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE posture_records ADD COLUMN {col} {col_def}"))
            except Exception:
                pass
        conn.commit()


def safe_create_user(db, username, email, password, role="user", nickname=None):
    """
    安全创建用户：先检查是否已存在，创建失败则 rollback 恢复 session。
    返回 True 表示新创建，False 表示已存在。
    """
    existing = get_user_by_username(db, username)
    if existing:
        return False
    try:
        u = create_user(db, username, email, hash_password(password))
        if role == "admin" or nickname:
            crud.update_user(db, u.id, {"role": role, "nickname": nickname or username})
        print(f"[Init] 已创建: {username} (role={role})")
        return True
    except Exception as e:
        db.rollback()  # ★ 关键：重置 session，否则后续查询全部报错
        print(f"[Init] 创建 {username} 失败: {e}")
        return False


def init_database():
    """启动时自动建表 + 迁移 + 初始化默认用户"""
    Base.metadata.create_all(bind=engine)
    migrate_tables()

    db = SessionLocal()
    try:
        safe_create_user(db, "test", "test@example.com", "123456", "user", "测试用户")
        safe_create_user(db, "admin", "admin@posture.com", "admin123", "super_admin", "系统管理员")
        # 修复已有 admin 用户角色（如果之前创建时使用了旧角色名 "admin"）
        existing_admin = get_user_by_username(db, "admin")
        if existing_admin and existing_admin.role != "super_admin":
            try:
                crud.update_user(db, existing_admin.id, {"role": "super_admin"})
                print("[Init] 已将 admin 升级为 super_admin")
            except Exception:
                db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    scheduler_task = asyncio.create_task(run_scheduler())
    logger.info("[Init] 后端启动完成")
    yield
    scheduler_task.cancel()
    logger.info("[Init] 后端关闭")


app = FastAPI(title="智能坐姿监测系统 API", version="1.0.0", lifespan=lifespan)

# 允许前端 Vue 开发服务器跨域访问
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(data.router, prefix="/api/v1/data", tags=["data"])
app.include_router(ml.router, prefix="/api/v1/ml", tags=["ml"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(ws.router, tags=["ws"])
app.include_router(video_proxy.router, tags=["video"])


@app.get("/")
def root():
    return {"message": "Smart Sitting Posture Monitor Backend"}
