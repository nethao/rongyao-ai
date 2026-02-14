"""
发布服务 - 处理草稿发布到WordPress
"""
import re
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.draft import Draft
from app.models.submission import Submission
from app.models.wordpress_site import WordPressSite
from app.services.wordpress_site_service import WordPressSiteService
from app.services.wordpress_service import WordPressService


class PublishService:
    """发布服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.site_service = WordPressSiteService(db)

    def replace_image_urls(self, content: str, submission: Submission) -> str:
        """
        替换内容中的图片引用为OSS URL
        
        Args:
            content: 原始内容
            submission: 投稿对象（包含图片信息）
            
        Returns:
            替换后的内容
        """
        if not submission.images:
            return content
        
        # 创建图片文件名到OSS URL的映射
        image_map = {}
        for img in submission.images:
            if img.original_filename:
                image_map[img.original_filename] = img.oss_url
        
        # 替换内容中的图片引用
        # 匹配 <img src="..." /> 或 ![](...)
        def replace_img_src(match):
            full_match = match.group(0)
            src = match.group(1)
            
            # 检查是否是本地文件名
            for filename, oss_url in image_map.items():
                if filename in src:
                    return full_match.replace(src, oss_url)
            
            return full_match
        
        # HTML img标签
        content = re.sub(
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
            replace_img_src,
            content
        )
        
        # Markdown图片
        content = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            lambda m: f'![{m.group(1)}]({image_map.get(m.group(2), m.group(2))})',
            content
        )
        
        return content

    async def publish_draft(
        self,
        draft_id: int,
        site_id: int,
        status: str = "publish"
    ) -> tuple[bool, Optional[int], Optional[str], Optional[str]]:
        """
        发布草稿到WordPress站点
        
        Args:
            draft_id: 草稿ID
            site_id: 目标站点ID
            status: 发布状态 ('draft', 'publish', 'pending')
            
        Returns:
            (是否成功, WordPress文章ID, 错误信息, 站点名称)
        """
        # 获取草稿
        result = await self.db.execute(
            select(Draft).where(Draft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        
        if not draft:
            return False, None, "草稿不存在", None
        
        # 检查是否已发布
        if draft.status == "published":
            return False, None, "草稿已发布", None
        
        # 获取投稿信息
        result = await self.db.execute(
            select(Submission).where(Submission.id == draft.submission_id)
        )
        submission = result.scalar_one_or_none()
        
        if not submission:
            return False, None, "关联的投稿不存在", None
        
        # 获取站点信息
        site = await self.site_service.get_site(site_id)
        if not site:
            return False, None, "站点不存在", None
        
        if not site.active:
            return False, None, "站点未激活", site.name
        
        # 获取解密后的密码
        api_password = self.site_service.get_decrypted_password(site)
        if not api_password:
            return False, None, "站点未配置API密码", site.name
        
        # 替换图片URL
        content_with_images = self.replace_image_urls(draft.current_content, submission)
        
        # 生成标题（使用邮件主题或默认标题）
        title = submission.email_subject or "未命名文章"
        
        # 发布到WordPress
        wp_service = WordPressService(site, api_password)
        success, post_id, error_msg = await wp_service.create_post(
            title=title,
            content=content_with_images,
            status=status
        )
        
        if success:
            # 更新草稿状态
            draft.status = "published"
            draft.published_at = datetime.utcnow()
            draft.published_to_site_id = site_id
            draft.wordpress_post_id = post_id
            
            await self.db.commit()
            await self.db.refresh(draft)
            
            return True, post_id, None, site.name
        else:
            return False, None, error_msg, site.name

    async def get_published_info(self, draft_id: int) -> Optional[dict]:
        """
        获取草稿的发布信息
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            发布信息字典或None
        """
        result = await self.db.execute(
            select(Draft).where(Draft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        
        if not draft or draft.status != "published":
            return None
        
        site = None
        if draft.published_to_site_id:
            site = await self.site_service.get_site(draft.published_to_site_id)
        
        return {
            "published_at": draft.published_at,
            "wordpress_post_id": draft.wordpress_post_id,
            "site_name": site.name if site else None,
            "site_url": site.url if site else None
        }
