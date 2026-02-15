"""
AI转换相关的Celery任务
"""
import logging
from typing import Optional
from datetime import datetime

from sqlalchemy import text
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.llm_service import LLMService, LLMServiceError
from app.services.prompt_builder import PromptBuilder
from app.services.submission_service import SubmissionService


logger = logging.getLogger(__name__)


@celery_app.task(name="transform_content", bind=True, max_retries=3)
def transform_content_task(self, submission_id: int):
    """
    AI语义转换任务
    
    该任务会：
    1. 获取原始内容
    2. 构建LLM提示词
    3. 调用LLM API进行转换
    4. 解析转换结果
    5. 创建Draft记录
    
    Args:
        submission_id: 投稿ID
    
    Returns:
        dict: 包含转换结果的字典
    """
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    
    async def _transform():
        logger.info(f"开始AI转换任务: submission_id={submission_id}")
        
        async with AsyncSessionLocal() as db:
            submission_service = SubmissionService(db)
            
            # 记录任务开始
            await submission_service.log_task(
                task_type="ai_transform",
                task_id=str(submission_id),
                status="started",
                message=f"开始AI转换: submission_id={submission_id}"
            )
            
            try:
                # 获取投稿记录
                submission = await submission_service.get_submission(submission_id)
                if not submission:
                    error_msg = f"投稿记录不存在: submission_id={submission_id}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # 视频和压缩包类型跳过AI改写，直接创建草稿
                if submission.content_source in ['video', 'archive']:
                    logger.info(f"{submission.content_source}类型跳过AI改写，直接创建草稿")
                    
                    draft = await db.execute(
                        text('''
                            INSERT INTO drafts (submission_id, current_content, ai_content_md, status)
                            VALUES (:submission_id, :content, :content, 'draft')
                            RETURNING id
                        '''),
                        {
                            'submission_id': submission_id,
                            'content': submission.original_content
                        }
                    )
                    draft_id = draft.scalar_one()
                    await db.commit()
                    
                    await submission_service.update_status(submission_id, 'completed')
                    logger.info(f"{submission.content_source}草稿创建成功: draft_id={draft_id}")
                    
                    return {
                        'status': 'success',
                        'submission_id': submission_id,
                        'draft_id': draft_id,
                        'skipped': True,
                        'reason': submission.content_source
                    }
                
                # 更新状态为processing
                await submission_service.update_status(submission_id, 'processing')
                
                # 初始化服务
                llm_service = await LLMService.from_config_service(db)
                prompt_builder = PromptBuilder()
                
                # 提取来源名称
                source_name = prompt_builder.extract_source_name_from_content(
                    submission.original_content
                )
                
                # 提取参考日期
                reference_date = prompt_builder.extract_reference_date_from_email(
                    submission.email_date
                )
                
                # 构建提示词
                system_prompt = prompt_builder.build_transform_prompt(
                    source_name=source_name,
                    reference_date=reference_date
                )
                
                logger.info(
                    f"构建提示词完成: source_name={source_name}, "
                    f"reference_date={reference_date}"
                )
                
                # 使用占位符协议：从submission.images生成占位符
                from app.utils.content_processor import ContentProcessor
                
                # 获取图片列表（按ID排序）
                images = [
                    {"oss_url": img.oss_url, "original_filename": img.original_filename}
                    for img in sorted(submission.images, key=lambda x: x.id)
                ]
                
                # 生成带占位符的Markdown和media_map
                original_md, media_map = ContentProcessor.extract_images_from_content(
                    submission.original_content,
                    images
                )
                
                logger.info(
                    f"原文处理: 总长度={len(submission.original_content)}, "
                    f"带占位符={len(original_md)}, 图片={len(images)}"
                )
                
                # 调用LLM进行转换（AI只看到占位符，不看到URL）
                transformed_md = await llm_service.transform_text(
                    text=original_md,
                    system_prompt=system_prompt,
                    temperature=0.7
                )
                
                logger.info(
                    f"AI转换完成: submission_id={submission_id}, "
                    f"原文长度={len(submission.original_content)}, "
                    f"转换后长度={len(transformed_md)}, "
                    f"图片数量={len(images)}"
                )
                
                # 创建草稿记录（使用占位符协议）
                from app.services.draft_service import DraftService
                draft_service = DraftService(db)
                
                draft = await draft_service.create_draft(
                    submission_id=submission_id,
                    original_content_md=original_md,
                    ai_content_md=transformed_md,
                    media_map=media_map
                )
                
                logger.info(f"草稿创建成功: draft_id={draft.id}")
                
                # 更新投稿状态为completed
                await submission_service.update_status(submission_id, 'completed')
                
                # 记录任务成功
                await submission_service.log_task(
                    task_type="ai_transform",
                    task_id=str(submission_id),
                    status="success",
                    message=f"AI转换成功: draft_id={draft.id}"
                )
                
                # 关闭LLM服务
                await llm_service.close()
                
                return {
                    "success": True,
                    "submission_id": submission_id,
                    "draft_id": draft.id,
                    "original_length": len(submission.original_content),
                    "transformed_length": len(transformed_md)
                }
            
            except LLMServiceError as e:
                error_msg = f"LLM服务错误: {str(e)}"
                logger.error(error_msg)
                
                # 更新投稿状态为failed
                await submission_service.update_status(
                    submission_id,
                    'failed',
                    error_message=error_msg
                )
                
                # 记录任务失败
                await submission_service.log_task(
                    task_type="ai_transform",
                    task_id=str(submission_id),
                    status="failed",
                    message=error_msg
                )
                
                # 重试任务（限流/容量限制/连接类错误均可重试）
                err_lower = str(e).lower()
                if (
                    "rate limit" in err_lower
                    or "throttl" in err_lower
                    or "too many requests" in err_lower
                    or "connection" in err_lower
                    or "serviceunavailable" in err_lower
                ):
                    logger.info(f"将重试任务(限流/容量限制): submission_id={submission_id}")
                    raise self.retry(exc=e, countdown=60)  # 60秒后重试
                
                raise
            
            except Exception as e:
                error_msg = f"AI转换失败: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # 更新投稿状态为failed
                await submission_service.update_status(
                    submission_id,
                    'failed',
                    error_message=error_msg
                )
                
                # 记录任务失败
                await submission_service.log_task(
                    task_type="ai_transform",
                    task_id=str(submission_id),
                    status="failed",
                    message=error_msg
                )
                
                raise
    
    # 运行异步任务
    return asyncio.run(_transform())


@celery_app.task(name="batch_transform_content")
def batch_transform_content_task(submission_ids: list):
    """
    批量AI转换任务
    
    Args:
        submission_ids: 投稿ID列表
    
    Returns:
        dict: 包含批量转换结果的字典
    """
    logger.info(f"开始批量AI转换任务: {len(submission_ids)} 个投稿")
    
    results = {
        "total": len(submission_ids),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for submission_id in submission_ids:
        try:
            result = transform_content_task.delay(submission_id)
            results["success"] += 1
            results["details"].append({
                "submission_id": submission_id,
                "status": "queued",
                "task_id": result.id
            })
        except Exception as e:
            logger.error(f"提交转换任务失败: submission_id={submission_id}, error={str(e)}")
            results["failed"] += 1
            results["details"].append({
                "submission_id": submission_id,
                "status": "failed",
                "error": str(e)
            })
    
    logger.info(
        f"批量转换任务提交完成: 成功={results['success']}, 失败={results['failed']}"
    )
    
    return results


@celery_app.task(name="retry_failed_transform")
def retry_failed_transform_task(submission_id: int):
    """
    重试失败的AI转换任务
    
    Args:
        submission_id: 投稿ID
    
    Returns:
        dict: 包含重试结果的字典
    """
    import asyncio
    
    async def _retry():
        logger.info(f"重试AI转换任务: submission_id={submission_id}")
        
        async with AsyncSessionLocal() as db:
            submission_service = SubmissionService(db)
            
            # 获取投稿记录
            submission = await submission_service.get_submission(submission_id)
            if not submission:
                error_msg = f"投稿记录不存在: submission_id={submission_id}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # 检查状态
            if submission.status != 'failed':
                logger.warning(
                    f"投稿状态不是failed，无需重试: submission_id={submission_id}, "
                    f"status={submission.status}"
                )
                return {
                    "success": False,
                    "error": f"投稿状态不是failed: {submission.status}"
                }
            
            # 重置状态为pending
            await submission_service.update_status(
                submission_id,
                'pending',
                error_message=None
            )
            
            # 提交新的转换任务
            result = transform_content_task.delay(submission_id)
            
            logger.info(f"重试任务已提交: submission_id={submission_id}, task_id={result.id}")
            
            return {
                "success": True,
                "submission_id": submission_id,
                "task_id": result.id
            }
    
    return asyncio.run(_retry())
