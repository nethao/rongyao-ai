"""
投稿管理服务
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.submission import Submission, SubmissionImage
from app.models.task_log import TaskLog
import logging

logger = logging.getLogger(__name__)


class SubmissionService:
    """投稿管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_submission(
        self,
        email_subject: str,
        email_from: str,
        email_date,
        original_content: str,
        doc_file_path: Optional[str] = None,
        docx_file_path: Optional[str] = None
    ) -> Submission:
        """
        创建投稿记录
        
        Args:
            email_subject: 邮件主题
            email_from: 发件人
            email_date: 邮件日期
            original_content: 原始内容
            doc_file_path: .doc文件路径
            docx_file_path: .docx文件路径
        
        Returns:
            Submission: 创建的投稿对象
        """
        submission = Submission(
            email_subject=email_subject,
            email_from=email_from,
            email_date=email_date,
            original_content=original_content,
            doc_file_path=doc_file_path,
            docx_file_path=docx_file_path,
            status='pending'
        )
        
        self.db.add(submission)
        await self.db.commit()
        await self.db.refresh(submission)
        
        logger.info(f"创建投稿记录: ID={submission.id}")
        return submission
    
    async def add_image(
        self,
        submission_id: int,
        oss_url: str,
        oss_key: str,
        original_filename: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> SubmissionImage:
        """
        添加投稿图片
        
        Args:
            submission_id: 投稿ID
            oss_url: OSS URL
            oss_key: OSS Key
            original_filename: 原始文件名
            file_size: 文件大小
        
        Returns:
            SubmissionImage: 创建的图片对象
        """
        image = SubmissionImage(
            submission_id=submission_id,
            oss_url=oss_url,
            oss_key=oss_key,
            original_filename=original_filename,
            file_size=file_size
        )
        
        self.db.add(image)
        await self.db.commit()
        await self.db.refresh(image)
        
        logger.info(f"添加投稿图片: submission_id={submission_id}, url={oss_url}")
        return image
    
    async def update_status(
        self,
        submission_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> bool:
        """
        更新投稿状态
        
        Args:
            submission_id: 投稿ID
            status: 状态（pending, processing, completed, failed）
            error_message: 错误信息
        
        Returns:
            bool: 是否更新成功
        """
        result = await self.db.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        
        if not submission:
            logger.warning(f"投稿不存在: ID={submission_id}")
            return False
        
        submission.status = status
        if error_message:
            submission.error_message = error_message
        
        await self.db.commit()
        logger.info(f"更新投稿状态: ID={submission_id}, status={status}")
        return True
    
    async def get_submission(
        self,
        submission_id: int,
        include_images: bool = True
    ) -> Optional[Submission]:
        """
        获取投稿详情
        
        Args:
            submission_id: 投稿ID
            include_images: 是否包含图片
        
        Returns:
            Optional[Submission]: 投稿对象
        """
        query = select(Submission).where(Submission.id == submission_id)
        
        if include_images:
            query = query.options(selectinload(Submission.images))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_submissions(
        self,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> tuple[List[Submission], int]:
        """
        获取投稿列表
        
        Args:
            status: 状态过滤
            page: 页码
            size: 每页数量
        
        Returns:
            tuple[List[Submission], int]: (投稿列表, 总数)
        """
        # 构建查询
        query = select(Submission).options(selectinload(Submission.images))
        
        if status:
            query = query.where(Submission.status == status)
        
        # 计算总数
        count_query = select(Submission)
        if status:
            count_query = count_query.where(Submission.status == status)
        
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # 分页查询
        query = query.order_by(Submission.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        
        result = await self.db.execute(query)
        submissions = result.scalars().all()
        
        return list(submissions), total
    
    async def log_task(
        self,
        task_type: str,
        task_id: Optional[str],
        status: str,
        message: Optional[str] = None
    ) -> TaskLog:
        """
        记录任务日志
        
        Args:
            task_type: 任务类型
            task_id: 任务ID
            status: 状态
            message: 消息
        
        Returns:
            TaskLog: 任务日志对象
        """
        log = TaskLog(
            task_type=task_type,
            task_id=task_id,
            status=status,
            message=message
        )
        
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        
        return log
