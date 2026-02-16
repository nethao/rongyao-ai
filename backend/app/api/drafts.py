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
from app.models.submission import Submission  # 用于 selectinload(Submission.images)
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
    
    # 查询草稿及关联的投稿（含投稿图片，用于 media_map 丢失时按序恢复）
    query = select(Draft).where(Draft.id == draft_id).options(
        selectinload(Draft.submission).selectinload(Submission.images)
    )
    result = await db.execute(query)
    draft = result.scalar_one_or_none()
    
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")
    
    # 占位符映射：优先用草稿自己的；若为空但内容里有 [[IMG_N]] 且投稿有图片，则按投稿图片顺序恢复
    media_map = draft.media_map if draft.media_map else {}
    content_for_placeholders = (draft.ai_content_md or "") or (draft.current_content or "")
    if not media_map and content_for_placeholders and "[[IMG_" in content_for_placeholders and draft.submission.images:
        ordered_images = sorted(draft.submission.images, key=lambda x: x.id)
        for i, img in enumerate(ordered_images, start=1):
            placeholder = f"[[IMG_{i}]]"
            if placeholder in content_for_placeholders:
                media_map[placeholder] = img.oss_url
    
    # === Hydration：把 [[IMG_N]] 转为 <img>，前端直接展示 ===
    content_to_hydrate = draft.ai_content_md or draft.current_content or ""
    
    # 视频类型直接使用HTML内容，不需要hydrate
    if draft.submission.content_source == 'video':
        current_content = content_to_hydrate
    elif content_to_hydrate and media_map:
        current_content = ContentProcessor.hydrate(content_to_hydrate, media_map)
    elif draft.ai_content_md:
        current_content = ContentProcessor.hydrate(draft.ai_content_md, {})
    else:
        current_content = draft.current_content
    
    # 处理原始内容：如果是Word文档且有占位符，也需要hydrate
    original_content_display = draft.submission.original_content
    if draft.submission.content_source in ['doc', 'docx'] and media_map:
        # Word文档：将原始内容中的占位符替换为图片
        original_content_display = ContentProcessor.hydrate(
            draft.submission.original_content,
            media_map
        )
    
    # 构建响应（避免 None 导致 Pydantic 校验失败）
    draft_dict = {
        "id": draft.id,
        "submission_id": draft.submission_id,
        "current_content": current_content or "",
        "media_map": media_map,
        "current_version": draft.current_version if draft.current_version is not None else 1,
        "status": draft.status or "draft",
        "published_at": draft.published_at,
        "published_to_site_id": draft.published_to_site_id,
        "wordpress_post_id": draft.wordpress_post_id,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "original_content": original_content_display if original_content_display is not None else "",
        "original_html": draft.submission.original_html,
        "email_subject": draft.submission.email_subject,
        "content_source": draft.submission.content_source,
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
    import logging
    from app.utils.content_processor import ContentProcessor

    logger = logging.getLogger(__name__)

    # 获取当前草稿
    result = await db.execute(
        select(Draft).where(Draft.id == draft_id)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    try:
        # === 占位符协议 Dehydration ===
        content_str = draft_update.content if draft_update.content is not None else ""
        new_md, new_media_map = ContentProcessor.dehydrate(
            content_str,
            draft.media_map or {}
        )
        # 若保存内容里仍有占位符文本但无 <img>（如编辑器未显示图时），保留旧 media_map 中对应项，避免丢失
        old_map = draft.media_map or {}
        for placeholder, url in old_map.items():
            if placeholder in new_md and placeholder not in new_media_map:
                new_media_map[placeholder] = url

        # 更新草稿（兼容 current_version 为 NULL 的旧数据）
        draft.ai_content_md = new_md
        draft.media_map = new_media_map
        draft.current_content = content_str
        draft.current_version = (draft.current_version or 0) + 1
        if draft.status is None:
            draft.status = "draft"

        # 创建版本记录
        version = DraftVersion(
            draft_id=draft.id,
            version_number=draft.current_version,
            content=content_str,
            content_md=new_md,
            media_map=new_media_map,
            created_by=current_user.id
        )

        db.add(version)
        await db.commit()
        await db.refresh(draft)

        return draft
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_draft failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"保存失败: {type(e).__name__}: {str(e)}"
        )


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
        status="publish",
        author_id=current_user.wp_author_id  # 使用当前用户的WP作者ID
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
