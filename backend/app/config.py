"""
系统配置管理
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "荣耀AI审核发布系统"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost/glory_audit"
    
    # Redis配置
    REDIS_URL: str = "redis://redis:6379/0"
    
    # JWT配置
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时
    
    # OpenAI配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    
    # 阿里云OSS配置
    OSS_ACCESS_KEY_ID: Optional[str] = None
    OSS_ACCESS_KEY_SECRET: Optional[str] = None
    OSS_ENDPOINT: Optional[str] = None
    OSS_BUCKET_NAME: Optional[str] = None
    
    # IMAP邮箱配置
    IMAP_HOST: Optional[str] = None
    IMAP_PORT: int = 993
    IMAP_USER: Optional[str] = None
    IMAP_PASSWORD: Optional[str] = None
    IMAP_USE_SSL: bool = True
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # 文件存储配置
    TEMP_FILE_DIR: str = "/tmp/glory_audit"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # 数据清理配置
    IMAGE_COMPRESS_DAYS: int = 365
    DATA_DELETE_DAYS: int = 730
    CLEANUP_SCHEDULE_HOUR: int = 2  # 凌晨2点
    
    # 性能配置
    MAX_CONCURRENT_TASKS: int = 10
    EMAIL_FETCH_INTERVAL_MINUTES: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
