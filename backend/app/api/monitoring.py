"""
系统监控API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.task_log import TaskLog
from app.api.dependencies import require_admin

router = APIRouter(prefix="/monitoring", tags=["系统监控"])


class TaskLogSchema(BaseModel):
    """任务日志模型"""
    id: int
    task_type: str
    task_id: Optional[str]
    status: str
    message: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TaskLogListResponse(BaseModel):
    """任务日志列表响应"""
    logs: List[TaskLogSchema]
    total: int


class SystemStats(BaseModel):
    """系统统计信息"""
    total_submissions: int
    total_drafts: int
    total_published: int
    pending_submissions: int
    failed_tasks_24h: int
    successful_tasks_24h: int


@router.get("/logs", response_model=TaskLogListResponse)
async def get_task_logs(
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取任务日志（仅管理员）
    """
    query = select(TaskLog)
    
    # 过滤条件
    if task_type:
        query = query.where(TaskLog.task_type == task_type)
    if status:
        query = query.where(TaskLog.status == status)
    
    # 排序和分页
    query = query.order_by(desc(TaskLog.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # 获取总数
    count_query = select(func.count(TaskLog.id))
    if task_type:
        count_query = count_query.where(TaskLog.task_type == task_type)
    if status:
        count_query = count_query.where(TaskLog.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return TaskLogListResponse(logs=logs, total=total)


@router.get("/stats", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取系统统计信息（仅管理员）
    """
    from app.models.submission import Submission
    from app.models.draft import Draft
    
    # 统计投稿数量
    submissions_result = await db.execute(select(func.count(Submission.id)))
    total_submissions = submissions_result.scalar()
    
    # 统计草稿数量
    drafts_result = await db.execute(select(func.count(Draft.id)))
    total_drafts = drafts_result.scalar()
    
    # 统计已发布数量
    published_result = await db.execute(
        select(func.count(Draft.id)).where(Draft.status == "published")
    )
    total_published = published_result.scalar()
    
    # 统计待处理投稿
    pending_result = await db.execute(
        select(func.count(Submission.id)).where(Submission.status == "pending")
    )
    pending_submissions = pending_result.scalar()
    
    # 统计24小时内的任务
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    failed_result = await db.execute(
        select(func.count(TaskLog.id)).where(
            TaskLog.created_at >= cutoff_time,
            TaskLog.status == "failed"
        )
    )
    failed_tasks_24h = failed_result.scalar()
    
    success_result = await db.execute(
        select(func.count(TaskLog.id)).where(
            TaskLog.created_at >= cutoff_time,
            TaskLog.status == "success"
        )
    )
    successful_tasks_24h = success_result.scalar()
    
    return SystemStats(
        total_submissions=total_submissions,
        total_drafts=total_drafts,
        total_published=total_published,
        pending_submissions=pending_submissions,
        failed_tasks_24h=failed_tasks_24h,
        successful_tasks_24h=successful_tasks_24h
    )


@router.post("/fetch-emails")
async def trigger_fetch_emails(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    手动触发邮件抓取（仅管理员）
    """
    from app.tasks.email_tasks import fetch_emails_task
    
    try:
        # 触发邮件抓取任务
        result = fetch_emails_task()
        return {
            "success": True,
            "message": "邮件抓取任务已执行",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"邮件抓取失败: {str(e)}")


@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
