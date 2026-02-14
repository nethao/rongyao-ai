"""
投稿相关的Pydantic模型
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class SubmissionImageSchema(BaseModel):
    """投稿图片模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    oss_url: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    compressed: bool = False


class DraftSummarySchema(BaseModel):
    """草稿摘要模型（用于投稿列表）"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: str
    current_version: int


class SubmissionBase(BaseModel):
    """投稿基础模型"""
    email_subject: Optional[str] = None
    email_from: Optional[str] = None
    original_content: str


class SubmissionCreate(SubmissionBase):
    """创建投稿模型"""
    pass


class SubmissionSchema(SubmissionBase):
    """投稿响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email_date: Optional[datetime] = None
    doc_file_path: Optional[str] = None
    docx_file_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    images: List[SubmissionImageSchema] = []
    drafts: List[DraftSummarySchema] = []


class SubmissionListResponse(BaseModel):
    """投稿列表响应模型"""
    items: List[SubmissionSchema]
    total: int
    page: int
    size: int
