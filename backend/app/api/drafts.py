"""
草稿管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.draft import Draft, DraftVersion
from app.models.submission import Submission  # 用于 selectinload(Submission.images)
from app.models.media_site_mapping import MediaSiteMapping
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
from app.services.oss_service import OSSService
from app.config import settings

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
        selectinload(Draft.submission).selectinload(Submission.images),
        selectinload(Draft.submission).selectinload(Submission.attachments),
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
    # 若历史数据未写入 target_site_id，则根据 media_type 现查映射补齐
    target_site_id = draft.submission.target_site_id
    if target_site_id is None and draft.submission.media_type:
        mapping_result = await db.execute(
            select(MediaSiteMapping).where(
                MediaSiteMapping.media_type == draft.submission.media_type
            )
        )
        mapping = mapping_result.scalar_one_or_none()
        if mapping and mapping.site_id:
            target_site_id = mapping.site_id
            draft.submission.target_site_id = mapping.site_id
            await db.commit()

    # 组装附件列表（图片 + 其他附件）
    attachments = []
    for img in (draft.submission.images or []):
        attachments.append({
            "id": img.id,
            "type": "image",
            "name": img.original_filename or "图片",
            "url": img.oss_url,
            "size": img.file_size,
            "created_at": getattr(img, "created_at", None)
        })
    for att in (draft.submission.attachments or []):
        attachments.append({
            "id": att.id,
            "type": att.attachment_type,
            "name": att.original_filename or "附件",
            "url": att.oss_url,
            "size": att.file_size,
            "created_at": att.created_at
        })

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
        "target_site_id": target_site_id,  # 添加目标站点ID
        "cooperation_type": draft.submission.cooperation_type,
        "media_type": draft.submission.media_type,
        "source_unit": draft.submission.source_unit,
        "attachments": attachments,
        "attachment_retention_days": settings.ATTACHMENT_RETENTION_DAYS,
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
    import base64
    import time
    import re
    import mimetypes
    from urllib.parse import urlparse
    import requests
    from bs4 import BeautifulSoup
    from app.models.submission import SubmissionImage
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
        def _is_oss_url(url: str) -> bool:
            if not url:
                return False
            if settings.OSS_BUCKET_NAME and settings.OSS_ENDPOINT:
                prefix = f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/"
                if url.startswith(prefix):
                    return True
            return ".aliyuncs.com/" in url

        def _ext_from_content_type(content_type: str) -> str:
            if not content_type:
                return ""
            ct = content_type.split(";")[0].strip().lower()
            mapping = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/gif": ".gif",
                "image/webp": ".webp",
                "image/bmp": ".bmp",
                "image/svg+xml": ".svg",
                "image/tiff": ".tiff",
            }
            return mapping.get(ct, "")

        def _ext_from_url(url: str) -> str:
            try:
                path = urlparse(url).path
                ext = (mimetypes.guess_extension(mimetypes.guess_type(path)[0]) or "")
                if ext:
                    return ext
                _, ext = path.rsplit(".", 1) if "." in path else ("", "")
                return f".{ext}" if ext else ""
            except Exception:
                return ""

        # 1) 处理外链/BASE64图片：下载/解码并上传到OSS，替换为OSS URL
        content_str = draft_update.content if draft_update.content is not None else ""
        if content_str:
            soup = BeautifulSoup(content_str, "html.parser")
            oss_service = OSSService()
            img_index = 0

            for img in soup.find_all("img"):
                src = (img.get("src") or "").strip()
                if not src:
                    continue
                if _is_oss_url(src):
                    continue

                file_data = None
                filename = None
                content_type = None

                # base64 图片
                if src.startswith("data:image/"):
                    m = re.match(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", src)
                    if not m:
                        raise HTTPException(status_code=400, detail="图片Base64格式不正确")
                    content_type = m.group(1)
                    b64_data = m.group(2)
                    try:
                        file_data = base64.b64decode(b64_data)
                    except Exception:
                        raise HTTPException(status_code=400, detail="图片Base64解码失败")
                    ext = _ext_from_content_type(content_type) or ".png"
                    filename = f"inline_{int(time.time() * 1000)}{ext}"
                # 外链图片
                elif src.startswith("http://") or src.startswith("https://"):
                    try:
                        resp = requests.get(
                            src,
                            timeout=30,
                            headers={"User-Agent": "Mozilla/5.0"}
                        )
                        resp.raise_for_status()
                        file_data = resp.content
                        content_type = resp.headers.get("Content-Type", "")
                    except Exception as e:
                        logger.error("下载外链图片失败: %s, err=%s", src, e)
                        raise HTTPException(status_code=400, detail=f"下载外链图片失败: {src}")

                    ext = _ext_from_content_type(content_type) or _ext_from_url(src) or ".jpg"
                    img_index += 1
                    filename = f"external_{int(time.time() * 1000)}_{img_index}{ext}"
                else:
                    # blob: 或其他未知协议，无法在后端下载
                    raise HTTPException(status_code=400, detail=f"不支持的图片来源: {src}")

                # 上传到OSS
                oss_url, oss_key = oss_service.upload_file(
                    file_data=file_data,
                    filename=filename,
                    folder=f"drafts/{draft.id}"
                )

                # 记录到投稿图片表，便于清理与统计
                image = SubmissionImage(
                    submission_id=draft.submission_id,
                    oss_url=oss_url,
                    oss_key=oss_key,
                    original_filename=filename,
                    file_size=len(file_data) if file_data else None
                )
                db.add(image)

                # 替换src为OSS URL
                img["src"] = oss_url

            content_str = str(soup)

        # === 占位符协议 Dehydration ===
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
        system_username=current_user.username,
        publisher_user_id=current_user.id,
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


@router.post("/{draft_id}/upload-word")
async def upload_word_for_draft(
    draft_id: int,
    word_file: UploadFile = File(..., description="Word文档文件"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传Word文档并转换为可编辑HTML（保持图文顺序）
    """
    import tempfile
    import os
    import logging
    from app.services.document_processor import DocumentProcessor
    from app.utils.content_processor import ContentProcessor
    from app.models.draft import Draft
    from app.models.submission import SubmissionImage
    from app.models.submission_attachment import SubmissionAttachment

    logger = logging.getLogger(__name__)

    result = await db.execute(select(Draft).where(Draft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="草稿不存在")

    suffix = os.path.splitext(word_file.filename or "")[1].lower()
    if suffix not in (".doc", ".docx"):
        raise HTTPException(status_code=400, detail="仅允许上传 .doc 或 .docx 文件")

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file_path = temp_file.name
    try:
        content_bytes = await word_file.read()
        temp_file.write(content_bytes)
        temp_file.close()

        doc_processor = DocumentProcessor()
        # 上传原始Word文件到OSS并记录附件
        try:
            word_url, word_key = oss_service.upload_file(
                file_data=content_bytes,
                filename=word_file.filename or f"word_upload{suffix}",
                folder='attachments'
            )
            word_attachment = SubmissionAttachment(
                submission_id=draft.submission_id,
                attachment_type="word",
                oss_url=word_url,
                oss_key=word_key,
                original_filename=word_file.filename,
                file_size=len(content_bytes) if content_bytes else None
            )
            db.add(word_attachment)
            await db.commit()
        except Exception as e:
            logger.error("Word原文件上传失败: %s", e)
        docx_path = None
        title = "无标题"
        content_md = ""

        if suffix == ".doc":
            docx_path = doc_processor.convert_doc_to_docx(temp_file_path)
            title, title_lines = doc_processor.extract_title_from_docx(docx_path)
            content_md = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)
            images = doc_processor.extract_images_from_docx(docx_path)
        else:
            title, title_lines = doc_processor.extract_title_from_docx(temp_file_path)
            content_md = doc_processor.extract_text_from_docx(temp_file_path, skip_title_lines=title_lines)
            images = doc_processor.extract_images_from_docx(temp_file_path)

        # 上传图片到OSS并构建media_map
        media_map = {}
        oss_service = OSSService()
        for idx, (img_filename, img_data) in enumerate(images, start=1):
            try:
                oss_url, oss_key = oss_service.upload_file(
                    file_data=img_data,
                    filename=img_filename,
                    folder=f"drafts/{draft.id}"
                )
                placeholder = f"[[IMG_{idx}]]"
                media_map[placeholder] = oss_url

                image = SubmissionImage(
                    submission_id=draft.submission_id,
                    oss_url=oss_url,
                    oss_key=oss_key,
                    original_filename=img_filename,
                    file_size=len(img_data) if img_data else None
                )
                db.add(image)
            except Exception as e:
                logger.error("Word图片上传失败 %s: %s", img_filename, e)

        await db.commit()

        # 将占位符替换为实际图片，得到可编辑HTML
        content_html = ContentProcessor.render_for_wordpress(content_md, media_map)

        return {
            "title": title or "无标题",
            "content_md": content_md,
            "content_html": content_html,
            "image_count": len(media_map),
            "media_map": media_map
        }
    finally:
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        except Exception:
            pass
        try:
            if docx_path and os.path.exists(docx_path) and docx_path != temp_file_path:
                os.unlink(docx_path)
        except Exception:
            pass
