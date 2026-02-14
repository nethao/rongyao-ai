"""
WordPress站点相关的Pydantic模型
"""
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class WordPressSiteBase(BaseModel):
    """WordPress站点基础模型"""
    name: str
    url: str
    api_username: Optional[str] = None
    active: bool = True


class WordPressSiteCreate(WordPressSiteBase):
    """创建WordPress站点请求"""
    api_password: Optional[str] = None


class WordPressSiteUpdate(BaseModel):
    """更新WordPress站点请求"""
    name: Optional[str] = None
    url: Optional[str] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    active: Optional[bool] = None


class WordPressSite(WordPressSiteBase):
    """WordPress站点响应"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WordPressSiteList(BaseModel):
    """WordPress站点列表响应"""
    sites: list[WordPressSite]
    total: int


class PublishRequest(BaseModel):
    """发布请求"""
    site_id: int


class PublishResult(BaseModel):
    """发布结果"""
    success: bool
    wordpress_post_id: Optional[int] = None
    message: Optional[str] = None
    site_name: Optional[str] = None
