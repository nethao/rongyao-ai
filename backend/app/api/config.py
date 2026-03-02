"""
配置管理API端点
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.config_service import ConfigService
from app.schemas.config import ConfigUpdate, ConfigVerifyResult
from app.api.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/config", tags=["配置管理"])


@router.get("/", response_model=dict)
async def get_all_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取所有配置（管理员）
    """
    service = ConfigService(db)
    configs = await service.get_all_configs(include_encrypted=False)
    return {"configs": configs}


@router.put("/", response_model=dict)
async def update_config(
    config: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    更新配置项（管理员）
    """
    service = ConfigService(db)
    await service.set_config(
        key=config.key,
        value=config.value,
        encrypted=config.encrypted,
        description=config.description
    )
    return {"message": "配置更新成功"}


@router.post("/verify/llm", response_model=ConfigVerifyResult)
async def verify_llm_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    验证LLM配置（管理员）
    """
    service = ConfigService(db)
    valid = await service.verify_llm_config()
    return ConfigVerifyResult(
        valid=valid,
        message="LLM配置有效" if valid else "LLM配置无效或缺失"
    )


@router.post("/verify/oss", response_model=ConfigVerifyResult)
async def verify_oss_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    验证OSS配置（管理员）
    """
    service = ConfigService(db)
    valid = await service.verify_oss_config()
    return ConfigVerifyResult(
        valid=valid,
        message="OSS配置有效" if valid else "OSS配置无效或缺失"
    )


@router.post("/verify/wechat302", response_model=ConfigVerifyResult)
async def verify_wechat302_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    验证 302 微信抓取配置（管理员）
    """
    service = ConfigService(db)
    valid, message = await service.verify_wechat302_config()
    return ConfigVerifyResult(valid=valid, message=message)


@router.post("/verify/imap", response_model=ConfigVerifyResult)
@router.post("/verify/imap/", response_model=ConfigVerifyResult)
async def verify_imap_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    验证IMAP配置（管理员）
    """
    service = ConfigService(db)
    valid, message = await service.verify_imap_config()
    return ConfigVerifyResult(valid=valid, message=message)


@router.get("/auto-fetch-interval", response_model=dict)
async def get_auto_fetch_interval(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取自动抓取邮件间隔（分钟）
    """
    service = ConfigService(db)
    interval = await service.get_config("AUTO_FETCH_INTERVAL_MINUTES")
    return {"interval": int(interval) if interval else 0}


@router.put("/auto-fetch-interval", response_model=dict)
async def update_auto_fetch_interval(
    interval: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    设置自动抓取邮件间隔（分钟，0 表示禁用）
    """
    if interval < 0:
        return {"error": "间隔不能为负数"}
    
    service = ConfigService(db)
    await service.set_config(
        key="AUTO_FETCH_INTERVAL_MINUTES",
        value=str(interval),
        description="自动抓取邮件间隔（分钟，0表示禁用）"
    )
    
    # 重新加载 Celery Beat 配置
    from app.tasks import reload_beat_schedule
    reload_beat_schedule()
    
    return {
        "message": f"已设置自动抓取间隔为 {interval} 分钟" if interval > 0 else "已禁用自动抓取",
        "interval": interval
    }
