"""
Celery异步任务
"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings

# 创建Celery应用实例
celery_app = Celery(
    "glory_audit",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# 动态加载定时任务配置
def get_beat_schedule():
    """从数据库读取定时任务配置"""
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from app.services.config_service import ConfigService
        
        async def _get_interval():
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            async with async_session() as session:
                cs = ConfigService(session)
                interval = await cs.get_config("AUTO_FETCH_INTERVAL_MINUTES")
                await engine.dispose()
                return int(interval) if interval else 0
        
        interval = asyncio.run(_get_interval())
    except Exception:
        interval = 0  # 默认禁用
    
    schedule = {}
    
    # 自动抓取邮件（如果启用）
    if interval > 0:
        schedule["auto-fetch-emails"] = {
            "task": "fetch_emails",
            "schedule": interval * 60.0,  # 转换为秒
        }
    
    return schedule

# 初始化定时任务
celery_app.conf.beat_schedule = get_beat_schedule()

def reload_beat_schedule():
    """重新加载定时任务配置"""
    celery_app.conf.beat_schedule = get_beat_schedule()

# 导入任务模块（在应用启动时自动发现）
celery_app.autodiscover_tasks(["app.tasks"])

# 显式导入所有任务
from app.tasks.email_tasks import fetch_emails_task  # noqa
from app.tasks.transform_tasks import transform_content_task  # noqa

# 供命令行 `celery -A app.tasks worker` 识别的入口（Celery 默认查找 app 或 celery）
app = celery_app
