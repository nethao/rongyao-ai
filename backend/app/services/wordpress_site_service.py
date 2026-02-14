"""
WordPress站点管理服务
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.wordpress_site import WordPressSite
from app.schemas.wordpress import WordPressSiteCreate, WordPressSiteUpdate
from app.utils.encryption import encrypt_value, decrypt_value


class WordPressSiteService:
    """WordPress站点管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_site(self, site_data: WordPressSiteCreate) -> WordPressSite:
        """
        创建WordPress站点
        
        Args:
            site_data: 站点数据
            
        Returns:
            创建的站点对象
        """
        # 加密API密码
        api_password_encrypted = None
        if site_data.api_password:
            api_password_encrypted = encrypt_value(site_data.api_password)

        site = WordPressSite(
            name=site_data.name,
            url=site_data.url,
            api_username=site_data.api_username,
            api_password_encrypted=api_password_encrypted,
            active=site_data.active
        )

        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)

        return site

    async def get_site(self, site_id: int) -> Optional[WordPressSite]:
        """
        获取站点详情
        
        Args:
            site_id: 站点ID
            
        Returns:
            站点对象或None
        """
        result = await self.db.execute(
            select(WordPressSite).where(WordPressSite.id == site_id)
        )
        return result.scalar_one_or_none()

    async def list_sites(self, active_only: bool = False) -> List[WordPressSite]:
        """
        获取站点列表
        
        Args:
            active_only: 是否只返回激活的站点
            
        Returns:
            站点列表
        """
        query = select(WordPressSite)
        if active_only:
            query = query.where(WordPressSite.active == True)
        
        query = query.order_by(WordPressSite.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_site(self, site_id: int, site_data: WordPressSiteUpdate) -> Optional[WordPressSite]:
        """
        更新站点信息
        
        Args:
            site_id: 站点ID
            site_data: 更新数据
            
        Returns:
            更新后的站点对象或None
        """
        site = await self.get_site(site_id)
        if not site:
            return None

        # 更新字段
        if site_data.name is not None:
            site.name = site_data.name
        if site_data.url is not None:
            site.url = site_data.url
        if site_data.api_username is not None:
            site.api_username = site_data.api_username
        if site_data.api_password is not None:
            site.api_password_encrypted = encrypt_value(site_data.api_password)
        if site_data.active is not None:
            site.active = site_data.active

        await self.db.commit()
        await self.db.refresh(site)

        return site

    async def delete_site(self, site_id: int) -> bool:
        """
        删除站点
        
        Args:
            site_id: 站点ID
            
        Returns:
            是否删除成功
        """
        site = await self.get_site(site_id)
        if not site:
            return False

        await self.db.delete(site)
        await self.db.commit()

        return True

    def get_decrypted_password(self, site: WordPressSite) -> Optional[str]:
        """
        获取解密后的API密码
        
        Args:
            site: 站点对象
            
        Returns:
            解密后的密码或None
        """
        if not site.api_password_encrypted:
            return None
        
        return decrypt_value(site.api_password_encrypted)
