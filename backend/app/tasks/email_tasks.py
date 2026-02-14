"""
邮件抓取相关的Celery任务
"""
import os
import tempfile
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.imap_fetcher import IMAPFetcher
from app.services.document_processor import DocumentProcessor
from app.services.oss_service import OSSService
from app.services.submission_service import SubmissionService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="fetch_emails")
def fetch_emails_task():
    """
    定时抓取邮件任务
    
    该任务会：
    1. 连接IMAP服务器
    2. 获取未读邮件
    3. 提取附件和内容
    4. 转换.doc为.docx
    5. 提取图片并上传OSS
    6. 创建Submission记录
    7. 触发AI转换任务
    """
    import asyncio
    
    async def _fetch():
        logger.info("开始执行邮件抓取任务")
        
        try:
            # 初始化服务
            fetcher = IMAPFetcher()
            doc_processor = DocumentProcessor()
            oss_service = OSSService()
            
            # 获取未读邮件
            emails = fetcher.fetch_unread_emails(limit=10, mark_as_read=True)
            logger.info(f"获取到 {len(emails)} 封未读邮件")
            
            # 处理每封邮件
            for email_data in emails:
                try:
                    await process_email(email_data, doc_processor, oss_service)
                except Exception as e:
                    logger.error(f"处理邮件失败: {str(e)}")
                    continue
            
            logger.info("邮件抓取任务完成")
            return {"success": True, "processed": len(emails)}
        
        except Exception as e:
            logger.error(f"邮件抓取任务失败: {str(e)}")
            return {"success": False, "error": str(e)}
    
    # 运行异步任务
    return asyncio.run(_fetch())


async def process_email(email_data, doc_processor, oss_service):
    """
    处理单封邮件
    
    Args:
        email_data: 邮件数据对象
        doc_processor: 文档处理器
        oss_service: OSS服务
    """
    async with AsyncSessionLocal() as db:
        submission_service = SubmissionService(db)
        
        # 记录任务开始
        await submission_service.log_task(
            task_type="fetch_email",
            task_id=None,
            status="started",
            message=f"开始处理邮件: {email_data.subject}"
        )
        
        try:
            # 处理附件
            doc_path = None
            docx_path = None
            content = email_data.body
            
            for filename, file_data in email_data.attachments:
                # 保存附件到临时文件
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=os.path.splitext(filename)[1]
                )
                temp_file.write(file_data)
                temp_file.close()
                
                # 处理Word文档
                if filename.lower().endswith('.doc'):
                    doc_path = temp_file.name
                    # 转换为docx
                    docx_path = doc_processor.convert_doc_to_docx(doc_path)
                    # 提取文本
                    content = doc_processor.extract_text_from_docx(docx_path)
                
                elif filename.lower().endswith('.docx'):
                    docx_path = temp_file.name
                    # 提取文本
                    content = doc_processor.extract_text_from_docx(docx_path)
            
            # 创建投稿记录
            submission = await submission_service.create_submission(
                email_subject=email_data.subject,
                email_from=email_data.from_addr,
                email_date=email_data.date,
                original_content=content,
                doc_file_path=doc_path,
                docx_file_path=docx_path
            )
            
            # 提取并上传图片
            if docx_path:
                images = doc_processor.extract_images_from_docx(docx_path)
                
                for img_filename, img_data in images:
                    try:
                        # 上传到OSS
                        oss_url, oss_key = oss_service.upload_file(
                            file_data=img_data,
                            filename=img_filename,
                            folder=f"submissions/{submission.id}"
                        )
                        
                        # 记录图片信息
                        await submission_service.add_image(
                            submission_id=submission.id,
                            oss_url=oss_url,
                            oss_key=oss_key,
                            original_filename=img_filename,
                            file_size=len(img_data)
                        )
                    
                    except Exception as e:
                        logger.error(f"上传图片失败: {str(e)}")
                        continue
            
            # 更新状态为completed
            await submission_service.update_status(submission.id, 'completed')
            
            # 记录任务成功
            await submission_service.log_task(
                task_type="fetch_email",
                task_id=str(submission.id),
                status="success",
                message=f"邮件处理成功: submission_id={submission.id}"
            )
            
            logger.info(f"邮件处理成功: submission_id={submission.id}")
            
            # 触发AI转换任务
            from app.tasks.transform_tasks import transform_content_task
            transform_content_task.delay(submission.id)
            logger.info(f"已触发AI转换任务: submission_id={submission.id}")
        
        except Exception as e:
            error_msg = f"邮件处理失败: {str(e)}"
            logger.error(error_msg)
            
            # 记录任务失败
            await submission_service.log_task(
                task_type="fetch_email",
                task_id=None,
                status="failed",
                message=error_msg
            )
            
            raise


@celery_app.task(name="convert_doc_to_docx")
def convert_doc_to_docx_task(doc_path: str) -> str:
    """
    使用LibreOffice转换文档格式
    
    Args:
        doc_path: .doc文件路径
    
    Returns:
        str: 转换后的.docx文件路径
    """
    try:
        processor = DocumentProcessor()
        docx_path = processor.convert_doc_to_docx(doc_path)
        logger.info(f"文档转换成功: {docx_path}")
        return docx_path
    except Exception as e:
        logger.error(f"文档转换失败: {str(e)}")
        raise


@celery_app.task(name="extract_images_from_docx")
def extract_images_task(docx_path: str) -> list:
    """
    从docx提取图片并上传OSS
    
    Args:
        docx_path: .docx文件路径
    
    Returns:
        list: 上传后的图片URL列表
    """
    try:
        processor = DocumentProcessor()
        oss_service = OSSService()
        
        # 提取图片
        images = processor.extract_images_from_docx(docx_path)
        
        # 上传到OSS
        uploaded_urls = []
        for filename, image_data in images:
            oss_url, oss_key = oss_service.upload_file(
                file_data=image_data,
                filename=filename
            )
            uploaded_urls.append(oss_url)
        
        logger.info(f"成功上传 {len(uploaded_urls)} 张图片")
        return uploaded_urls
    
    except Exception as e:
        logger.error(f"图片提取上传失败: {str(e)}")
        raise
