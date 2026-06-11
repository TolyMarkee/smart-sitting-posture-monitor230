"""
用户认证相关的 Pydantic 校验模型
Pydantic 会自动校验请求/响应数据格式，不合法则返回 422 错误
"""

from pydantic import BaseModel
from typing import Optional


# ---- 认证 ----
class UserRegister(BaseModel):
    """注册请求"""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录成功后返回的 JWT"""
    access_token: str
    token_type: str = "bearer"
    username: str
    user_id: int
    role: str = "user"


# ---- 用户信息 ----
class UserProfile(BaseModel):
    """用户公开信息（返回给前端展示）"""
    id: int
    username: str
    email: str
    nickname: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    points: int = 0
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """用户自己修改资料（只能改昵称/手机/邮箱）"""
    nickname: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class PasswordChange(BaseModel):
    """修改密码"""
    old_password: str
    new_password: str


# ---- 管理员 ----
class AdminUserUpdate(BaseModel):
    """管理员修改用户（可以改角色和启用状态）"""
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
