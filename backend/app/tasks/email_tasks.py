"""
邮件抓取相关的Celery任务
"""
import os
import tempfile
from sqlalchemy import text
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
    import nest_asyncio
    
    # 允许嵌套事件循环
    nest_asyncio.apply()
    
    async def _fetch():
        logger.info("开始执行邮件抓取任务")
        
        # 记录任务开始
        async with AsyncSessionLocal() as db:
            from app.services.submission_service import SubmissionService
            service = SubmissionService(db)
            await service.log_task(
                task_type="fetch_email",
                task_id=None,
                status="started",
                message="开始抓取邮箱未读邮件"
            )
        
        try:
            # 初始化服务
            fetcher = IMAPFetcher()
            doc_processor = DocumentProcessor()
            oss_service = OSSService()
            
            # 获取未读邮件
            emails = fetcher.fetch_unread_emails(limit=10, mark_as_read=True)
            logger.info(f"获取到 {len(emails)} 封未读邮件")
            
            # 处理每封邮件
            processed_count = 0
            for email_data in emails:
                try:
                    await process_email(email_data, doc_processor, oss_service)
                    processed_count += 1
                except Exception as e:
                    logger.error(f"处理邮件失败: {str(e)}")
                    continue
            
            # 记录任务成功
            async with AsyncSessionLocal() as db:
                from app.services.submission_service import SubmissionService
                service = SubmissionService(db)
                await service.log_task(
                    task_type="fetch_email",
                    task_id=None,
                    status="success",
                    message=f"邮件抓取完成，共处理 {processed_count} 封邮件"
                )
            
            logger.info("邮件抓取任务完成")
            return {"success": True, "processed": processed_count}
        
        except Exception as e:
            # 记录任务失败
            async with AsyncSessionLocal() as db:
                from app.services.submission_service import SubmissionService
                service = SubmissionService(db)
                await service.log_task(
                    task_type="fetch_email",
                    task_id=None,
                    status="failed",
                    message=f"邮件抓取失败: {str(e)}"
                )
            
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
    from app.services.email_parser import EmailParser, ContentType
    from app.services.web_fetcher import WebFetcher
    
    async with AsyncSessionLocal() as db:
        submission_service = SubmissionService(db)
        
        # 解析邮件标题
        cooperation, media_type, source_unit, title = EmailParser.parse_subject(email_data.subject)
        
        logger.info(f"邮件解析结果 - 合作方式:{cooperation}, 媒体:{media_type}, 单位:{source_unit}, 标题:{title}")
        
        # 记录任务开始
        await submission_service.log_task(
            task_type="fetch_email",
            task_id=None,
            status="started",
            message=f"开始处理邮件: {email_data.subject}"
        )
        
        try:
            # 检测内容类型
            content_type = EmailParser.detect_content_type(email_data.body, email_data.attachments)
            logger.info(f"内容类型: {content_type}")
            
            content = email_data.body
            doc_path = None
            docx_path = None
            images_to_upload = []
            original_html = None  # 保存原始HTML
            
            # 根据内容类型处理
            if content_type == ContentType.WEIXIN:
                # 抓取公众号文章
                url = EmailParser.extract_url(email_data.body, ContentType.WEIXIN)
                if url:
                    logger.info(f"抓取公众号文章: {url}")
                    fetcher = WebFetcher()
                    fetched_title, fetched_content, fetched_html, image_urls = fetcher.fetch_weixin_article(url)
                    
                    if fetched_content:
                        content = fetched_content
                        original_html = fetched_html  # 保存原始HTML
                        # 优先使用抓取的标题
                        if fetched_title:
                            title = fetched_title
                        
                        # 下载图片
                        for idx, img_url in enumerate(image_urls):
                            img_data = fetcher.download_image(img_url)
                            if img_data:
                                images_to_upload.append((f"weixin_image_{idx}.jpg", img_data))
            
            elif content_type == ContentType.MEIPIAN:
                # 抓取美篇文章
                url = EmailParser.extract_url(email_data.body, ContentType.MEIPIAN)
                if url:
                    logger.info(f"抓取美篇文章: {url}")
                    fetcher = WebFetcher()
                    fetched_title, fetched_content, image_urls, fetched_html = fetcher.fetch_meipian_article(url)
                    
                    if fetched_content:
                        content = fetched_content
                        original_html = fetched_html  # 保存HTML保持排版
                        # 优先使用抓取的标题
                        if fetched_title:
                            title = fetched_title
                        
                        # 下载图片
                        for idx, img_url in enumerate(image_urls):
                            img_data = fetcher.download_image(img_url)
                            if img_data:
                                images_to_upload.append((f"meipian_image_{idx}.jpg", img_data))
            
            elif content_type == ContentType.WORD:
                # 处理Word文档附件
                temp_file_path = None
                docx_path_to_clean = None
                
                try:
                    for filename, file_data in email_data.attachments:
                        # 保存附件到临时文件
                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=os.path.splitext(filename)[1]
                        )
                        temp_file.write(file_data)
                        temp_file.close()
                        temp_file_path = temp_file.name
                        
                        # 处理Word文档
                        if filename.lower().endswith('.doc'):
                            doc_path = temp_file_path
                            # 转换为docx
                            docx_path = doc_processor.convert_doc_to_docx(doc_path)
                            docx_path_to_clean = docx_path
                            # 先提取标题
                            doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                            if doc_title and doc_title != "无标题":
                                title = doc_title
                                logger.info(f"从Word文档提取标题: {title}, 占用{title_lines}行")
                            # 提取文本时跳过标题行
                            content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)
                        
                        elif filename.lower().endswith('.docx'):
                            docx_path = temp_file_path
                            # 先提取标题
                            doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                            if doc_title and doc_title != "无标题":
                                title = doc_title
                                logger.info(f"从Word文档提取标题: {title}, 占用{title_lines}行")
                            # 提取文本时跳过标题行
                            content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)
                finally:
                    # 清理临时文件
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                        logger.info(f"已清理临时文件: {temp_file_path}")
                    if docx_path_to_clean and os.path.exists(docx_path_to_clean) and docx_path_to_clean != temp_file_path:
                        os.unlink(docx_path_to_clean)
                        logger.info(f"已清理转换后的docx文件: {docx_path_to_clean}")
            
            elif content_type == ContentType.ARCHIVE:
                # 处理压缩包 - 解压并处理Word+图片
                import zipfile
                import tempfile
                import os
                
                for filename, file_data in email_data.attachments:
                    if filename.lower().endswith('.zip'):
                        logger.info(f"发现压缩包: {filename}, 大小: {len(file_data)/1024/1024:.2f}MB")
                        
                        # 保存压缩包到临时文件
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as zip_file:
                            zip_file.write(file_data)
                            zip_path = zip_file.name
                        
                        # 解压到临时目录
                        extract_dir = tempfile.mkdtemp()
                        try:
                            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                                zip_ref.extractall(extract_dir)
                            logger.info(f"压缩包已解压到: {extract_dir}")
                            
                            # 查找Word文档
                            word_file = None
                            for root, dirs, files in os.walk(extract_dir):
                                for file in files:
                                    if file.lower().endswith(('.doc', '.docx')):
                                        word_file = os.path.join(root, file)
                                        break
                                if word_file:
                                    break
                            
                            if word_file:
                                logger.info(f"找到Word文档: {word_file}")
                                
                                # 转换.doc为.docx
                                if word_file.lower().endswith('.doc'):
                                    docx_path = doc_processor.convert_doc_to_docx(word_file)
                                else:
                                    docx_path = word_file
                                
                                # 提取标题
                                doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                                if doc_title and doc_title != "无标题":
                                    title = doc_title
                                    logger.info(f"从Word文档提取标题: {title}, 占用{title_lines}行")
                                
                                # 提取文本（跳过标题行）
                                content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)
                                
                                # 提取图片
                                images = doc_processor.extract_images_from_docx(docx_path)
                                logger.info(f"从Word文档提取{len(images)}张图片")
                                
                                # 上传图片到待上传列表
                                for img_filename, img_data in images:
                                    images_to_upload.append((img_filename, img_data))
                            else:
                                logger.warning("压缩包中未找到Word文档")
                                content = "压缩包中未找到Word文档"
                        
                        finally:
                            # 清理临时文件
                            import shutil
                            shutil.rmtree(extract_dir, ignore_errors=True)
                            os.unlink(zip_path)
            
            elif content_type == ContentType.VIDEO:
                # 处理视频附件 - 直接上传到OSS
                video_urls = []
                for filename, file_data in email_data.attachments:
                    if any(filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']):
                        logger.info(f"发现视频文件: {filename}, 大小: {len(file_data)/1024/1024:.2f}MB")
                        # 直接上传到OSS
                        oss_url, oss_key = oss_service.upload_file(
                            file_data=file_data,
                            filename=filename,
                            folder='videos'
                        )
                        video_urls.append(oss_url)
                        logger.info(f"视频已上传到OSS: {oss_url}")
                
                # 生成视频嵌入代码，并保留邮件正文
                video_html = "\n\n".join([f'<video controls width="100%"><source src="{url}" type="video/mp4"></video>' for url in video_urls])
                if content:
                    # 邮件正文 + 视频
                    content = f"{content}\n\n{video_html}"
                else:
                    content = video_html
            
            # 确定内容来源
            if content_type == ContentType.WEIXIN:
                content_source = 'weixin'
            elif content_type == ContentType.MEIPIAN:
                content_source = 'meipian'
            elif content_type == ContentType.ARCHIVE:
                # 压缩包解压后按Word处理
                content_source = 'docx'
            elif content_type == ContentType.VIDEO:
                content_source = 'video'
            elif doc_path:
                content_source = 'doc'
            elif docx_path:
                content_source = 'docx'
            else:
                content_source = 'text'
            
            # 创建投稿记录（使用解析后的标题，保存原始HTML）
            submission = await submission_service.create_submission(
                email_subject=title or email_data.subject,
                email_from=email_data.from_addr,
                email_date=email_data.date,
                original_content=content,
                doc_file_path=doc_path,
                docx_file_path=docx_path
            )
            
            # 更新content_source和original_html
            update_data = {'id': submission.id}
            if original_html:
                update_data['html'] = original_html
                logger.info(f"已保存原始HTML，长度: {len(original_html)}")
            
            await db.execute(
                text('UPDATE submissions SET original_html = :html, content_source = :source WHERE id = :id'),
                {'html': original_html, 'source': content_source, 'id': submission.id}
            )
            await db.commit()
            
            # 保存解析的元数据
            if cooperation or media_type or source_unit:
                site_id = EmailParser.get_wordpress_site_id(media_type) if media_type else None
                
                # 更新投稿记录的元数据
                await db.execute(
                    text('''
                        UPDATE submissions 
                        SET cooperation_type = :cooperation,
                            media_type = :media,
                            source_unit = :source,
                            target_site_id = :site_id
                        WHERE id = :id
                    '''),
                    {
                        'cooperation': cooperation.value if cooperation else None,
                        'media': media_type.value if media_type else None,
                        'source': source_unit,
                        'site_id': site_id,
                        'id': submission.id
                    }
                )
                await db.commit()
                
                logger.info(f"元数据已保存: 合作={cooperation}, 媒体={media_type}, 单位={source_unit}, 站点={site_id}")
            
            # 上传从网页抓取的图片并替换URL
            url_mapping = {}  # 原始URL -> OSS URL的映射（用于 Markdown content）
            oss_urls_ordered = []  # 按图片顺序的 OSS URL 列表（用于 HTML 按序替换）
            original_image_urls = []  # 保存原始图片URL顺序
            
            for idx, (img_filename, img_data) in enumerate(images_to_upload):
                try:
                    oss_url, oss_key = oss_service.upload_file(
                        file_data=img_data,
                        filename=img_filename,
                        folder=f"submissions/{submission.id}"
                    )
                    
                    await submission_service.add_image(
                        submission_id=submission.id,
                        oss_url=oss_url,
                        oss_key=oss_key,
                        original_filename=img_filename,
                        file_size=len(img_data)
                    )
                    
                    oss_urls_ordered.append(oss_url)
                    
                    # 记录原始URL（从image_urls列表获取）
                    if idx < len(image_urls):
                        original_image_urls.append(image_urls[idx])
                    
                    # 记录URL映射（用于替换 Markdown content）
                    if content_type in [ContentType.WEIXIN, ContentType.MEIPIAN]:
                        import re
                        pattern = rf'!\[图片{idx+1}\]\(([^\)]+)\)'
                        match = re.search(pattern, content)
                        if match:
                            original_url = match.group(1)
                            url_mapping[original_url] = oss_url
                            
                except Exception as e:
                    logger.error(f"上传图片失败: {str(e)}")
                    continue
            
            # 替换 Markdown content 中的图片URL为 OSS URL
            if url_mapping:
                for original_url, oss_url in url_mapping.items():
                    content = content.replace(original_url, oss_url)
            
            # 美篇：从HTML生成图文混排的Markdown
            if content_type == ContentType.MEIPIAN and original_html and oss_urls_ordered:
                from bs4 import BeautifulSoup, NavigableString
                soup = BeautifulSoup(original_html, 'html.parser')
                content_tag = soup.find('div', {'class': 'mp-article-tpl'})
                
                if content_tag:
                    markdown_parts = []
                    img_index = 0
                    
                    # 遍历所有子元素，保持图文顺序
                    for elem in content_tag.descendants:
                        if elem.name == 'img' and img_index < len(oss_urls_ordered):
                            markdown_parts.append(f'\n![图片{img_index+1}]({oss_urls_ordered[img_index]})\n')
                            img_index += 1
                        elif isinstance(elem, NavigableString) and elem.strip():
                            elem_text = elem.strip()
                            if elem_text and not elem_text.startswith('[IMAGE_'):
                                markdown_parts.append(elem_text)
                    
                    content = '\n\n'.join([p for p in markdown_parts if p.strip()])
                    logger.info(f"美篇Markdown已生成，保持图文混排，{img_index}张图片")
            
            # 公众号/美篇：替换HTML中的图片URL为OSS URL
            if original_html and content_type in [ContentType.WEIXIN, ContentType.MEIPIAN] and len(oss_urls_ordered) > 0:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(original_html, 'html.parser')
                imgs = soup.find_all('img')
                for i, img in enumerate(imgs):
                    if i < len(oss_urls_ordered):
                        img['src'] = oss_urls_ordered[i]
                        if img.get('data-src'):
                            img['data-src'] = oss_urls_ordered[i]
                original_html = str(soup)
                logger.info(f"HTML已替换 {len(oss_urls_ordered)} 个图片URL为OSS地址")
            
            # 更新投稿内容和 HTML
            if url_mapping or oss_urls_ordered:
                await db.execute(
                    text('UPDATE submissions SET original_content = :content, original_html = :html WHERE id = :id'),
                    {'content': content, 'html': original_html, 'id': submission.id}
                )
                await db.commit()
                logger.info(f"已替换 {len(oss_urls_ordered) or len(url_mapping)} 个图片URL为OSS地址")
            
            # 提取并上传Word文档中的图片
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
            
            # 创建原文草稿（供编辑人员查看和手动编辑）
            from app.services.draft_service import DraftService
            from app.utils.content_processor import ContentProcessor
            draft_service = DraftService(db)
            
            # 公众号和美篇：将HTML转换为Markdown，并插入占位符
            if (content_type == ContentType.WEIXIN or content_type == ContentType.MEIPIAN) and original_html:
                import html2text
                from bs4 import BeautifulSoup
                
                # 先用BeautifulSoup替换img标签为占位符
                soup = BeautifulSoup(original_html, 'html.parser')
                img_tags = soup.find_all('img')
                
                for idx, img in enumerate(img_tags, start=1):
                    placeholder = f'[[IMG_{idx}]]'
                    img.replace_with(placeholder)
                
                # 转换为Markdown
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0
                draft_content = h.handle(str(soup))
            else:
                draft_content = content
            
            draft = await draft_service.create_draft(
                submission_id=submission.id,
                transformed_content=draft_content
            )
            logger.info(f"已创建原文草稿: draft_id={draft.id}, content_type={content_type}")
            
            # 更新状态为completed
            await submission_service.update_status(submission.id, 'completed')
            
            # 记录任务成功
            await submission_service.log_task(
                task_type="fetch_email",
                task_id=str(submission.id),
                status="success",
                message=f"邮件处理成功: submission_id={submission.id}"
            )
            
            logger.info(f"邮件处理成功: submission_id={submission.id}, 等待编辑人员操作")
        
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
