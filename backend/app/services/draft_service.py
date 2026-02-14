"""
草稿管理服务
"""
import logging
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
    
    async def create_draft(
        self,
        submission_id: int,
        transformed_content: str,
        created_by: Optional[int] = None
    ) -> Draft:
        """
        创建草稿
        
        Args:
            submission_id: 投稿ID
            transformed_content: AI转换后的内容
            created_by: 创建者用户ID（可选）
        
        Returns:
            创建的草稿对象
        
        Raises:
            ValueError: 如果投稿不存在或内容为空
        """
        # 验证投稿是否存在
        result = await self.db.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        
        if not submission:
            error_msg = f"投稿不存在: submission_id={submission_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 验证内容不为空
        if not transformed_content or not transformed_content.strip():
            error_msg = "转换后的内容不能为空"
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
                transformed_content,
                created_by=created_by
            )
        
        # 创建草稿记录
        draft = Draft(
            submission_id=submission_id,
            current_content=transformed_content,
            current_version=1,
            status='draft'
        )
        
        self.db.add(draft)
        await self.db.flush()  # 获取draft.id
        
        # 创建第一个版本记录
        version = DraftVersion(
            draft_id=draft.id,
            version_number=1,
            content=transformed_content,
            created_by=created_by
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(draft)
        
        logger.info(
            f"草稿创建成功: draft_id={draft.id}, submission_id={submission_id}, "
            f"content_length={len(transformed_content)}"
        )
        
        return draft
    
    async def update_draft(
        self,
        draft_id: int,
        content: str,
        created_by: Optional[int] = None
    ) -> Draft:
        """
        更新草稿内容（创建新版本）
        
        Args:
            draft_id: 草稿ID
            content: 新的内容
            created_by: 创建者用户ID（可选）
        
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
        
        # 验证内容不为空
        if not content or not content.strip():
            error_msg = "内容不能为空"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 检查内容是否有变化
        if content.strip() == draft.current_content.strip():
            logger.info(f"内容未变化，不创建新版本: draft_id={draft_id}")
            return draft
        
        # 更新草稿当前内容和版本号
        new_version_number = draft.current_version + 1
        draft.current_content = content
        draft.current_version = new_version_number
        draft.updated_at = datetime.utcnow()
        
        # 创建新版本记录
        version = DraftVersion(
            draft_id=draft_id,
            version_number=new_version_number,
            content=content,
            created_by=created_by
        )
        
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(draft)
        
        logger.info(
            f"草稿更新成功: draft_id={draft_id}, new_version={new_version_number}, "
            f"content_length={len(content)}"
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
        
        # 使用版本内容更新草稿
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
        
        # 使用版本1的内容更新草稿
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
        
        # 如果版本数量超过限制，删除旧版本
        if len(versions) > keep_count:
            versions_to_delete = versions[keep_count:]
            
            for version in versions_to_delete:
                await self.db.delete(version)
            
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
