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

# 定时任务配置
celery_app.conf.beat_schedule = {
    # 每5分钟抓取邮件
    "fetch-emails-every-5-minutes": {
        "task": "email.fetch_emails",
        "schedule": 300.0,  # 5分钟
    },
    # 每天凌晨2点执行清理任务
    "daily-cleanup-at-2am": {
        "task": "cleanup.daily_cleanup",
        "schedule": crontab(hour=2, minute=0),
    },
}

# 导入任务模块（在应用启动时自动发现）
celery_app.autodiscover_tasks(["app.tasks"])

# 显式导入所有任务
from app.tasks.email_tasks import fetch_emails_task  # noqa
from app.tasks.transform_tasks import transform_content_task  # noqa

# 供命令行 `celery -A app.tasks worker` 识别的入口（Celery 默认查找 app 或 celery）
app = celery_app
