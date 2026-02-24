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
    
    # 数据库配置（无安全默认值，必须通过 .env 或环境变量提供）
    DATABASE_URL: str = "postgresql+asyncpg://postgres:CHANGE_ME@localhost/glory_audit"
    
    # Redis配置
    REDIS_URL: str = "redis://redis:6379/0"
    
    # JWT配置（无安全默认值）
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 独立加密密钥（用于 Fernet 加密站点密码等，与 JWT 密钥分离）
    ENCRYPTION_KEY: str = ""
    
    # CORS 允许的前端域名（逗号分隔，如 "https://e.com,http://localhost:3000"）
    ALLOWED_ORIGINS: str = ""
    
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

# 启动时安全校验：关键密钥不能为空或使用已知弱默认值
_INSECURE_DEFAULTS = {
    "", "your-secret-key-change-in-production",
    "your-super-secret-jwt-key-change-this-in-production",
    "CHANGE_ME",
}
if settings.JWT_SECRET_KEY in _INSECURE_DEFAULTS:
    raise RuntimeError(
        "FATAL: JWT_SECRET_KEY 未设置或使用了不安全的默认值。"
        "请在 .env 或环境变量中设置一个 32 字符以上的随机密钥。"
    )
if settings.ENCRYPTION_KEY in _INSECURE_DEFAULTS:
    raise RuntimeError(
        "FATAL: ENCRYPTION_KEY 未设置。"
        "请在 .env 或环境变量中设置 Fernet 兼容的 base64 密钥。"
    )
