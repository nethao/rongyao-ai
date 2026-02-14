"""
投稿管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.submission import Submission
from app.schemas.submission import SubmissionSchema, SubmissionListResponse
from app.api.dependencies import get_current_user
from app.tasks.transform_tasks import transform_content_task

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("/", response_model=SubmissionListResponse)
async def list_submissions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取投稿列表
    支持分页、状态筛选和关键词搜索
    """
    from sqlalchemy.orm import selectinload
    from app.models.draft import Draft
    
    # 构建查询
    query = select(Submission).options(
        selectinload(Submission.images),
        selectinload(Submission.drafts)
    )
    
    # 状态筛选
    if status:
        query = query.where(Submission.status == status)
    
    # 关键词搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Submission.email_subject.ilike(search_pattern),
                Submission.email_from.ilike(search_pattern),
                Submission.original_content.ilike(search_pattern)
            )
        )
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar_one()
    
    # 分页查询
    query = query.order_by(Submission.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    submissions = result.scalars().all()
    
    return SubmissionListResponse(
        items=submissions,
        total=total,
        page=page,
        size=size
    )


@router.get("/{submission_id}", response_model=SubmissionSchema)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取投稿详情
    """
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="投稿不存在")
    
    return submission


@router.post("/{submission_id}/transform")
async def trigger_transform(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    触发AI转换任务
    """
    # 检查投稿是否存在
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="投稿不存在")
    
    # 触发异步任务
    task = transform_content_task.delay(submission_id)
    
    return {
        "message": "AI转换任务已启动",
        "task_id": task.id,
        "submission_id": submission_id
    }
