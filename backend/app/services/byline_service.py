"""
署名服务：责编（采编）、文编 名称解析
"""
import re
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.editor_name_mapping import EditorNameMapping
from app.models.copy_editor_site_mapping import CopyEditorSiteMapping
from app.models.user import User

logger = logging.getLogger(__name__)


def _extract_email(addr: str) -> str:
    """从发件人字符串提取纯邮箱地址"""
    if not addr or not addr.strip():
        return ""
    s = addr.strip()
    # 匹配 <email@domain.com> 格式
    m = re.search(r"<([^>]+@[^>]+)>", s)
    if m:
        return m.group(1).strip().lower()
    # 整个字符串像邮箱则直接返回
    if "@" in s and " " not in s:
        return s.lower()
    return s.lower()


class BylineService:
    """署名名称解析"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_editor_display_name(self, email: Optional[str]) -> Optional[str]:
        """
        根据邮箱获取采编姓名（用于 责编 署名）
        支持 "Name <email>" 格式，先精确匹配再前缀匹配
        """
        if not email or not str(email).strip():
            return None
        email = _extract_email(str(email))
        if not email:
            return None
        # 精确匹配
        r = await self.db.execute(
            select(EditorNameMapping.display_name).where(
                EditorNameMapping.email == email
            ).limit(1)
        )
        row = r.scalar_one_or_none()
        if row:
            return row
        # 前缀匹配：如 user@qq.com -> 查 "user"
        if "@" in email:
            prefix = email.split("@")[0]
            r = await self.db.execute(
                select(EditorNameMapping.display_name).where(
                    EditorNameMapping.email == prefix
                ).limit(1)
            )
            row = r.scalar_one_or_none()
            if row:
                return row
        return None

    async def get_copy_editor_display_name(
        self, user_id: int, site_id: int
    ) -> Optional[str]:
        """
        获取用户在指定站点下的文编署名
        若未配置映射，则用用户的 display_name 或 username
        """
        if not user_id or site_id is None:
            logger.warning("文编署名: user_id 或 site_id 为空, user_id=%s site_id=%s", user_id, site_id)
            return None
        uid, sid = int(user_id), int(site_id)
        r = await self.db.execute(
            select(CopyEditorSiteMapping.display_name).where(
                CopyEditorSiteMapping.user_id == uid,
                CopyEditorSiteMapping.site_id == sid,
            ).limit(1)
        )
        name = r.scalars().one_or_none()
        if name and str(name).strip():
            logger.info("文编署名: user_id=%s site_id=%s -> %s", uid, sid, name)
            return str(name).strip()
        # 回退：用户 display_name 或 username
        r = await self.db.execute(select(User).where(User.id == uid).limit(1))
        user = r.scalar_one_or_none()
        fallback = None
        if user:
            fallback = (user.display_name and user.display_name.strip()) or user.username
        logger.warning(
            "文编署名: 未找到映射 user_id=%s site_id=%s，使用回退=%s。请在个人中心为该站点配置文编署名。",
            uid, sid, fallback
        )
        return fallback

    @staticmethod
    def append_bylines(content_html: str, editor_name: Optional[str], copy_editor_name: Optional[str]) -> str:
        """在正文末尾追加 责编、文编 署名（HTML 段落）"""
        parts = []
        if editor_name:
            parts.append(f"<p>责编：{editor_name}</p>")
        if copy_editor_name:
            parts.append(f"<p>文编：{copy_editor_name}</p>")
        if not parts:
            return content_html
        return content_html.rstrip() + "\n" + "\n".join(parts)
