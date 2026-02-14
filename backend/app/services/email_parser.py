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
    WORD = "word"  # Word文档
    VIDEO = "video"  # 视频


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
        
        # 按逗号或顿号分割
        parts = re.split(r'[，,、]', subject, maxsplit=3)
        
        if len(parts) < 4:
            return None, None, None, subject
        
        cooperation_str = parts[0].strip()
        media_str = parts[1].strip()
        source_unit = parts[2].strip()
        title = parts[3].strip()
        
        # 映射合作方式
        cooperation = cls.COOPERATION_MAPPING.get(cooperation_str)
        
        # 映射媒体类型
        media = cls.MEDIA_MAPPING.get(media_str)
        
        return cooperation, media, source_unit, title
    
    @classmethod
    def detect_content_type(cls, content: str, attachments: list) -> ContentType:
        """
        检测内容类型
        
        Args:
            content: 邮件正文
            attachments: 附件列表 [(filename, data), ...]
            
        Returns:
            内容类型
        """
        # 检查公众号链接
        if 'mp.weixin.qq.com' in content:
            return ContentType.WEIXIN
        
        # 检查美篇链接
        if 'meipian.cn' in content:
            return ContentType.MEIPIAN
        
        # 检查附件
        if attachments:
            for filename, _ in attachments:
                filename_lower = filename.lower()
                
                # 视频文件
                if any(filename_lower.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']):
                    return ContentType.VIDEO
                
                # Word文档
                if filename_lower.endswith(('.doc', '.docx')):
                    return ContentType.WORD
        
        return ContentType.WORD  # 默认为文档类型
    
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
        if url_type == ContentType.WEIXIN:
            # 提取公众号链接
            match = re.search(r'https?://mp\.weixin\.qq\.com/s/[^\s<>"]+', content)
            if match:
                return match.group(0)
        
        elif url_type == ContentType.MEIPIAN:
            # 提取美篇链接
            match = re.search(r'https?://(?:www\.)?meipian\.cn/[^\s<>"]+', content)
            if match:
                return match.group(0)
        
        return None
    
    @classmethod
    def get_wordpress_site_id(cls, media_type: MediaType) -> Optional[int]:
        """
        根据媒体类型获取WordPress站点ID
        
        Args:
            media_type: 媒体类型
            
        Returns:
            站点ID或None（今日头条返回None）
        """
        mapping = {
            MediaType.RONGYAO: 7,    # 荣耀网 - 站点A
            MediaType.SHIDAI: 8,     # 时代网 - 站点B
            MediaType.ZHENGXIAN: 9,  # 争先网 - 站点C
            MediaType.ZHENGQI: 10,   # 政企网 - 站点D
            MediaType.TOUTIAO: None, # 今日头条 - 手动发布
        }
        return mapping.get(media_type)
