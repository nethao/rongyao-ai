"""
认证相关的Pydantic模型
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    role: str
    wp_author_id: Optional[int] = None  # WordPress作者ID


class UserCreate(UserBase):
    """用户创建模型"""
    password: str


class UserUpdate(BaseModel):
    """用户更新模型"""
    role: str  # 'admin' | 'editor'
    wp_author_id: Optional[int] = None  # WordPress作者ID


class AdminResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求"""
    new_password: str


class User(UserBase):
    """用户响应模型"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str = "bearer"
    user: User


class PasswordChangeRequest(BaseModel):
    """修改密码请求"""
    old_password: str
    new_password: str


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


class UserListResponse(BaseModel):
    """用户列表响应"""
    items: List[User]
    total: int
    page: int
    size: int
