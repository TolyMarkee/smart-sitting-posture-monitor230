"""
认证接口：注册、登录、个人中心、管理员

JWT Token 流程:
  1. 用户登录 → 后端验证密码 → 生成 JWT → 返回给前端
  2. 前端存 localStorage → 每次请求携带 Authorization: Bearer <token>
  3. 后端解析 JWT → 获取 user_id → 查数据库 → 返回对应数据
"""

from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import json, os
from ..db.session import get_db
from ..db import models
from ..db import crud, models
from ..schemas.user import (
    UserRegister, UserLogin, TokenResponse,
    UserProfile, UserUpdate, PasswordChange, AdminUserUpdate,
)
from ..utils.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)

router = APIRouter()


# ---------- 辅助函数：从请求头解析当前用户 ----------
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> models.User:
    """
    从 HTTP 请求头 Authorization 中提取 JWT，解析出当前用户。
    所有需要登录的接口都调用此函数做身份验证。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")

    token = authorization[7:]  # 去掉 "Bearer " 前缀
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user_id = int(payload.get("sub", 0))
    user = crud.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已被禁用")
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """检查当前用户是否为管理员（admin 或 super_admin）"""
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def require_super_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """检查当前用户是否为超级管理员"""
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


# ============================================================
# 注册 & 登录
# ============================================================

@router.post("/register")
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """用户注册：创建新账号"""
    if crud.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=409, detail="用户名已存在")
    if crud.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="邮箱已被注册")

    crud.create_user(db, payload.username, payload.email, hash_password(payload.password))
    return {"status": "success", "message": "注册成功"}


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """用户登录：验证密码 → 返回 JWT token"""
    user = crud.get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        username=user.username,
        user_id=user.id,
        role=user.role,
    )


# ============================================================
# 个人中心（需要登录）
# ============================================================

@router.get("/profile", response_model=UserProfile)
def get_profile(
    current_user: models.User = Depends(get_current_user),
):
    """获取当前登录用户的个人信息"""
    return UserProfile(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        nickname=current_user.nickname,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else "",
    )


@router.put("/profile")
def update_profile(
    payload: UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改个人资料（昵称/手机/邮箱）"""
    # 检查邮箱唯一性
    if payload.email and payload.email != current_user.email:
        if crud.get_user_by_email(db, payload.email):
            raise HTTPException(status_code=409, detail="邮箱已被使用")

    updates = payload.model_dump(exclude_none=True)
    crud.update_user(db, current_user.id, updates)
    return {"status": "success", "message": "资料更新成功"}


@router.put("/change-password")
def change_password(
    payload: PasswordChange,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码：验证旧密码 → 更新为新密码"""
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码不正确")

    crud.update_user(db, current_user.id, {"password_hash": hash_password(payload.new_password)})
    return {"status": "success", "message": "密码修改成功"}


# ============================================================
# 管理员接口（需要 admin 角色）
# ============================================================

@router.get("/admin/users")
def admin_list_users(
    skip: int = 0,
    limit: int = 50,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员：列出所有用户"""
    users = crud.list_all_users(db, skip, limit)
    total = crud.count_users(db)
    return {
        "total": total,
        "users": [
            {
                "id": u.id, "username": u.username, "email": u.email,
                "nickname": u.nickname, "role": u.role, "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else "",
            }
            for u in users
        ],
    }


@router.put("/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """超级管理员：修改任意用户（角色/状态/信息）"""
    target = crud.get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.role == "super_admin" and admin.id != user_id:
        raise HTTPException(status_code=403, detail="不能修改其他超级管理员")

    updates = payload.model_dump(exclude_none=True)
    crud.update_user(db, user_id, updates)
    return {"status": "success", "message": f"用户 {user_id} 已更新"}


@router.delete("/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    admin: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """超级管理员：删除用户"""
    if admin.id == user_id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    target = crud.get_user_by_id(db, user_id)
    if target and target.role == "super_admin":
        raise HTTPException(status_code=403, detail="不能删除超级管理员")
    if crud.delete_user(db, user_id):
        return {"status": "success", "message": f"用户 {user_id} 已删除"}
    raise HTTPException(status_code=404, detail="用户不存在")


@router.post("/admin/create-user")
def admin_create_user(
    username: str,
    email: str,
    password: str,
    role: str = "user",
    nickname: str = "",
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员：创建新用户"""
    if crud.get_user_by_username(db, username):
        raise HTTPException(status_code=409, detail="用户名已存在")
    if crud.get_user_by_email(db, email):
        raise HTTPException(status_code=409, detail="邮箱已被注册")

    try:
        u = crud.create_user(db, username, email, hash_password(password))
        crud.update_user(db, u.id, {"role": role, "nickname": nickname or username})
        return {"status": "success", "user_id": u.id, "message": f"用户 {username} 已创建"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 公告接口
# ============================================================
from pydantic import BaseModel as PydanticBase

class AnnouncementCreate(PydanticBase):
    title: str
    content: str

@router.get("/announcements")
def list_announcements(db: Session = Depends(get_db)):
    """获取活跃公告列表"""
    anns = db.query(models.Announcement).filter(
        models.Announcement.is_active == True
    ).order_by(models.Announcement.created_at.desc()).limit(10).all()
    return {"announcements": [
        {"id": a.id, "title": a.title, "content": a.content, "created_at": a.created_at.isoformat()}
        for a in anns
    ]}

@router.post("/announcements")
def create_announcement(
    payload: AnnouncementCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员：发布公告"""
    a = models.Announcement(title=payload.title, content=payload.content, created_by=admin.id)
    db.add(a)
    db.commit()
    return {"status": "success", "id": a.id}

@router.delete("/announcements/{ann_id}")
def delete_announcement(
    ann_id: int,
    admin: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """超级管理员：删除公告"""
    a = db.query(models.Announcement).filter(models.Announcement.id == ann_id).first()
    if a:
        a.is_active = False
        db.commit()
    return {"status": "success"}


# ============================================================
# 每日任务 + 积分
# ============================================================
@router.get("/tasks")
def get_my_tasks(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的任务列表"""
    tasks = db.query(models.UserTask).filter(
        models.UserTask.user_id == current_user.id
    ).order_by(models.UserTask.created_at.desc()).limit(50).all()
    return {"tasks": [
        {"id": t.id, "title": t.title, "description": t.description,
         "task_type": t.task_type, "points": t.points, "status": t.status,
         "done_at": t.done_at.isoformat() if t.done_at else None}
        for t in tasks
    ], "total_points": current_user.points or 0}

@router.post("/tasks/{task_id}/done")
def complete_task(
    task_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """完成一个任务，获得积分"""
    task = db.query(models.UserTask).filter(
        models.UserTask.id == task_id,
        models.UserTask.user_id == current_user.id,
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status == "done":
        raise HTTPException(status_code=400, detail="任务已完成")

    from datetime import datetime as dt
    task.status = "done"
    task.done_at = dt.utcnow()
    current_user.points = (current_user.points or 0) + task.points
    db.commit()
    return {"status": "success", "points_earned": task.points, "total_points": current_user.points}


@router.post("/tasks/generate-daily")
def generate_daily_tasks(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """为用户生成今日任务（并自动清理昨日未完成任务）"""
    from datetime import datetime as dt
    today_start = dt.combine(date_type.today(), dt.min.time())
    # 清理昨天及以前的未完成任务
    db.query(models.UserTask).filter(
        models.UserTask.user_id == current_user.id,
        models.UserTask.task_type == "daily",
        models.UserTask.status == "pending",
        models.UserTask.created_at < today_start,
    ).delete()
    db.commit()

    today_count = db.query(models.UserTask).filter(
        models.UserTask.user_id == current_user.id,
        models.UserTask.task_type == "daily",
        models.UserTask.created_at >= today_start,
    ).count()

    if today_count > 0:
        return {"status": "already_generated", "count": today_count}

    daily_tasks = [
        ("保持良好坐姿30分钟", "连续30分钟坐姿标签为normal", 20),
        ("完成一次站立休息", "站起来活动2分钟", 15),
        ("检查今日坐姿报告", "查看健康报告页面", 10),
        ("做5分钟颈部拉伸", "完成一组颈部拉伸运动", 15),
        ("使用智能客服咨询", "向AI助手询问一个坐姿问题", 5),
    ]
    for title, desc, pts in daily_tasks:
        t = models.UserTask(user_id=current_user.id, title=title,
                            description=desc, task_type="daily", points=pts)
        db.add(t)
    db.commit()
    return {"status": "success", "count": len(daily_tasks)}

@router.put("/admin/tasks/{task_id}")
def admin_update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    points: Optional[int] = None,
    status: Optional[str] = None,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员：编辑任意任务"""
    task = db.query(models.UserTask).filter(models.UserTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if title is not None: task.title = title
    if description is not None: task.description = description
    if points is not None: task.points = points
    if status is not None: task.status = status
    db.commit()
    return {"status": "success"}

@router.get("/admin/all-tasks")
def admin_list_all_tasks(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员：查看所有用户的任务"""
    tasks = db.query(models.UserTask).order_by(models.UserTask.created_at.desc()).limit(200).all()
    return {"tasks": [
        {"id": t.id, "user_id": t.user_id, "title": t.title, "description": t.description,
         "task_type": t.task_type, "points": t.points, "status": t.status}
        for t in tasks
    ]}

@router.post("/admin/tasks/create-for-user")
def admin_create_task_for_user(
    user_id: int,
    title: str,
    description: str = "",
    task_type: str = "daily",
    points: int = 10,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """管理员：为指定用户创建任务"""
    t = models.UserTask(user_id=user_id, title=title, description=description,
                        task_type=task_type, points=points)
    db.add(t)
    db.commit()
    return {"status": "success", "id": t.id}


# ============================================================
# 系统设置（管理员配置 API Key，无需改代码）
# ============================================================
SETTINGS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "settings.json"))

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(data):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[Settings] 已保存到 {SETTINGS_FILE}")

@router.get("/admin/settings")
def get_settings(admin: models.User = Depends(require_admin)):
    """管理员：读取系统设置"""
    return {"settings": load_settings()}

@router.put("/admin/settings")
def update_settings(
    amap_key: Optional[str] = None,
    weather_key: Optional[str] = None,
    admin: models.User = Depends(require_admin),
):
    """管理员：更新系统设置（高德API Key等）"""
    s = load_settings()
    if amap_key is not None: s["amap_key"] = amap_key
    if weather_key is not None: s["weather_key"] = weather_key
    save_settings(s)
    return {"status": "success", "settings": s}
