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
    from app.models.duplicate_log import DuplicateLog
    
    superseded_ids = select(DuplicateLog.superseded_submission_id).where(
        DuplicateLog.superseded_submission_id.isnot(None)
    )
    
    # 统计投稿数量（排除被替换的旧稿）
    submissions_result = await db.execute(
        select(func.count(Submission.id)).where(~Submission.id.in_(superseded_ids))
    )
    total_submissions = submissions_result.scalar()
    
    # 统计草稿数量
    drafts_result = await db.execute(select(func.count(Draft.id)))
    total_drafts = drafts_result.scalar()
    
    # 统计已发布数量
    published_result = await db.execute(
        select(func.count(Draft.id)).where(Draft.status == "published")
    )
    total_published = published_result.scalar()
    
    # 统计待处理投稿（排除被替换的旧稿）
    pending_result = await db.execute(
        select(func.count(Submission.id))
        .where(Submission.status == "pending")
        .where(~Submission.id.in_(superseded_ids))
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
    手动触发邮件抓取（仅管理员）- 异步执行
    """
    from app.tasks.email_tasks import fetch_emails_task
    
    try:
        # 异步触发邮件抓取任务
        task = fetch_emails_task.delay()
        return {
            "success": True,
            "message": "邮件抓取任务已启动",
            "task_id": task.id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动邮件抓取失败: {str(e)}")


@router.get("/fetch-emails/status")
async def get_fetch_emails_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取最新的邮件抓取任务状态（仅管理员）。只返回「本次任务」的日志：
    从最近一条 status=started 到当前的所有 fetch_email 日志。
    """
    # 查询最近的 fetch_email 日志（足够多以便找到本次 run 的起点）
    query = (
        select(TaskLog)
        .where(TaskLog.task_type == "fetch_email")
        .order_by(desc(TaskLog.created_at))
        .limit(50)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    if not rows:
        return {
            "status": "idle",
            "message": "暂无邮件抓取任务",
            "logs": []
        }

    # 只认「本轮抓取」的 started：message 为「开始抓取邮箱未读邮件」，避免把单封邮件的 started 当成本轮起点
    RUN_START_MESSAGE = "开始抓取邮箱未读邮件"
    run_start_idx = None
    for i, log in enumerate(rows):
        if log.status == "started" and log.message and log.message.strip() == RUN_START_MESSAGE:
            run_start_idx = i
            break
    
    if run_start_idx is None:
        # 没找到本轮开始，返回最近10条日志（按时间正序）
        recent_logs = list(reversed(rows[:10]))
        latest = rows[0] if rows else None
        if not latest:
            return {
                "status": "idle",
                "message": "暂无邮件抓取任务",
                "logs": []
            }
        return {
            "status": latest.status,
            "message": latest.message,
            "created_at": latest.created_at.isoformat(),
            "logs": [
                {"status": log.status, "message": log.message, "created_at": log.created_at.isoformat()}
                for log in recent_logs
            ]
        }

    # 本轮任务日志：从该 run 起点到当前，按时间正序
    # rows 是倒序（最新的在前），run_start_idx 对应本轮最早一条 started，
    # 因此应取 rows[:run_start_idx+1]（本轮所有日志，倒序）再 reversed 为正序。
    run_rows_desc = rows[:run_start_idx + 1]
    run_logs = list(reversed(run_rows_desc))
    latest = run_rows_desc[0] if run_rows_desc else rows[0]
    
    # 如果日志太多（超过50条），只返回最近50条，避免前端显示过长
    logs_for_response = run_logs[-50:] if len(run_logs) > 50 else run_logs
    
    return {
        "status": latest.status,
        "message": latest.message,
        "created_at": latest.created_at.isoformat(),
        "logs": [
            {"status": log.status, "message": log.message, "created_at": log.created_at.isoformat()}
            for log in logs_for_response
        ]
    }


@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
