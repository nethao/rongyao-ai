"""
配置管理服务
"""
import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_config import SystemConfig
from app.utils.encryption import encrypt_value, decrypt_value


class ConfigService:
    """系统配置管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def set_config(
        self,
        key: str,
        value: str,
        encrypted: bool = False,
        description: Optional[str] = None
    ) -> SystemConfig:
        """
        设置配置项
        
        Args:
            key: 配置键
            value: 配置值
            encrypted: 是否加密存储
            description: 配置描述
        
        Returns:
            SystemConfig: 配置对象
        """
        # 如果需要加密，先加密值
        stored_value = encrypt_value(value) if encrypted else value
        
        # 查找现有配置
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        
        if config:
            # 更新现有配置
            config.config_value = stored_value
            config.encrypted = encrypted
            if description:
                config.description = description
        else:
            # 创建新配置
            config = SystemConfig(
                config_key=key,
                config_value=stored_value,
                encrypted=encrypted,
                description=description
            )
            self.db.add(config)
        
        await self.db.commit()
        await self.db.refresh(config)
        return config
    
    async def get_config(
        self,
        key: str,
        decrypt: bool = False
    ) -> Optional[str]:
        """
        获取配置项
        
        Args:
            key: 配置键
            decrypt: 是否解密（如果配置是加密的）
        
        Returns:
            Optional[str]: 配置值，不存在返回None
        """
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return None
        
        value = config.config_value
        
        # 如果配置是加密的且需要解密
        if config.encrypted and decrypt and value:
            value = decrypt_value(value)
        
        return value
    
    async def delete_config(self, key: str) -> bool:
        """
        删除配置项
        
        Args:
            key: 配置键
        
        Returns:
            bool: 是否删除成功
        """
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        
        if config:
            await self.db.delete(config)
            await self.db.commit()
            return True
        
        return False
    
    async def get_all_configs(self, include_encrypted: bool = False) -> dict:
        """
        获取所有配置
        
        Args:
            include_encrypted: 是否包含加密配置的值
        
        Returns:
            dict: 配置字典
        """
        result = await self.db.execute(select(SystemConfig))
        configs = result.scalars().all()
        
        config_dict = {}
        for config in configs:
            if config.encrypted and not include_encrypted:
                config_dict[config.config_key] = "***encrypted***"
            else:
                config_dict[config.config_key] = config.config_value
        
        return config_dict
    
    async def verify_llm_config(self) -> bool:
        """
        验证LLM配置
        
        Returns:
            bool: 配置是否有效
        """
        api_key = await self.get_config("openai_api_key", decrypt=True)
        if not api_key:
            return False
        
        # 实际验证API密钥有效性
        try:
            from app.services.llm_service import LLMService
            llm_service = LLMService(api_key=api_key)
            is_valid = await llm_service.verify_connection()
            await llm_service.close()
            return is_valid
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"LLM config verification failed: {e}")
            return False
    
    async def verify_oss_config(self) -> bool:
        """验证OSS配置"""
        access_key = await self.get_config("oss_access_key_id", decrypt=True)
        secret_key = await self.get_config("oss_access_key_secret", decrypt=True)
        endpoint = await self.get_config("oss_endpoint")
        bucket = await self.get_config("oss_bucket_name")
        
        if not all([access_key, secret_key, endpoint, bucket]):
            return False
        
        # TODO: 实际验证OSS连接
        return True
    
    async def verify_imap_config(self) -> bool:
        """验证IMAP配置"""
        host = await self.get_config("imap_host")
        user = await self.get_config("imap_user")
        password = await self.get_config("imap_password", decrypt=True)
        
        if not all([host, user, password]):
            return False
        
        # TODO: 实际验证IMAP连接
        return True
