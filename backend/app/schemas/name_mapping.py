"""
采编/文编名称映射的 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class EditorNameMappingSchema(BaseModel):
    """采编映射"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    created_at: datetime
    updated_at: datetime


class EditorNameMappingCreate(BaseModel):
    email: str
    display_name: str


class EditorNameMappingUpdate(BaseModel):
    display_name: str


class CopyEditorSiteMappingSchema(BaseModel):
    """文编站点映射"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    site_id: int
    display_name: str
    created_at: datetime
    updated_at: datetime
    site_name: Optional[str] = None


class CopyEditorSiteMappingCreate(BaseModel):
    user_id: int
    site_id: int
    display_name: str


class CopyEditorSiteMappingUpdate(BaseModel):
    display_name: str
