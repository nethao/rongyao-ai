"""
配置相关的Pydantic模型
"""
from pydantic import BaseModel
from typing import Optional


class ConfigUpdate(BaseModel):
    """配置更新请求"""
    key: str
    value: str
    encrypted: bool = False
    description: Optional[str] = None


class ConfigResponse(BaseModel):
    """配置响应"""
    key: str
    value: str
    encrypted: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConfigVerifyResult(BaseModel):
    """配置验证结果"""
    valid: bool
    message: Optional[str] = None
