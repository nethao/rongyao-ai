"""
草稿管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.draft import Draft, DraftVersion
from app.models.submission import Submission
from app.schemas.draft import (
    DraftSchema,
    DraftDetailSchema,
    DraftUpdate,
    DraftVersionListResponse,
    RestoreVersionRequest
)
from app.schemas.wordpress import PublishRequest, PublishResult
from app.api.dependencies import get_current_user
from app.services.draft_service import DraftService
from app.services.publish_service import PublishService

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get("/{draft_id}", response_model=DraftDetailSchema)
async def get_draft(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取草稿详情（使用占位符协议 - Hydration）
    """
    from app.utils.content_processor import ContentProcessor
    
    # 查询草稿及关联的投稿
    query = select(Draft).where(Draft.id == draft_id).options(
        selectinload(Draft.submission)
    )
    result = await db.execute(query)
    draft = result.scalar_one_or_none()
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    # === 占位符协议 Hydration ===
    # 如果有新字段，使用占位符协议
    if draft.ai_content_md and draft.media_map:
        # 直接返回AI原始Markdown内容（不做hydrate转换）
        current_content = draft.ai_content_md
    else:
        # 兼容旧数据
        current_content = draft.current_content
    
    # 构建响应
    draft_dict = {
        "id": draft.id,
        "submission_id": draft.submission_id,
        "current_content": current_content,  # 返回hydrated HTML
        "current_version": draft.current_version,
        "status": draft.status,
        "published_at": draft.published_at,
        "published_to_site_id": draft.published_to_site_id,
        "wordpress_post_id": draft.wordpress_post_id,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "original_content": draft.submission.original_content,
        "original_html": draft.submission.original_html,
        "email_subject": draft.submission.email_subject,
        "content_source": draft.submission.content_source
    }
    
    return draft_dict


@router.put("/{draft_id}", response_model=DraftSchema)
async def update_draft(
    draft_id: int,
    draft_update: DraftUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新草稿内容（使用占位符协议 - Dehydration）
    """
    from app.utils.content_processor import ContentProcessor
    
    # 获取当前草稿
    result = await db.execute(
        select(Draft).where(Draft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    # === 占位符协议 Dehydration ===
    # Dehydrate: HTML → Markdown + 占位符
    new_md, new_media_map = ContentProcessor.dehydrate(
        draft_update.content,
        draft.media_map or {}
    )
    
    # 更新草稿
    draft.ai_content_md = new_md
    draft.media_map = new_media_map
    draft.current_content = draft_update.content  # 保留旧字段兼容
    draft.current_version += 1
    
    # 创建版本记录
    version = DraftVersion(
        draft_id=draft.id,
        version_number=draft.current_version,
        content=draft_update.content,  # 旧字段
        content_md=new_md,  # 新字段
        media_map=new_media_map,  # 新字段
        created_by=current_user.id
    )
    
    db.add(version)
    await db.commit()
    await db.refresh(draft)
    
    return draft


@router.get("/{draft_id}/versions", response_model=DraftVersionListResponse)
async def get_draft_versions(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取草稿版本历史
    """
    # 检查草稿是否存在
    query = select(Draft).where(Draft.id == draft_id)
    result = await db.execute(query)
    draft = result.scalar_one_or_none()
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    # 查询版本历史
    versions_query = select(DraftVersion).where(
        DraftVersion.draft_id == draft_id
    ).order_by(DraftVersion.version_number.desc())
    
    result = await db.execute(versions_query)
    versions = result.scalars().all()
    
    return DraftVersionListResponse(versions=versions)


@router.post("/{draft_id}/restore", response_model=DraftSchema)
async def restore_version(
    draft_id: int,
    restore_request: RestoreVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    恢复到指定版本
    """
    draft_service = DraftService(db)
    
    try:
        restored_draft = await draft_service.restore_version(
            draft_id=draft_id,
            version_id=restore_request.version_id,
            created_by=current_user.id
        )
        return restored_draft
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{draft_id}/restore-ai", response_model=DraftSchema)
async def restore_ai_version(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    恢复到AI转换的原始版本（版本1）
    """
    draft_service = DraftService(db)
    
    try:
        # 查询版本1
        version_query = select(DraftVersion).where(
            DraftVersion.draft_id == draft_id,
            DraftVersion.version_number == 1
        )
        result = await db.execute(version_query)
        version_1 = result.scalar_one_or_none()
        
        if not version_1:
            raise HTTPException(status_code=404, detail="AI原始版本不存在")
        
        restored_draft = await draft_service.restore_version(
            draft_id=draft_id,
            version_id=version_1.id,
            user_id=current_user.id
        )
        return restored_draft
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{draft_id}/publish", response_model=PublishResult)
async def publish_draft(
    draft_id: int,
    publish_request: PublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    发布草稿到WordPress站点
    """
    publish_service = PublishService(db)
    
    success, post_id, error_msg, site_name = await publish_service.publish_draft(
        draft_id=draft_id,
        site_id=publish_request.site_id,
        status="publish"
    )
    
    if success:
        return PublishResult(
            success=True,
            wordpress_post_id=post_id,
            message=f"成功发布到 {site_name}",
            site_name=site_name
        )
    else:
        return PublishResult(
            success=False,
            message=error_msg,
            site_name=site_name
        )


@router.get("/{draft_id}/publish-history")
async def get_publish_history(
    draft_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取草稿的发布历史
    """
    publish_service = PublishService(db)
    history = await publish_service.get_publish_history(draft_id)
    return history
