"""
草稿相关的Pydantic模型
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class DraftVersionSchema(BaseModel):
    """草稿版本模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    version_number: int
    content: str
    created_by: Optional[int] = None
    created_at: datetime


class DraftBase(BaseModel):
    """草稿基础模型"""
    current_content: str


class DraftCreate(DraftBase):
    """创建草稿模型"""
    submission_id: int


class DraftUpdate(BaseModel):
    """更新草稿模型"""
    content: str


class DraftSchema(DraftBase):
    """草稿响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    submission_id: int
    current_version: int
    status: str
    published_at: Optional[datetime] = None
    published_to_site_id: Optional[int] = None
    wordpress_post_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class DraftDetailSchema(DraftSchema):
    """草稿详情模型（包含原文）"""
    original_content: str  # 来自关联的submission
    original_html: Optional[str] = None  # 公众号原始 HTML，用于还原排版
    email_subject: Optional[str] = None  # 文章标题
    content_source: Optional[str] = None  # 内容来源：weixin/meipian/word等
    

class DraftVersionListResponse(BaseModel):
    """草稿版本列表响应"""
    versions: List[DraftVersionSchema]


class RestoreVersionRequest(BaseModel):
    """恢复版本请求"""
    version_id: int
