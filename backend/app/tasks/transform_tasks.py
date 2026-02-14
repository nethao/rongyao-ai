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
                
                # 提取原文中的图片标记并用占位符替换
                import re
                img_pattern = r'!\[图片\d+\]\([^\)]+\)'
                original_images = re.findall(img_pattern, submission.original_content)
                
                # 用占位符替换图片，保留位置
                text_with_placeholders = submission.original_content
                for idx, img_md in enumerate(original_images):
                    text_with_placeholders = text_with_placeholders.replace(
                        img_md, 
                        f'[IMAGE_PLACEHOLDER_{idx}]', 
                        1  # 只替换第一个匹配
                    )
                
                # 清理多余空行
                text_with_placeholders = re.sub(r'\n{3,}', '\n\n', text_with_placeholders).strip()
                
                logger.info(
                    f"原文处理: 总长度={len(submission.original_content)}, "
                    f"带占位符={len(text_with_placeholders)}, 图片={len(original_images)}"
                )
                
                # 调用LLM进行转换（包含占位符）
                transformed_content = await llm_service.transform_text(
                    text=text_with_placeholders,
                    system_prompt=system_prompt,
                    temperature=0.7
                )
                
                # 将占位符替换回图片Markdown
                for idx, img_md in enumerate(original_images):
                    placeholder = f'[IMAGE_PLACEHOLDER_{idx}]'
                    transformed_content = transformed_content.replace(placeholder, f'\n{img_md}\n')
                
                logger.info(
                    f"AI转换完成: submission_id={submission_id}, "
                    f"原文长度={len(submission.original_content)}, "
                    f"转换后长度={len(transformed_content)}, "
                    f"图片数量={len(original_images)}"
                )
                
                # 创建草稿记录
                from app.services.draft_service import DraftService
                draft_service = DraftService(db)
                
                draft = await draft_service.create_draft(
                    submission_id=submission_id,
                    transformed_content=transformed_content
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
                    "transformed_length": len(transformed_content)
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
                
                # 重试任务（如果是可重试的错误）
                if "rate limit" in str(e).lower() or "connection" in str(e).lower():
                    logger.info(f"将重试任务: submission_id={submission_id}")
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
