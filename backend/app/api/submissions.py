"""
投稿管理API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
import tempfile
import os
import logging

from app.database import get_db
from app.models.user import User
from app.models.submission import Submission
from app.models.task_log import TaskLog
from app.schemas.submission import SubmissionSchema, SubmissionListResponse, ManualSubmissionCreate, ContentPreviewResponse, ManualSubmissionCreateFromPreview
from app.api.dependencies import get_current_user
from app.tasks.transform_tasks import transform_content_task
from sqlalchemy import desc

router = APIRouter(prefix="/submissions", tags=["submissions"])
logger = logging.getLogger(__name__)


@router.post("/preview", response_model=ContentPreviewResponse)
async def preview_content(
    article_type: str = Form(..., description="文章类型: weixin, meipian, word"),
    article_url: Optional[str] = Form(None, description="文章链接（公众号/美篇）"),
    word_file: Optional[UploadFile] = File(None, description="Word文档文件"),
    current_user: User = Depends(get_current_user)
):
    """
    预览/解析内容（在预览阶段上传图片到OSS）
    用于手动发布的第一步：用户输入链接或上传文件后，先解析内容并上传图片
    """
    from app.services.web_fetcher import WebFetcher
    from app.services.document_processor import DocumentProcessor
    from app.services.oss_service import OSSService
    from app.utils.content_processor import ContentProcessor
    from bs4 import BeautifulSoup
    
    try:
        title = ""
        content = ""
        original_html = None
        content_source = ""
        image_count = 0
        media_map = {}
        
        oss_service = OSSService()
        
        if article_type == "weixin":
            # 抓取公众号文章
            if not article_url:
                raise HTTPException(status_code=400, detail="公众号类型需要提供文章链接")
            
            fetcher = WebFetcher()
            fetched_title, fetched_content, fetched_html, image_urls = fetcher.fetch_weixin_article(article_url)
            
            if not fetched_content:
                raise HTTPException(status_code=400, detail="无法从链接获取文章内容，请检查链接是否正确")
            
            title = fetched_title or "无标题"
            original_html = fetched_html
            content_source = "weixin"
            
            # 下载并上传图片，构建media_map
            for idx, img_url in enumerate(image_urls):
                try:
                    img_data = fetcher.download_image(img_url)
                    if img_data:
                        oss_url, oss_key = oss_service.upload_file(
                            file_data=img_data,
                            filename=f"preview_weixin_{idx}.jpg",
                            folder='images'
                        )
                        placeholder = f"[[IMG_{idx}]]"
                        media_map[placeholder] = oss_url
                        logger.info(f"预览上传图片 {idx}: {oss_url}")
                except Exception as e:
                    logger.error(f"预览上传图片失败 {idx}: {e}")
            
            # 将Markdown图片语法替换为占位符
            import re
            content = fetched_content
            for idx in range(len(image_urls)):
                # 匹配 ![图片N](url) 格式
                pattern = rf'!\[图片{idx+1}\]\([^)]+\)'
                replacement = f'[[IMG_{idx}]]'
                content = re.sub(pattern, replacement, content)
            
            image_count = len(media_map)
        
        elif article_type == "meipian":
            # 抓取美篇文章
            if not article_url:
                raise HTTPException(status_code=400, detail="美篇类型需要提供文章链接")
            
            fetcher = WebFetcher()
            fetched_title, fetched_content, image_urls, fetched_html = await fetcher.fetch_meipian_article_async(article_url)
            
            if not fetched_content:
                raise HTTPException(status_code=400, detail="无法从链接获取文章内容，请检查链接是否正确")
            
            title = fetched_title or "无标题"
            original_html = fetched_html
            content_source = "meipian"
            
            # 下载并上传图片，构建media_map
            for idx, img_url in enumerate(image_urls):
                try:
                    img_data = fetcher.download_image(img_url)
                    if img_data:
                        oss_url, oss_key = oss_service.upload_file(
                            file_data=img_data,
                            filename=f"preview_meipian_{idx}.jpg",
                            folder='images'
                        )
                        placeholder = f"[[IMG_{idx}]]"
                        media_map[placeholder] = oss_url
                        logger.info(f"预览上传图片 {idx}: {oss_url}")
                except Exception as e:
                    logger.error(f"预览上传图片失败 {idx}: {e}")
            
            # 美篇返回纯文本，需要从HTML中提取图片位置并插入占位符
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(fetched_html, 'html.parser')
            
            # 在HTML中将图片替换为占位符
            img_tags = soup.find_all('img')
            img_idx = 0
            for img in img_tags:
                # 跳过图标等小图
                img_url = img.get('data-src') or img.get('src')
                if img_url and img_url in image_urls:
                    # 用占位符替换img标签
                    placeholder_text = f"\n\n[[IMG_{img_idx}]]\n\n"
                    img.replace_with(placeholder_text)
                    img_idx += 1
            
            # 提取带占位符的文本
            content = soup.get_text(separator='\n', strip=True)
            
            image_count = len(media_map)
        
        elif article_type == "word":
            # 处理Word文档
            if not word_file:
                raise HTTPException(status_code=400, detail="Word类型需要上传文件")
            
            # 保存上传的文件到临时目录
            suffix = os.path.splitext(word_file.filename)[1]
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            try:
                content_bytes = await word_file.read()
                temp_file.write(content_bytes)
                temp_file.close()
                
                doc_processor = DocumentProcessor()
                
                if suffix.lower() == '.doc':
                    # 转换为docx
                    docx_path = doc_processor.convert_doc_to_docx(temp_file.name)
                    # 提取标题
                    doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                    title = doc_title if doc_title and doc_title != "无标题" else "无标题"
                    # 提取内容
                    content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)
                    # 提取图片
                    images = doc_processor.extract_images_from_docx(docx_path)
                    # 清理临时文件
                    if os.path.exists(docx_path) and docx_path != temp_file.name:
                        os.unlink(docx_path)
                elif suffix.lower() == '.docx':
                    # 提取标题
                    doc_title, title_lines = doc_processor.extract_title_from_docx(temp_file.name)
                    title = doc_title if doc_title and doc_title != "无标题" else "无标题"
                    # 提取内容
                    content = doc_processor.extract_text_from_docx(temp_file.name, skip_title_lines=title_lines)
                    # 提取图片
                    images = doc_processor.extract_images_from_docx(temp_file.name)
                
                # 上传图片
                for idx, (img_filename, img_data) in enumerate(images):
                    try:
                        oss_url, oss_key = oss_service.upload_file(
                            file_data=img_data,
                            filename=img_filename,
                            folder='images'
                        )
                        placeholder = f"[[IMG_{idx}]]"
                        media_map[placeholder] = oss_url
                        logger.info(f"预览上传Word图片 {idx}: {oss_url}")
                    except Exception as e:
                        logger.error(f"预览上传Word图片失败 {idx}: {e}")
                
                content_source = "docx" if suffix.lower() == '.docx' else "doc"
                image_count = len(media_map)
            finally:
                # 清理临时文件
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文章类型: {article_type}")
        
        if not content or not content.strip():
            raise HTTPException(status_code=400, detail="未能提取到有效内容")
        
        # 生成预览HTML（将占位符替换为实际图片）
        preview_html = ContentProcessor.render_for_wordpress(content, media_map)
        
        logger.info(f"预览完成 - Title: {title}, Image Count: {image_count}, Media Map: {media_map}")
        
        return ContentPreviewResponse(
            title=title,
            content=content,
            preview_html=preview_html,
            original_html=original_html,
            content_source=content_source,
            image_count=image_count,
            media_map=media_map
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览内容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预览内容失败: {str(e)}")


@router.post("/", response_model=SubmissionSchema, status_code=201)
async def create_submission(
    body: ManualSubmissionCreateFromPreview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    手动创建投稿（编辑人员可创建）
    接收已解析的内容数据（图片已在预览阶段上传），创建投稿和草稿
    """
    from app.services.submission_service import SubmissionService
    from app.models.draft import Draft
    from datetime import datetime
    from sqlalchemy.orm import selectinload
    
    submission_service = SubmissionService(db)
    
    try:
        logger.info(f"=== 创建投稿 ===")
        logger.info(f"Title: {body.title}")
        logger.info(f"Source: {body.content_source}")
        logger.info(f"Media Map Type: {type(body.media_map)}")
        logger.info(f"Media Map: {body.media_map}")
        logger.info(f"Content (first 200 chars): {body.content[:200] if body.content else None}")
        
        # 创建投稿
        submission = await submission_service.create_submission(
            email_subject=body.title,
            email_from=body.email_from or current_user.username,
            email_date=datetime.utcnow(),
            original_content=body.content
        )
        
        # 设置元数据
        submission.cooperation_type = body.cooperation_type
        submission.media_type = body.media_type
        submission.source_unit = body.source_unit
        submission.content_source = body.content_source
        if body.original_html:
            submission.original_html = body.original_html
        
        # 先提交以获取 submission.id
        await db.commit()
        await db.refresh(submission)
        
        # 使用预览阶段已上传的图片（media_map）
        media_map = body.media_map or {}
        
        # 创建草稿
        draft = Draft(
            submission_id=submission.id,
            current_content=body.content,
            ai_content_md=body.content,
            media_map=media_map,
            status='draft',
            current_version=1
        )
        
        db.add(draft)
        await db.commit()
        
        # 重新加载 submission 以包含 drafts
        result = await db.execute(
            select(Submission)
            .options(selectinload(Submission.images), selectinload(Submission.drafts))
            .where(Submission.id == submission.id)
        )
        submission = result.scalar_one()
        
        return submission
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建投稿失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建投稿失败: {str(e)}")


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


@router.get("/{submission_id}/transform-status")
async def get_transform_status(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询该投稿的 AI 改写任务最新状态（用于前端轮询，判断任务是否完成或失败）
    """
    query = (
        select(TaskLog)
        .where(
            TaskLog.task_type == "ai_transform",
            TaskLog.task_id == str(submission_id)
        )
        .order_by(desc(TaskLog.created_at))
        .limit(1)
    )
    result = await db.execute(query)
    log = result.scalar_one_or_none()
    if not log:
        return {"status": "idle", "message": None, "created_at": None}
    return {
        "status": log.status,
        "message": log.message,
        "created_at": log.created_at.isoformat() if log.created_at else None
    }
