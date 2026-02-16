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
    compressed: Optional[bool] = False


class DraftSummarySchema(BaseModel):
    """草稿摘要模型（用于投稿列表）"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: str
    current_version: Optional[int] = 1  # DB 可能为 NULL，兼容旧数据


class SubmissionBase(BaseModel):
    """投稿基础模型"""
    email_subject: Optional[str] = None
    email_from: Optional[str] = None
    original_content: Optional[str] = ""  # 列表/详情兼容 DB 空值


class SubmissionCreate(SubmissionBase):
    """创建投稿模型"""
    pass


class ManualSubmissionCreate(BaseModel):
    """手动创建投稿模型"""
    email_subject: str  # 标题（必填）
    original_content: str  # 内容（必填）
    email_from: Optional[str] = None  # 采编（可选，默认当前用户）
    cooperation_type: Optional[str] = None  # 合作方式：free/partner
    media_type: Optional[str] = None  # 媒体类型
    source_unit: Optional[str] = None  # 来稿单位
    content_source: Optional[str] = "text"  # 内容来源，默认 text


class SubmissionSchema(SubmissionBase):
    """投稿响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email_date: Optional[datetime] = None
    doc_file_path: Optional[str] = None
    docx_file_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    
    # 邮件解析元数据
    cooperation_type: Optional[str] = None  # 合作方式
    media_type: Optional[str] = None  # 媒体类型
    source_unit: Optional[str] = None  # 来稿单位
    target_site_id: Optional[int] = None  # 目标站点ID
    content_source: Optional[str] = None  # 内容来源: weixin, meipian, doc, docx, text
    
    created_at: datetime
    updated_at: datetime
    images: List[SubmissionImageSchema] = []
    drafts: List[DraftSummarySchema] = []
    can_edit: Optional[bool] = True  # 当前用户是否可编辑


class SubmissionListResponse(BaseModel):
    """投稿列表响应模型"""
    items: List[SubmissionSchema]
    total: int
    page: int
    size: int


class ContentPreviewResponse(BaseModel):
    """内容预览响应模型（用于手动发布第一步）"""
    title: str  # 提取的标题
    content: str  # 提取的内容（Markdown格式，带占位符）
    preview_html: str  # 预览HTML（图片已上传OSS）
    original_html: Optional[str] = None  # 原始HTML（公众号/美篇）
    content_source: str  # 内容来源：weixin, meipian, doc, docx
    image_count: int = 0  # 图片数量
    media_map: Optional[dict] = None  # 占位符到OSS URL的映射


class ManualSubmissionCreateFromPreview(BaseModel):
    """从预览创建投稿模型"""
    title: str  # 标题
    content: str  # 内容（带占位符）
    original_html: Optional[str] = None  # 原始HTML
    content_source: str  # 内容来源
    media_map: Optional[dict] = None  # 占位符到OSS URL的映射
    email_from: str  # 采编
    cooperation_type: str  # 合作方式
    media_type: str  # 发布媒体
    source_unit: str  # 来稿单位
