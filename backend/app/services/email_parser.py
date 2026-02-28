"""
邮件解析服务
解析邮件标题和内容，提取媒体类型、来稿单位等信息
"""
import re
from typing import Optional, Tuple
from enum import Enum


class MediaType(str, Enum):
    """媒体类型"""
    RONGYAO = "rongyao"  # 荣耀网
    SHIDAI = "shidai"    # 时代网
    ZHENGXIAN = "zhengxian"  # 争先网
    ZHENGQI = "zhengqi"  # 政企网
    TOUTIAO = "toutiao"  # 今日头条


class CooperationType(str, Enum):
    """合作方式"""
    FREE = "free"  # 投：免费投稿
    PARTNER = "partner"  # 合：合作客户


class ContentType(str, Enum):
    """内容类型"""
    WEIXIN = "weixin"  # 公众号链接
    MEIPIAN = "meipian"  # 美篇链接
    OTHER_URL = "other_url"  # 其他网页链接（非公众号/美篇）
    LARGE_ATTACHMENT = "large_attachment"  # 超大附件
    WORD = "word"  # Word文档
    VIDEO = "video"  # 视频
    ARCHIVE = "archive"  # 压缩包


class EmailParser:
    """邮件解析器"""
    
    # 媒体标识映射
    MEDIA_MAPPING = {
        "荣": MediaType.RONGYAO,
        "时": MediaType.SHIDAI,
        "争": MediaType.ZHENGXIAN,
        "优": MediaType.ZHENGXIAN,
        "政": MediaType.ZHENGQI,
        "头": MediaType.TOUTIAO,
    }
    
    # 合作方式映射
    COOPERATION_MAPPING = {
        "投": CooperationType.FREE,
        "合": CooperationType.PARTNER,
    }
    
    @classmethod
    def parse_subject(cls, subject: str) -> Tuple[Optional[CooperationType], Optional[MediaType], Optional[str], Optional[str]]:
        """
        解析邮件标题
        
        格式：[合作方式]+[对应媒体]+[来稿单位名称]+[标题]
        例如：投，时，凤翔区人社局，春风迎归人 人社暖民心
        
        Args:
            subject: 邮件标题
            
        Returns:
            (合作方式, 媒体类型, 来稿单位, 标题)
        """
        # 移除"转发："前缀
        subject = re.sub(r'^转发[：:]\s*', '', subject)
        
        # 按逗号或顿号分割（最多4段：合作方式、媒体、来稿单位、标题）
        parts = re.split(r'[，,、]', subject, maxsplit=3)
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) < 3:
            return None, None, None, subject
        
        cooperation_str = parts[0]
        media_str = parts[1]
        source_unit = parts[2]
        title = parts[3].strip() if len(parts) >= 4 else subject
        
        # 映射合作方式
        cooperation = cls.COOPERATION_MAPPING.get(cooperation_str)
        
        # 映射媒体类型
        media = cls.MEDIA_MAPPING.get(media_str)
        
        return cooperation, media, source_unit, title

    @classmethod
    def extract_title_for_dedup(cls, subject: str) -> str:
        """
        从邮件主题提取用于去重匹配的标题
        与 parse_subject 的 title 规则一致：4 段时取第 4 段，否则取全文
        """
        subject = re.sub(r'^转发[：:]\s*', '', subject)
        parts = re.split(r'[，,、]', subject, maxsplit=3)
        parts = [p.strip() for p in parts if p.strip()]
        if len(parts) >= 4:
            return parts[3].strip()
        return subject.strip() if subject else ""
    
    # 图片扩展名
    IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    # 视频扩展名
    VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'}
    # 压缩包扩展名
    ARCHIVE_EXTS = {'.zip', '.rar', '.7z'}

    @classmethod
    def detect_content_type(cls, content: str, attachments: list) -> ContentType:
        """
        检测内容类型

        优先级（高→低）：
          1. 压缩包附件                → ARCHIVE
          2. 超大附件下载链接           → LARGE_ATTACHMENT
          3. 正文含公众号链接           → WEIXIN
          4. 正文含美篇链接             → MEIPIAN
          5. 正文含其他 http(s) 链接    → OTHER_URL
          6. Word 附件（含同时有视频/图片）→ WORD
          7. 纯视频附件（无 Word）      → VIDEO
          8. 纯图片附件（无 Word/视频） → WORD（正文即文章，图片为配图）
          9. 其他                      → WORD（默认）

        Args:
            content: 邮件正文
            attachments: 附件列表 [(filename, data), ...]

        Returns:
            内容类型
        """
        # 最高优先级：压缩包附件
        if attachments:
            for filename, _ in attachments:
                ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
                if ext in cls.ARCHIVE_EXTS:
                    return ContentType.ARCHIVE

        # 检测超大附件下载链接（QQ邮箱和网易邮箱）
        if 'wx.mail.qq.com/ftn/download' in content or 'mail.163.com/large-attachment-download' in content:
            return ContentType.LARGE_ATTACHMENT

        # 检测正文中的链接
        if 'mp.weixin.qq.com' in content:
            return ContentType.WEIXIN

        if 'meipian.cn' in content:
            return ContentType.MEIPIAN

        first_url = re.search(r'https?://[^\s<>"]+', content)
        if first_url:
            url_str = first_url.group(0)
            # 排除邮件内部链接（图标、名片等）
            excluded_patterns = [
                'icon_att.gif', 'images/icon', '/icons/',
                'readmail_businesscard',  # 邮箱名片
                'get_mailhead_icon'  # 邮箱头像
            ]
            if any(x in url_str for x in excluded_patterns):
                pass  # 忽略邮件内部链接
            elif 'mp.weixin.qq.com' not in url_str and 'meipian.cn' not in url_str:
                return ContentType.OTHER_URL

        # 最后检测其他附件
        if attachments:
            has_word = False
            has_video = False
            has_image = False
            for filename, _ in attachments:
                ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

                if ext in cls.VIDEO_EXTS:
                    has_video = True
                elif filename.lower().endswith(('.doc', '.docx')):
                    has_word = True
                elif ext in cls.IMAGE_EXTS:
                    has_image = True

            # Word 附件优先（可同时携带视频/图片）
            if has_word:
                return ContentType.WORD

            # 纯视频（无 Word 附件）
            if has_video:
                return ContentType.VIDEO

            # 纯图片附件（正文即文章内容，图片为配图）→ 归入 WORD 处理流程
            if has_image:
                return ContentType.WORD

        return ContentType.WORD  # 默认：邮件正文即文章内容
    
    @classmethod
    def extract_url(cls, content: str, url_type: ContentType) -> Optional[str]:
        """
        从内容中提取URL
        
        Args:
            content: 邮件正文
            url_type: URL类型
            
        Returns:
            提取的URL或None
        """
        import html
        
        if url_type == ContentType.WEIXIN:
            # 提取公众号链接
            match = re.search(r'https?://mp\.weixin\.qq\.com/s/[^\s<>"]+', content)
            if match:
                url = match.group(0)
                # 解码 HTML 实体（如 &amp; -> &）
                return html.unescape(url)
        
        elif url_type == ContentType.MEIPIAN:
            # 提取美篇链接
            match = re.search(r'https?://(?:www\.)?meipian\.cn/[^\s<>"]+', content)
            if match:
                url = match.group(0)
                # 解码 HTML 实体（如 &amp; -> &）
                return html.unescape(url)
        
        elif url_type == ContentType.OTHER_URL:
            # 提取通用URL（排除已知类型）
            match = re.search(r'https?://[^\s<>"]+', content)
            if match:
                url = match.group(0)
                # 排除公众号和美篇链接
                if 'mp.weixin.qq.com' not in url and 'meipian.cn' not in url:
                    # 解码 HTML 实体（如 &amp; -> &）
                    return html.unescape(url)
        
        return None
    
    @classmethod
    @classmethod
    async def get_wordpress_site_id_async(cls, media_type: MediaType, db) -> Optional[int]:
        """
        根据媒体类型从数据库获取WordPress站点ID
        
        Args:
            media_type: 媒体类型
            db: 数据库会话
            
        Returns:
            站点ID或None
        """
        from sqlalchemy import select
        from app.models.media_site_mapping import MediaSiteMapping
        
        result = await db.execute(
            select(MediaSiteMapping).where(
                MediaSiteMapping.media_type == media_type.value
            )
        )
        mapping = result.scalar_one_or_none()
        return mapping.site_id if mapping else None
    
    @classmethod
    def get_wordpress_site_id(cls, media_type: MediaType) -> Optional[int]:
        """
        根据媒体类型获取WordPress站点ID（同步版本，使用默认映射）
        
        Args:
            media_type: 媒体类型
            
        Returns:
            站点ID或None（今日头条返回None）
        """
        # 默认映射（用于向后兼容）
        mapping = {
            MediaType.RONGYAO: 7,    # 荣耀网 - 站点A
            MediaType.SHIDAI: 8,     # 时代网 - 站点B
            MediaType.ZHENGXIAN: 9,  # 争先网 - 站点C
            MediaType.ZHENGQI: 10,   # 政企网 - 站点D
            MediaType.TOUTIAO: None, # 今日头条 - 手动发布
        }
        return mapping.get(media_type)
