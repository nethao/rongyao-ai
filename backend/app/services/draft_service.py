"""
草稿管理服务
"""
import logging
import re
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.draft import Draft, DraftVersion
from app.models.submission import Submission


logger = logging.getLogger(__name__)


class DraftService:
    """草稿管理服务"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化草稿服务
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def format_content_for_wordpress(self, content: str) -> str:
        """
        格式化内容以适配WordPress发布
        - 识别Markdown标题并转换为HTML标签（## -> <h2>, ### -> <h3>）
        - 识别中文标题格式（一、二、三、或（一）（二））
        - 为普通段落添加<p>标签和首行缩进
        - 保留图片标记
        
        Args:
            content: 原始内容（Markdown或纯文本格式）
        
        Returns:
            格式化后的HTML内容
        """
        # 如果内容已经包含HTML标签，清理图片的<p>包裹后直接返回
        if '<p' in content or '<h2' in content or '<h3' in content:
            logger.info("内容已包含HTML标签，清理图片<p>标签后返回")
            # 移除图片周围的<p>标签
            content = re.sub(r'<p[^>]*>\s*(!\[图片\d+\][^\n]+)\s*</p>', r'\1', content)
            # 清理连续空行
            content = re.sub(r'\n{2,}', '\n', content)
            return content
        
        # 清理多余空行（3个以上连续换行 -> 2个）
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 预处理：标记图片行，避免被包裹<p>标签
        content = re.sub(r'(!\[图片\d+\]\([^\)]+\))', r'__IMG_START__\1__IMG_END__', content)
        
        lines = content.split('\n')
        formatted_lines = []
        
        # 中文标题模式
        h2_pattern = re.compile(r'^[一二三四五六七八九十]+、.+')  # 一、二、三、
        h3_pattern = re.compile(r'^（[一二三四五六七八九十]+）.+')  # （一）（二）
        h3_pattern2 = re.compile(r'^\d+\..+')  # 1. 2. 3.
        
        for line in lines:
            line = line.strip()
            
            # 空行：跳过
            if not line:
                continue
            
            # 图片标记：恢复并保持原样
            if '__IMG_START__' in line:
                img_line = re.sub(r'__IMG_START__|__IMG_END__', '', line)
                formatted_lines.append(img_line)
            # Markdown标题：转换为HTML
            elif line.startswith('####'):
                title = line.replace('####', '').strip()
                formatted_lines.append(f'<h4>{title}</h4>')
            elif line.startswith('###'):
                title = line.replace('###', '').strip()
                formatted_lines.append(f'<h3>{title}</h3>')
            elif line.startswith('##'):
                title = line.replace('##', '').strip()
                formatted_lines.append(f'<h2>{title}</h2>')
            elif line.startswith('#'):
                title = line.replace('#', '').strip()
                formatted_lines.append(f'<h2>{title}</h2>')
            # 中文标题：一、二、三、
            elif h2_pattern.match(line):
                formatted_lines.append(f'<h2>{line}</h2>')
            # 中文标题：（一）（二）或 1. 2.
            elif h3_pattern.match(line) or h3_pattern2.match(line):
                formatted_lines.append(f'<h3>{line}</h3>')
            # 普通段落：添加<p>标签和首行缩进
            else:
                formatted_lines.append(f'<p style="text-indent: 2em;">{line}</p>')
        
        result = '\n'.join(formatted_lines)
        
        # 清理连续空行（保留单个换行用于分隔）
        result = re.sub(r'\n{2,}', '\n', result)
        
        # 后处理：移除图片周围的<p>标签
        result = re.sub(r'<p[^>]*>\s*(!\[图片\d+\][^\n]+)\s*</p>', r'\1', result)
        
        return result
    
    async def create_draft(
        self,
        submission_id: int,
        transformed_content: str = None,
        created_by: Optional[int] = None,
        original_content_md: str = None,
        ai_content_md: str = None,
        media_map: dict = None
    ) -> Draft:
        """
        创建草稿（使用占位符协议）
        
        Args:
            submission_id: 投稿ID
            transformed_content: AI转换后的内容（Markdown格式，旧方式）
            created_by: 创建者用户ID（可选）
            original_content_md: 原始Markdown（带占位符，新方式）
            ai_content_md: AI转换后的Markdown（带占位符，新方式）
            media_map: 占位符映射（新方式）
        
        Returns:
            创建的草稿对象
        
        Raises:
            ValueError: 如果投稿不存在或内容为空
        """
        from app.utils.content_processor import ContentProcessor
        from sqlalchemy.orm import selectinload
        
        # 验证投稿是否存在并加载图片
        result = await self.db.execute(
            select(Submission)
            .options(selectinload(Submission.images))
            .where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        
        if not submission:
            error_msg = f"投稿不存在: submission_id={submission_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 检查是否已存在草稿
        existing_draft = await self.get_draft_by_submission(submission_id)
        if existing_draft:
            logger.warning(
                f"投稿已存在草稿: submission_id={submission_id}, "
                f"draft_id={existing_draft.id}"
            )
            # 如果已存在草稿，更新内容而不是创建新草稿
            return await self.update_draft(
                existing_draft.id,
                transformed_content=transformed_content,
                created_by=created_by,
                ai_content_md=ai_content_md,
                media_map=media_map
            )
        
        # === 占位符协议处理 ===
        # 如果直接传入了占位符数据（新方式），直接使用
        if original_content_md and ai_content_md and media_map is not None:
            content_md = ai_content_md
            final_media_map = media_map
            formatted_content = ai_content_md  # 直接存储Markdown
        else:
            # 否则从transformed_content提取（旧方式，向后兼容）
            if not transformed_content or not transformed_content.strip():
                error_msg = "转换后的内容不能为空"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 1. 从投稿图片生成media_map
            images_data = [
                {"oss_url": img.oss_url, "original_filename": img.original_filename}
                for img in submission.images
            ]
            
            # 2. 提取图片并生成占位符
            content_md, final_media_map = ContentProcessor.extract_images_from_content(
                transformed_content, 
                images_data
            )
            original_content_md = content_md
            formatted_content = self.format_content_for_wordpress(transformed_content)
        
        # 创建草稿记录
        draft = Draft(
            submission_id=submission_id,
            original_content_md=original_content_md,  # 新字段：带占位符的Markdown
            ai_content_md=content_md,  # AI转换后的Markdown
            media_map=final_media_map,  # 新字段：占位符映射
            current_content=formatted_content,  # 旧字段：保留兼容
            current_version=1,
            status='draft'
        )
        
        self.db.add(draft)
        await self.db.flush()  # 获取draft.id
        
        # 创建第一个版本记录
        version = DraftVersion(
            draft_id=draft.id,
            version_number=1,
            content=formatted_content,  # 旧字段
            content_md=content_md,  # 新字段：Markdown
            media_map=final_media_map,  # 新字段：映射
            created_by=created_by
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(draft)
        
        logger.info(
            f"草稿创建成功（占位符协议）: draft_id={draft.id}, "
            f"submission_id={submission_id}, placeholders={len(final_media_map)}"
        )
        
        return draft
    
    async def update_draft(
        self,
        draft_id: int,
        content: str = None,
        created_by: Optional[int] = None,
        transformed_content: str = None,
        ai_content_md: str = None,
        media_map: dict = None
    ) -> Draft:
        """
        更新草稿内容（创建新版本）
        
        Args:
            draft_id: 草稿ID
            content: 新的内容（旧方式）
            created_by: 创建者用户ID（可选）
            transformed_content: AI转换后的内容（旧方式）
            ai_content_md: AI转换后的Markdown（带占位符，新方式）
            media_map: 占位符映射（新方式）
        
        Returns:
            更新后的草稿对象
        
        Raises:
            ValueError: 如果草稿不存在或内容为空
        """
        # 获取草稿
        draft = await self.get_draft(draft_id)
        if not draft:
            error_msg = f"草稿不存在: draft_id={draft_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 使用新方式或旧方式
        if ai_content_md and media_map is not None:
            # 新方式：直接存储Markdown，不做格式化
            content_md = ai_content_md
            final_media_map = media_map
            formatted_content = ai_content_md  # 直接存储Markdown
        else:
            # 旧方式：使用content或transformed_content
            actual_content = content or transformed_content
            if not actual_content or not actual_content.strip():
                error_msg = "内容不能为空"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # 检查内容是否有变化
            if actual_content.strip() == draft.current_content.strip():
                logger.info(f"内容未变化，不创建新版本: draft_id={draft_id}")
                return draft
            
            content_md = actual_content
            final_media_map = draft.media_map or {}
            formatted_content = actual_content
        
        # 更新草稿当前内容和版本号
        new_version_number = draft.current_version + 1
        draft.ai_content_md = content_md
        draft.media_map = final_media_map
        draft.current_content = formatted_content
        draft.current_version = new_version_number
        draft.updated_at = datetime.utcnow()
        
        # 创建新版本记录
        version = DraftVersion(
            draft_id=draft_id,
            version_number=new_version_number,
            content=formatted_content,
            content_md=content_md,
            media_map=final_media_map,
            created_by=created_by
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(draft)
        
        logger.info(
            f"草稿更新成功: draft_id={draft_id}, new_version={new_version_number}, "
            f"content_length={len(content_md)}"
        )
        
        # 清理旧版本（保留最近30个）
        await self._cleanup_old_versions(draft_id)
        
        return draft
    
    async def get_draft(self, draft_id: int) -> Optional[Draft]:
        """
        获取草稿详情
        
        Args:
            draft_id: 草稿ID
        
        Returns:
            草稿对象，如果不存在则返回None
        """
        result = await self.db.execute(
            select(Draft)
            .options(
                selectinload(Draft.submission),
                selectinload(Draft.published_site)
            )
            .where(Draft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        
        if draft:
            logger.debug(f"获取草稿成功: draft_id={draft_id}")
        else:
            logger.warning(f"草稿不存在: draft_id={draft_id}")
        
        return draft
    
    async def get_draft_by_submission(self, submission_id: int) -> Optional[Draft]:
        """
        根据投稿ID获取草稿
        
        Args:
            submission_id: 投稿ID
        
        Returns:
            草稿对象，如果不存在则返回None
        """
        result = await self.db.execute(
            select(Draft)
            .where(Draft.submission_id == submission_id)
            .order_by(desc(Draft.created_at))
        )
        draft = result.scalar_one_or_none()
        
        if draft:
            logger.debug(f"根据投稿ID获取草稿成功: submission_id={submission_id}, draft_id={draft.id}")
        else:
            logger.debug(f"投稿没有关联的草稿: submission_id={submission_id}")
        
        return draft
    
    async def get_versions(self, draft_id: int) -> List[DraftVersion]:
        """
        获取草稿版本历史
        
        Args:
            draft_id: 草稿ID
        
        Returns:
            版本列表，按版本号降序排列
        """
        result = await self.db.execute(
            select(DraftVersion)
            .where(DraftVersion.draft_id == draft_id)
            .order_by(desc(DraftVersion.version_number))
        )
        versions = result.scalars().all()
        
        logger.debug(f"获取草稿版本历史: draft_id={draft_id}, count={len(versions)}")
        
        return list(versions)
    
    async def restore_version(
        self,
        draft_id: int,
        version_id: int,
        created_by: Optional[int] = None
    ) -> Draft:
        """
        恢复到指定版本
        
        Args:
            draft_id: 草稿ID
            version_id: 版本ID
            created_by: 操作者用户ID（可选）
        
        Returns:
            更新后的草稿对象
        
        Raises:
            ValueError: 如果草稿或版本不存在
        """
        # 获取版本
        result = await self.db.execute(
            select(DraftVersion).where(DraftVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        
        if not version:
            error_msg = f"版本不存在: version_id={version_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if version.draft_id != draft_id:
            error_msg = f"版本不属于该草稿: draft_id={draft_id}, version.draft_id={version.draft_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 优先使用 content_md + media_map（占位符协议），否则回退到 content（旧版 HTML）
        if version.content_md:
            media = version.media_map if version.media_map is not None else None
            if media is None:
                current = await self.get_draft(draft_id)
                media = (current.media_map if current else None) or {}
            draft = await self.update_draft(
                draft_id=draft_id,
                ai_content_md=version.content_md,
                media_map=media,
                created_by=created_by
            )
        else:
            draft = await self.update_draft(
                draft_id=draft_id,
                content=version.content,
                created_by=created_by
            )
        
        logger.info(
            f"恢复版本成功: draft_id={draft_id}, version_id={version_id}, "
            f"version_number={version.version_number}"
        )
        
        return draft
    
    async def restore_ai_version(
        self,
        draft_id: int,
        created_by: Optional[int] = None
    ) -> Draft:
        """
        恢复到AI转换的原始版本（版本1）
        
        Args:
            draft_id: 草稿ID
            created_by: 操作者用户ID（可选）
        
        Returns:
            更新后的草稿对象
        
        Raises:
            ValueError: 如果草稿或版本1不存在
        """
        # 获取版本1
        result = await self.db.execute(
            select(DraftVersion)
            .where(
                DraftVersion.draft_id == draft_id,
                DraftVersion.version_number == 1
            )
        )
        version = result.scalar_one_or_none()
        
        if not version:
            error_msg = f"AI原始版本不存在: draft_id={draft_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if version.content_md:
            media = version.media_map if version.media_map is not None else None
            if media is None:
                current = await self.get_draft(draft_id)
                media = (current.media_map if current else None) or {}
            draft = await self.update_draft(
                draft_id=draft_id,
                ai_content_md=version.content_md,
                media_map=media,
                created_by=created_by
            )
        else:
            draft = await self.update_draft(
                draft_id=draft_id,
                content=version.content,
                created_by=created_by
            )
        
        logger.info(f"恢复AI原始版本成功: draft_id={draft_id}")
        
        return draft
    
    async def list_drafts(
        self,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> tuple[List[Draft], int]:
        """
        获取草稿列表
        
        Args:
            status: 状态筛选（'draft', 'published'）
            page: 页码（从1开始）
            size: 每页数量
        
        Returns:
            (草稿列表, 总数)
        """
        # 构建查询
        query = select(Draft).options(
            selectinload(Draft.submission),
            selectinload(Draft.published_site)
        )
        
        if status:
            query = query.where(Draft.status == status)
        
        # 获取总数
        count_query = select(Draft)
        if status:
            count_query = count_query.where(Draft.status == status)
        
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # 分页查询
        query = query.order_by(desc(Draft.created_at))
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.db.execute(query)
        drafts = result.scalars().all()
        
        logger.debug(
            f"获取草稿列表: status={status}, page={page}, size={size}, "
            f"count={len(drafts)}, total={total}"
        )
        
        return list(drafts), total
    
    async def mark_as_published(
        self,
        draft_id: int,
        site_id: int,
        wordpress_post_id: int
    ) -> Draft:
        """
        标记草稿为已发布
        
        Args:
            draft_id: 草稿ID
            site_id: WordPress站点ID
            wordpress_post_id: WordPress文章ID
        
        Returns:
            更新后的草稿对象
        
        Raises:
            ValueError: 如果草稿不存在
        """
        draft = await self.get_draft(draft_id)
        if not draft:
            error_msg = f"草稿不存在: draft_id={draft_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        draft.status = 'published'
        draft.published_at = datetime.utcnow()
        draft.published_to_site_id = site_id
        draft.wordpress_post_id = wordpress_post_id
        draft.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(draft)
        
        logger.info(
            f"草稿标记为已发布: draft_id={draft_id}, site_id={site_id}, "
            f"wordpress_post_id={wordpress_post_id}"
        )
        
        return draft
    
    async def _cleanup_old_versions(self, draft_id: int, keep_count: int = 30):
        """
        清理旧版本，只保留最近的N个版本
        
        Args:
            draft_id: 草稿ID
            keep_count: 保留的版本数量
        """
        # 获取所有版本
        result = await self.db.execute(
            select(DraftVersion)
            .where(DraftVersion.draft_id == draft_id)
            .order_by(desc(DraftVersion.version_number))
        )
        versions = result.scalars().all()
        
        # 如果版本数量超过限制，删除旧版本（delete 非异步，不可 await）
        if len(versions) > keep_count:
            versions_to_delete = versions[keep_count:]
            for version in versions_to_delete:
                self.db.delete(version)
            await self.db.commit()
            
            logger.info(
                f"清理旧版本: draft_id={draft_id}, deleted={len(versions_to_delete)}, "
                f"kept={keep_count}"
            )
    
    async def delete_draft(self, draft_id: int):
        """
        删除草稿（级联删除所有版本）
        
        Args:
            draft_id: 草稿ID
        
        Raises:
            ValueError: 如果草稿不存在
        """
        draft = await self.get_draft(draft_id)
        if not draft:
            error_msg = f"草稿不存在: draft_id={draft_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        await self.db.delete(draft)
        await self.db.commit()
        
        logger.info(f"草稿删除成功: draft_id={draft_id}")
