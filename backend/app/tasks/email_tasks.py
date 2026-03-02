"""
邮件抓取相关的Celery任务
"""
import os
import tempfile  # 仅用于确保 sys.modules['tempfile'] 已加载，process_email 内用 sys.modules 引用
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
            # 从数据库读取 IMAP 配置
            async with AsyncSessionLocal() as db:
                from app.services.config_service import ConfigService
                cs = ConfigService(db)
                imap_host = await cs.get_config("IMAP_HOST")
                imap_port = await cs.get_config("IMAP_PORT")
                imap_user = await cs.get_config("IMAP_USER")
                imap_password = await cs.get_config("IMAP_PASSWORD", decrypt=True)
                imap_use_ssl = await cs.get_config("IMAP_USE_SSL")
                imap_timeout = await cs.get_config("IMAP_TIMEOUT_SECONDS")
            
            # 初始化服务（使用数据库配置）
            port_int = int(imap_port) if imap_port else 993
            timeout_int = int(imap_timeout) if imap_timeout else 20
            use_ssl_bool = str(imap_use_ssl).strip().lower() not in {"false", "0", "no", "off"}
            
            fetcher = IMAPFetcher(
                host=imap_host,
                port=port_int,
                username=imap_user,
                password=imap_password,
                use_ssl=use_ssl_bool
            )
            doc_processor = DocumentProcessor()
            oss_service = OSSService()
            
            # 获取未读邮件
            emails = fetcher.fetch_unread_emails(limit=10, mark_as_read=True, fallback_recent_limit=0)
            logger.info(f"获取到 {len(emails)} 封未读邮件")
            
            # 批次内去重（基于邮件主题）
            seen_subjects = set()
            unique_emails = []
            for email_data in emails:
                if email_data.subject not in seen_subjects:
                    seen_subjects.add(email_data.subject)
                    unique_emails.append(email_data)
                else:
                    logger.info(f"批次内重复邮件，跳过: {email_data.subject}")
            
            logger.info(f"去重后剩余 {len(unique_emails)} 封邮件")
            
            # 处理每封邮件
            processed_count = 0
            for email_data in unique_emails:
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
    from app.services.config_service import ConfigService
    import sys
    _tf = sys.modules["tempfile"]

    async with AsyncSessionLocal() as db:
        submission_service = SubmissionService(db)
        config_service = ConfigService(db)
        wechat302_api_key = await config_service.get_config("WECHAT302_API_KEY", decrypt=True)
        wechat302_enabled = await config_service.get_config("WECHAT302_ENABLED")
        wechat302_base_url = await config_service.get_config("WECHAT302_BASE_URL")
        weixin_cookie = await config_service.get_config("WEIXIN_COOKIE", decrypt=True)
        weixin_proxy_url = await config_service.get_config("WEIXIN_PROXY_URL", decrypt=True)
        use_wechat302 = str(wechat302_enabled or "true").strip().lower() not in {"false", "0", "no", "off"}
        
        # 跳过撤回邮件
        if "发信方已撤回邮件" in email_data.subject or "已撤回" in email_data.subject:
            logger.info(f"跳过撤回邮件: {email_data.subject}")
            return
        
        # 解析邮件标题
        cooperation, media_type, source_unit, title = EmailParser.parse_subject(email_data.subject)
        
        logger.info(f"邮件解析结果 - 合作方式:{cooperation}, 媒体:{media_type}, 单位:{source_unit}, 标题:{title}")
        
        # 去重判断（早做判断，重复则不抓取内容）
        from sqlalchemy import select
        from app.models.submission import Submission
        from app.models.duplicate_log import DuplicateLog
        from app.services.email_parser import CooperationType
        
        # 1) 严格主题一致：沿用原逻辑
        result = await db.execute(
            select(Submission).where(Submission.email_subject == email_data.subject).limit(1)
        )
        if result.scalar_one_or_none():
            logger.info(f"邮件已处理过（主题一致），跳过: {email_data.subject}")
            return
        
        # 2) 同稿同媒体去重：需 source_unit、media_type、title 可解析
        superseded_id = None  # 若当前邮件胜出并替换，记录被替换的旧稿 ID
        if source_unit and media_type and title:
            # 查询同媒体、同单位的投稿，逐一比对标题
            r = await db.execute(
                select(Submission).where(
                    Submission.media_type == media_type.value if media_type else Submission.media_type,
                    Submission.source_unit == source_unit
                )
            )
            candidates = []
            for s in r.scalars().all():
                existing_title = EmailParser.extract_title_for_dedup(s.email_subject or "")
                if existing_title and existing_title.strip() == title.strip():
                    candidates.append(s)
            
            if candidates:
                def _dedup_score(sub):
                    """优先级：合作>投稿，新稿>旧稿。分数越小越优"""
                    coop_rank = 0 if sub.cooperation_type == "partner" else 1
                    ts = sub.email_date.timestamp() if sub.email_date else 0
                    return (coop_rank, -ts)
                
                best = min(candidates, key=_dedup_score)
                curr_rank = 0 if cooperation == CooperationType.PARTNER else 1
                curr_ts = email_data.date.timestamp() if email_data.date else 0
                curr_score = (curr_rank, -curr_ts)
                best_score = _dedup_score(best)
                
                if curr_score < best_score:
                    # 当前邮件胜出，将处理并替换旧稿
                    superseded_id = best.id
                    logger.info(f"同稿同媒体，当前邮件优于已有稿，将替换: 旧稿ID={best.id}, 主题={email_data.subject}")
                else:
                    # 已有稿胜出，跳过当前邮件，不抓取内容
                    dup_log = DuplicateLog(
                        email_subject=email_data.subject,
                        email_from=email_data.from_addr,
                        email_date=email_data.date,
                        cooperation_type=cooperation.value if cooperation else None,
                        media_type=media_type.value if media_type else None,
                        source_unit=source_unit,
                        title=title,
                        duplicate_type="skipped",
                        effective_submission_id=best.id,
                    )
                    db.add(dup_log)
                    await db.commit()
                    logger.info(f"重复稿件已跳过（不抓取内容）: {email_data.subject} -> 有效稿ID={best.id}")
                    return
        
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
            image_urls = []
            original_html = None  # 保存原始HTML
            attachment_records = []  # 待写入的附件记录（OSS已上传）
            source_url = None
            
            # 根据内容类型处理
            if content_type == ContentType.WEIXIN:
                # 抓取公众号文章
                url = EmailParser.extract_url(email_data.body, ContentType.WEIXIN)
                if url:
                    source_url = url
                    logger.info(f"抓取公众号文章: {url}")
                    fetcher = WebFetcher(
                        wechat302_api_key=wechat302_api_key,
                        wechat302_enabled=use_wechat302,
                        wechat302_base_url=wechat302_base_url or "https://api.302.ai",
                        weixin_cookie=weixin_cookie or "",
                        weixin_proxy_url=weixin_proxy_url or "",
                    )
                    fetched_title, fetched_content, fetched_html, image_urls = await fetcher.fetch_weixin_article_async(url)
                    
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
                    else:
                        # 抓取失败，提供打开链接的按钮
                        logger.warning(f"微信文章抓取失败，提供链接: {url}")
                        content = f"【微信文章抓取失败，请点击下方按钮打开】\n\n文章链接：{url}"
                        original_html = f'''
                        <div style="text-align: center; padding: 60px 20px; background: #f8f9fa; border-radius: 8px;">
                            <div style="font-size: 48px; margin-bottom: 20px;">📱</div>
                            <h3 style="color: #333; margin-bottom: 15px;">微信文章抓取失败</h3>
                            <p style="color: #666; margin-bottom: 30px;">由于微信反爬限制，无法自动抓取内容<br>请点击下方按钮在新窗口打开文章，然后复制内容</p>
                            <a href="{url}" target="_blank" style="display: inline-block; padding: 15px 40px; background: #07c160; color: white; text-decoration: none; border-radius: 6px; font-size: 16px; font-weight: bold;">
                                🔗 打开微信文章
                            </a>
                            <p style="margin-top: 20px; font-size: 12px; color: #999;">提示：打开后请手动复制文章内容到编辑器</p>
                        </div>
                        '''
            
            elif content_type == ContentType.MEIPIAN:
                # 抓取美篇文章
                url = EmailParser.extract_url(email_data.body, ContentType.MEIPIAN)
                if url:
                    source_url = url
                    logger.info(f"抓取美篇文章: {url}")
                    fetcher = WebFetcher(
                        wechat302_api_key=wechat302_api_key,
                        wechat302_enabled=use_wechat302,
                        wechat302_base_url=wechat302_base_url or "https://api.302.ai",
                        weixin_cookie=weixin_cookie or "",
                        weixin_proxy_url=weixin_proxy_url or "",
                    )
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
            
            elif content_type == ContentType.LARGE_ATTACHMENT:
                # 超大附件：提取所有下载链接，由编辑人员手动下载
                import re
                import html as html_module
                
                # 提取所有 QQ 邮箱和网易邮箱的超大附件下载链接
                qq_links = re.findall(r'https://wx\.mail\.qq\.com/ftn/download[^\s<>"\']+', email_data.body)
                netease_links = re.findall(r'https://mail\.163\.com/large-attachment-download/[^\s<>"\']+', email_data.body)
                
                # HTML 解码链接（&amp; -> &）
                qq_links = [html_module.unescape(link) for link in qq_links]
                netease_links = [html_module.unescape(link) for link in netease_links]
                
                # 去重（保持顺序）
                seen = set()
                all_links = []
                for link in qq_links + netease_links:
                    if link not in seen:
                        seen.add(link)
                        all_links.append(link)
                
                if not all_links:
                    logger.warning("未找到超大附件下载链接")
                    content = email_data.body or ""
                    original_html = f'<html><body><pre>{content}</pre></body></html>'
                else:
                    logger.info(f"检测到 {len(all_links)} 个超大附件下载链接")
                    
                    # 尝试提取文件名
                    filenames = []
                    for link in all_links:
                        # 从 title 或链接文本提取文件名
                        title_match = re.search(rf'title="([^"]+)"[^>]*>{re.escape(link)}', email_data.body)
                        if title_match:
                            filenames.append(title_match.group(1).split('\n')[0].strip())
                        else:
                            # 尝试从 URL 参数提取
                            title_param = re.search(r'[?&]title=([^&]+)', link)
                            if title_param:
                                import urllib.parse
                                filenames.append(urllib.parse.unquote(title_param.group(1)))
                            else:
                                filenames.append(f"附件 {len(filenames) + 1}")
                    
                    body_text = (email_data.body or "").strip()
                    
                    # 生成内容摘要
                    content_lines = [f"超大附件 ({len(all_links)} 个)"]
                    for i, (link, filename) in enumerate(zip(all_links, filenames), 1):
                        content_lines.append(f"{i}. {filename}: {link}")
                    content_lines.append(f"\n{body_text}")
                    content = "\n".join(content_lines)
                    
                    # 生成原始内容预览 HTML
                    download_items = []
                    for i, (link, filename) in enumerate(zip(all_links, filenames), 1):
                        download_items.append(
                            f'<div class="download-item">'
                            f'<p class="filename">📎 {i}. {filename}</p>'
                            f'<p><a href="{link}" target="_blank">点击此处进入下载页面</a></p>'
                            f'</div>'
                        )
                    
                    original_html = (
                        '<html><head><meta charset="utf-8">'
                        '<style>body{font-family:sans-serif;padding:20px;} '
                        'a{color:#409eff;font-size:16px;word-break:break-all;} '
                        '.download-section{background:#fff3cd;padding:15px;border-left:4px solid #ffc107;margin:10px 0;} '
                        '.download-item{margin:10px 0;padding:10px;background:#fff;border-radius:4px;} '
                        '.download-item a{color:#e6a23c;font-weight:bold;font-size:16px;} '
                        '.filename{color:#303133;font-size:14px;margin:5px 0;} '
                        'pre{white-space:pre-wrap;word-break:break-all;color:#606266;font-size:13px;}</style></head>'
                        '<body>'
                        '<div class="download-section">'
                        f'<p><strong>⚠️ 超大附件 ({len(all_links)} 个，请点击下载按钮手动下载）：</strong></p>'
                        + ''.join(download_items) +
                        '</div>'
                        f'<hr><p><strong>邮件原文：</strong></p><pre>{body_text}</pre>'
                        '</body></html>'
                    )
            
            elif content_type == ContentType.OTHER_URL:
                # 人工采集模式：只保存链接和邮件原文，不自动抓取网页内容
                url = EmailParser.extract_url(email_data.body, ContentType.OTHER_URL)
                source_url = url
                url_line = f"链接: {url}" if url else ""
                body_text = (email_data.body or "").strip()
                content = "\n\n".join(filter(None, [url_line, body_text])) or url_line or ""

                # 生成原始内容预览 HTML（供审核页左栏展示可点击链接）
                if url:
                    original_html = (
                        '<html><head><meta charset="utf-8">'
                        '<style>body{font-family:sans-serif;padding:20px;} '
                        'a{color:#409eff;font-size:16px;word-break:break-all;} '
                        'pre{white-space:pre-wrap;word-break:break-all;color:#606266;font-size:13px;}</style></head>'
                        f'<body><p><strong>外部链接（请点击打开后手动复制内容）：</strong></p>'
                        f'<p><a href="{url}" target="_blank">{url}</a></p>'
                        f'<hr><p><strong>邮件原文：</strong></p><pre>{body_text}</pre></body></html>'
                    )
            
            # Word 文档处理（包括超大附件下载成功后转换的）
            if content_type == ContentType.WORD:
                # 处理Word文档附件
                logger.info("开始处理Word文档")
                temp_file_path = None
                docx_path_to_clean = None
                word_attachment_images = []
                
                try:
                    logger.info(f"Word附件数量: {len(email_data.attachments)}")
                    for filename, file_data in email_data.attachments:
                        filename_lower = filename.lower()
                        logger.info(f"处理Word附件: {filename}")

                        # 邮件里"Word + 独立图片附件"场景：图片不在 docx 内，需一并入库并插入占位符
                        if any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]):
                            word_attachment_images.append((filename, file_data))
                            logger.info(f"识别到独立图片附件: {filename}")
                            continue

                        # 非 Word 附件在该分支跳过
                        if not filename_lower.endswith(('.doc', '.docx')):
                            logger.info(f"跳过非Word附件: {filename}")
                            continue

                        # 上传原始Word附件到OSS，记录附件
                        try:
                            oss_url, oss_key = oss_service.upload_file(
                                file_data=file_data,
                                filename=filename,
                                folder='attachments'
                            )
                            attachment_records.append({
                                "attachment_type": "word",
                                "oss_url": oss_url,
                                "oss_key": oss_key,
                                "original_filename": filename,
                                "file_size": len(file_data) if file_data else None
                            })
                        except Exception as e:
                            logger.error(f"Word附件上传失败: {filename}, err={e}")

                        # 保存 Word 附件到临时文件
                        temp_file = _tf.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
                        temp_file.write(file_data)
                        temp_file.close()
                        temp_file_path = temp_file.name
                        logger.info(f"Word临时文件已保存: {temp_file_path}")
                        
                        # 处理Word文档
                        if filename_lower.endswith('.doc'):
                            doc_path = temp_file_path
                            # 转换为docx（可能较慢，最多约 120 秒）
                            logger.info("开始将 .doc 转为 .docx")
                            docx_path = doc_processor.convert_doc_to_docx(doc_path)
                            docx_path_to_clean = docx_path
                            logger.info(".doc 转换完成，开始提取标题与正文")
                            # 先提取标题
                            doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                            if doc_title and doc_title != "无标题":
                                title = doc_title
                                logger.info(f"从Word文档提取标题: {title}, 占用{title_lines}行")
                            # 提取文本时跳过标题行
                            content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)
                        
                        elif filename_lower.endswith('.docx'):
                            docx_path = temp_file_path
                            logger.info("开始从 .docx 提取标题与正文")
                            # 先提取标题
                            doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                            if doc_title and doc_title != "无标题":
                                title = doc_title
                                logger.info(f"从Word文档提取标题: {title}, 占用{title_lines}行")
                            # 提取文本时跳过标题行
                            content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)

                    # 提取 Word 内嵌图片（保持 [[IMG_1]] 起始顺序）
                    if docx_path and os.path.exists(docx_path):
                        embedded_images = doc_processor.extract_images_from_docx(docx_path)
                        logger.info(f"从Word文档提取内嵌图片 {len(embedded_images)} 张")
                        images_to_upload.extend(embedded_images)

                    # 将"独立图片附件"追加到内容末尾，占位符从现有最大序号继续
                    if word_attachment_images:
                        import re
                        existing_indexes = [
                            int(x) for x in re.findall(r"\[\[IMG_(\d+)\]\]", content or "")
                        ]
                        next_idx = (max(existing_indexes) if existing_indexes else 0) + 1
                        for filename, file_data in word_attachment_images:
                            content = f"{content}\n\n[[IMG_{next_idx}]]"
                            images_to_upload.append((filename, file_data))
                            next_idx += 1
                        logger.info(f"已追加独立图片附件 {len(word_attachment_images)} 张并写入占位符")

                    # 处理视频附件（文档+视频场景）
                    video_exts = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'}
                    for filename, file_data in email_data.attachments:
                        if any(filename.lower().endswith(ext) for ext in video_exts):
                            logger.info(f"发现视频附件: {filename}, 大小: {len(file_data)/1024/1024:.2f}MB")
                            oss_url, oss_key = oss_service.upload_file(
                                file_data=file_data,
                                filename=filename,
                                folder='videos'
                            )
                            attachment_records.append({
                                "attachment_type": "video",
                                "oss_url": oss_url,
                                "oss_key": oss_key,
                                "original_filename": filename,
                                "file_size": len(file_data) if file_data else None
                            })
                            video_tag = f'<video controls width="100%"><source src="{oss_url}" type="video/mp4"></video>'
                            content = f"{content}\n\n{video_tag}"
                            logger.info(f"视频已上传OSS并追加到内容: {oss_url}")

                except Exception as e:
                    logger.error(f"Word处理异常: {e}", exc_info=True)
                    raise
                finally:
                    # 临时文件清理后移到"Word图片提取并上传"之后，
                    # 否则会导致 docx_path 不存在，图片无法提取，只剩占位符。
                    logger.info(
                        f"暂缓清理Word临时文件: temp_file_path={temp_file_path}, "
                        f"docx_path_to_clean={docx_path_to_clean}"
                    )
            
            elif content_type == ContentType.ARCHIVE:
                # 处理压缩包 - 解压并处理 Word + 图片 + 视频
                import zipfile
                import shutil
                import subprocess

                _video_exts = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'}

                def _extract_archive(file_path: str, filename: str, extract_dir: str):
                    fname_lower = filename.lower()
                    if fname_lower.endswith('.zip'):
                        with zipfile.ZipFile(file_path, 'r') as zip_ref:
                            for member in zip_ref.infolist():
                                target = os.path.realpath(
                                    os.path.join(extract_dir, member.filename)
                                )
                                if not target.startswith(
                                    os.path.realpath(extract_dir) + os.sep
                                ) and target != os.path.realpath(extract_dir):
                                    raise ValueError(f"Zip Slip 检测到恶意路径: {member.filename}")
                            zip_ref.extractall(extract_dir)
                        return

                    # rar/7z: 优先 7z，其次 unrar
                    if shutil.which('7z'):
                        result = subprocess.run(
                            ['7z', 'x', '-y', f'-o{extract_dir}', file_path],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            raise RuntimeError(result.stderr or result.stdout or '7z 解压失败')
                        return
                    if shutil.which('unrar'):
                        result = subprocess.run(
                            ['unrar', 'x', '-o+', file_path, extract_dir],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode != 0:
                            raise RuntimeError(result.stderr or result.stdout or 'unrar 解压失败')
                        return

                    raise RuntimeError('RAR/7Z 解压依赖未安装（需 7z 或 unrar）')

                for filename, file_data in email_data.attachments:
                    fname_lower = filename.lower()

                    if not fname_lower.endswith(('.zip', '.rar', '.7z')):
                        continue

                    logger.info(f"发现压缩包: {filename}, 大小: {len(file_data)/1024/1024:.2f}MB")

                    # 上传原始压缩包到OSS，记录附件
                    try:
                        arc_url, arc_key = oss_service.upload_file(
                            file_data=file_data,
                            filename=filename,
                            folder='attachments'
                        )
                        attachment_records.append({
                            "attachment_type": "archive",
                            "oss_url": arc_url,
                            "oss_key": arc_key,
                            "original_filename": filename,
                            "file_size": len(file_data) if file_data else None
                        })
                    except Exception as e:
                        logger.error(f"压缩包上传失败: {filename}, err={e}")

                    with _tf.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as zip_file:
                        zip_file.write(file_data)
                        zip_path = zip_file.name

                    extract_dir = _tf.mkdtemp()
                    try:
                        _extract_archive(zip_path, filename, extract_dir)
                        logger.info(f"压缩包已解压到: {extract_dir}")

                        # ── 查找并处理 Word 文档 ──
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
                            try:
                                with open(word_file, 'rb') as wf:
                                    word_data = wf.read()
                                w_url, w_key = oss_service.upload_file(
                                    file_data=word_data,
                                    filename=os.path.basename(word_file),
                                    folder='attachments'
                                )
                                attachment_records.append({
                                    "attachment_type": "word",
                                    "oss_url": w_url,
                                    "oss_key": w_key,
                                    "original_filename": os.path.basename(word_file),
                                    "file_size": len(word_data) if word_data else None
                                })
                            except Exception as e:
                                logger.error(f"压缩包内Word上传失败: {word_file}, err={e}")
                            if word_file.lower().endswith('.doc'):
                                docx_path = doc_processor.convert_doc_to_docx(word_file)
                            else:
                                docx_path = word_file

                            doc_title, title_lines = doc_processor.extract_title_from_docx(docx_path)
                            if doc_title and doc_title != "无标题":
                                title = doc_title
                                logger.info(f"从Word文档提取标题: {title}, 占用{title_lines}行")

                            content = doc_processor.extract_text_from_docx(docx_path, skip_title_lines=title_lines)

                            embedded_images = doc_processor.extract_images_from_docx(docx_path)
                            logger.info(f"从Word文档提取{len(embedded_images)}张图片")
                            for img_filename, img_data in embedded_images:
                                images_to_upload.append((img_filename, img_data))
                        else:
                            logger.warning("压缩包中未找到Word文档")
                            content = "压缩包中未找到Word文档"

                        # ── 查找并处理独立图片文件 ──
                        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
                        standalone_images = []
                        for root, dirs, files in os.walk(extract_dir):
                            for file in files:
                                file_ext = '.' + file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                                if file_ext in image_exts:
                                    img_path = os.path.join(root, file)
                                    logger.info(f"压缩包内发现图片: {file}")
                                    with open(img_path, 'rb') as img_f:
                                        img_data = img_f.read()
                                    standalone_images.append((file, img_data))
                        
                        # 将独立图片添加到内容末尾（使用占位符）
                        if standalone_images:
                            # 找到现有占位符的最大序号
                            import re
                            existing_indexes = [
                                int(x) for x in re.findall(r"\[\[IMG_(\d+)\]\]", content or "")
                            ]
                            next_idx = (max(existing_indexes) if existing_indexes else 0) + 1
                            
                            for img_filename, img_data in standalone_images:
                                images_to_upload.append((img_filename, img_data))
                                # 在内容中添加占位符
                                placeholder = f"[[IMG_{next_idx}]]"
                                content = f"{content}\n\n{placeholder}"
                                next_idx += 1
                            logger.info(f"压缩包内添加{len(standalone_images)}张独立图片到内容")

                        # ── 查找并处理视频文件 ──
                        for root, dirs, files in os.walk(extract_dir):
                            for file in files:
                                file_ext = '.' + file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                                if file_ext in _video_exts:
                                    video_path = os.path.join(root, file)
                                    logger.info(f"压缩包内发现视频: {file}")
                                    with open(video_path, 'rb') as vf:
                                        video_data = vf.read()
                                    oss_url, oss_key = oss_service.upload_file(
                                        file_data=video_data,
                                        filename=file,
                                        folder='videos'
                                    )
                                    attachment_records.append({
                                        "attachment_type": "video",
                                        "oss_url": oss_url,
                                        "oss_key": oss_key,
                                        "original_filename": file,
                                        "file_size": len(video_data) if video_data else None
                                    })
                                    video_tag = f'<video controls width="100%"><source src="{oss_url}" type="video/mp4"></video>'
                                    content = f"{content}\n\n{video_tag}"
                                    logger.info(f"压缩包内视频已上传OSS: {oss_url}")

                    finally:
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
                        attachment_records.append({
                            "attachment_type": "video",
                            "oss_url": oss_url,
                            "oss_key": oss_key,
                            "original_filename": filename,
                            "file_size": len(file_data) if file_data else None
                        })
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
            elif content_type == ContentType.OTHER_URL:
                content_source = 'other_url'
            elif content_type == ContentType.LARGE_ATTACHMENT:
                content_source = 'large_attachment'
            elif content_type == ContentType.ARCHIVE:
                # 压缩包
                content_source = 'archive'
            elif content_type == ContentType.VIDEO:
                content_source = 'video'
            elif doc_path:
                content_source = 'doc'
            elif docx_path:
                content_source = 'docx'
            else:
                content_source = 'text'
            
            # 自动创建采编映射（如果发件人包含名称）
            if '<' in email_data.from_addr and '>' in email_data.from_addr:
                # 格式: "姓名 <email@example.com>"
                import re
                match = re.match(r'(.+?)\s*<(.+?)>', email_data.from_addr)
                if match:
                    editor_name = match.group(1).strip()
                    email_addr = match.group(2).strip()
                    
                    # 清理乱码：只保留中文、字母、数字、空格
                    editor_name = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', editor_name).strip()
                    
                    if editor_name:  # 确保清理后不为空
                        # 检查是否已有映射
                        from app.models.editor_name_mapping import EditorNameMapping
                        existing = await db.execute(
                            select(EditorNameMapping).where(EditorNameMapping.email == email_addr).limit(1)
                        )
                        if not existing.scalar_one_or_none():
                            # 创建新映射
                            mapping = EditorNameMapping(email=email_addr, display_name=editor_name)
                            db.add(mapping)
                            await db.commit()
                            logger.info(f"自动创建采编映射: {email_addr} -> {editor_name}")
            
            # 创建投稿记录（保存原始邮件主题用于去重，解析后的标题另存）
            submission = await submission_service.create_submission(
                email_subject=email_data.subject,  # 保存原始邮件主题
                email_from=email_data.from_addr,
                email_date=email_data.date,
                email_raw_content=email_data.body,
                source_url=source_url,
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
                site_id = await EmailParser.get_wordpress_site_id_async(media_type, db) if media_type else None
                
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

            # 写入附件记录（Word/压缩包/视频等）
            if attachment_records:
                for rec in attachment_records:
                    try:
                        await submission_service.add_attachment(
                            submission_id=submission.id,
                            attachment_type=rec.get("attachment_type"),
                            oss_url=rec.get("oss_url"),
                            oss_key=rec.get("oss_key"),
                            original_filename=rec.get("original_filename"),
                            file_size=rec.get("file_size")
                        )
                    except Exception as e:
                        logger.error(f"附件记录写入失败: {rec}, err={e}")
            
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
            
            # Word分支：图片提取完成后再清理临时文件
            if content_type == ContentType.WORD:
                if doc_path and os.path.exists(doc_path):
                    os.unlink(doc_path)
                    logger.info(f"已清理Word临时源文件: {doc_path}")
                if docx_path and os.path.exists(docx_path) and docx_path != doc_path:
                    os.unlink(docx_path)
                    logger.info(f"已清理Word临时docx文件: {docx_path}")
            
            # 创建原文草稿（供编辑人员查看和手动编辑）
            from app.services.draft_service import DraftService
            from app.utils.content_processor import ContentProcessor
            draft_service = DraftService(db)
            
            # 公众号、美篇、OTHER_URL（有原始HTML时）：将HTML转换为Markdown，并插入占位符
            if (content_type in [ContentType.WEIXIN, ContentType.MEIPIAN, ContentType.OTHER_URL] and original_html and oss_urls_ordered):
                import html2text
                from bs4 import BeautifulSoup
                
                soup = BeautifulSoup(original_html, 'html.parser')
                img_tags = soup.find_all('img')
                # 只替换前 N 张（与 oss 顺序一致），避免占位符与 media_map 错位
                for idx, img in enumerate(img_tags, start=1):
                    if idx <= len(oss_urls_ordered):
                        placeholder = f'[[IMG_{idx}]]'
                        img.replace_with(placeholder)
                
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0
                draft_content = h.handle(str(soup))
                if content_type == ContentType.OTHER_URL:
                    logger.info(f"OTHER_URL 已从 HTML 生成带占位符的草稿，图片数: {len(oss_urls_ordered)}")
            else:
                draft_content = content

            # 有图时统一显式构建 media_map，避免占位符与图片错位或丢失
            if oss_urls_ordered:
                import re
                draft_media_map = {
                    f"[[IMG_{idx}]]": oss_url
                    for idx, oss_url in enumerate(oss_urls_ordered, start=1)
                }

                # 先把 Markdown 图片语法替换为占位符
                for idx in range(1, len(oss_urls_ordered) + 1):
                    draft_content = re.sub(
                        rf'!\[图片{idx}\]\([^)]+\)',
                        f'[[IMG_{idx}]]',
                        draft_content or ""
                    )

                # 对公众号/美篇：若正文中未保留占位符，则补到文末，保证编辑器可见
                if content_type in [ContentType.WEIXIN, ContentType.MEIPIAN] and '[[IMG_' not in (draft_content or ''):
                    appended = "\n\n".join(f"[[IMG_{idx}]]" for idx in range(1, len(oss_urls_ordered) + 1))
                    draft_content = f"{(draft_content or '').strip()}\n\n{appended}".strip()
                    logger.info(f"{content_type} 草稿未检测到占位符，已追加 {len(oss_urls_ordered)} 个到文末")

                draft = await draft_service.create_draft(
                    submission_id=submission.id,
                    original_content_md=draft_content,
                    ai_content_md=draft_content,
                    media_map=draft_media_map
                )
            else:
                draft = await draft_service.create_draft(
                    submission_id=submission.id,
                    transformed_content=draft_content
                )
            logger.info(f"已创建原文草稿: draft_id={draft.id}, content_type={content_type}")
            
            # 更新状态为completed
            await submission_service.update_status(submission.id, 'completed')
            
            # 若为替换稿，记录被替换的旧稿到 duplicate_logs
            if superseded_id:
                dup_log = DuplicateLog(
                    email_subject=email_data.subject,
                    email_from=email_data.from_addr,
                    email_date=email_data.date,
                    cooperation_type=cooperation.value if cooperation else None,
                    media_type=media_type.value if media_type else None,
                    source_unit=source_unit,
                    title=title,
                    duplicate_type="superseded",
                    effective_submission_id=submission.id,
                    superseded_submission_id=superseded_id,
                )
                db.add(dup_log)
                await db.commit()
                logger.info(f"已记录替换关系: 旧稿ID={superseded_id} -> 新稿ID={submission.id}")
            
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
