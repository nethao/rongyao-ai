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
    editor: Optional[str] = Query(None, description="采编筛选"),
    cooperation: Optional[str] = Query(None, description="合作方式筛选"),
    media: Optional[str] = Query(None, description="媒体类型筛选"),
    unit: Optional[str] = Query(None, description="来稿单位筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取投稿列表
    支持分页、状态筛选和关键词搜索
    """
    from sqlalchemy.orm import selectinload
    import logging
    logger = logging.getLogger(__name__)

    # 构建公共 where 条件（用于 count 与分页查询）
    base = select(Submission)

    if status:
        base = base.where(Submission.status == status)
    if editor:
        base = base.where(Submission.email_from.like(f"{editor}%"))
    if cooperation:
        base = base.where(Submission.cooperation_type == cooperation)
    if media:
        base = base.where(Submission.media_type == media)
    if unit:
        base = base.where(Submission.source_unit == unit)
    if search:
        search_pattern = f"%{search}%"
        base = base.where(
            or_(
                Submission.email_subject.ilike(search_pattern),
                Submission.email_from.ilike(search_pattern),
                Submission.original_content.ilike(search_pattern),
            )
        )

    # 总数：直接 count(Submission.id)，避免 subquery
    count_stmt = select(func.count(Submission.id)).select_from(Submission)
    if status:
        count_stmt = count_stmt.where(Submission.status == status)
    if editor:
        count_stmt = count_stmt.where(Submission.email_from.like(f"{editor}%"))
    if cooperation:
        count_stmt = count_stmt.where(Submission.cooperation_type == cooperation)
    if media:
        count_stmt = count_stmt.where(Submission.media_type == media)
    if unit:
        count_stmt = count_stmt.where(Submission.source_unit == unit)
    if search:
        search_pattern = f"%{search}%"
        count_stmt = count_stmt.where(
            or_(
                Submission.email_subject.ilike(search_pattern),
                Submission.email_from.ilike(search_pattern),
                Submission.original_content.ilike(search_pattern),
            )
        )
    try:
        total = (await db.execute(count_stmt)).scalar_one()
    except Exception as e:
        logger.exception("list_submissions count failed: %s", e)
        raise HTTPException(status_code=500, detail=f"统计总数失败: {str(e)}")

    # 分页查询（带 images、drafts）
    query = (
        base.order_by(Submission.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .options(
            selectinload(Submission.images),
            selectinload(Submission.drafts),
        )
    )
    try:
        result = await db.execute(query)
        submissions = result.scalars().all()
    except Exception as e:
        logger.exception("list_submissions query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"查询投稿列表失败: {str(e)}")

    try:
        return SubmissionListResponse(
            items=submissions,
            total=total,
            page=page,
            size=size,
        )
    except Exception as e:
        logger.exception("list_submissions serialize failed: %s", e)
        raise HTTPException(status_code=500, detail=f"序列化投稿列表失败: {str(e)}")


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


@router.delete("/{submission_id}")
async def delete_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除投稿（同时删除关联的图片、草稿等）
    """
    query = select(Submission).where(Submission.id == submission_id)
    result = await db.execute(query)
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="投稿不存在")
    await db.delete(submission)
    await db.commit()
    return {"message": "删除成功"}


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
