"""
配置管理服务
"""
import logging
import socket
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.system_config import SystemConfig
from app.utils.encryption import encrypt_value, decrypt_value

# QQ IMAP DNS 解析问题 workaround：强制使用可用 IP
# 必须在导入 imap_tools 之前 patch
_IMAP_HOST_OVERRIDE = {
    'imap.qq.com': '183.47.101.192',
}

_original_getaddrinfo = socket.getaddrinfo

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """修复 QQ IMAP DNS 解析到不可用 IP 的问题"""
    if host in _IMAP_HOST_OVERRIDE:
        override_ip = _IMAP_HOST_OVERRIDE[host]
        logger = logging.getLogger(__name__)
        logger.debug(f"DNS override: {host} -> {override_ip}")
        # 返回 IPv4 地址
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (override_ip, port))]
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _patched_getaddrinfo


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
        api_key = await self.get_config("OPENAI_API_KEY", decrypt=True)
        if not api_key:
            return False
        
        # 获取可选的自定义端点和模型
        base_url = await self.get_config("OPENAI_BASE_URL")
        model = await self.get_config("OPENAI_MODEL")
        
        # 实际验证API密钥有效性
        try:
            from app.services.llm_service import LLMService
            llm_service = LLMService(
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            is_valid = await llm_service.verify_connection()
            await llm_service.close()
            return is_valid
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"LLM config verification failed: {e}")
            return False
    
    async def verify_oss_config(self) -> bool:
        """验证OSS配置"""
        access_key = await self.get_config("OSS_ACCESS_KEY_ID", decrypt=True)
        secret_key = await self.get_config("OSS_ACCESS_KEY_SECRET", decrypt=True)
        endpoint = await self.get_config("OSS_ENDPOINT")
        bucket = await self.get_config("OSS_BUCKET_NAME")
        
        if not all([access_key, secret_key, endpoint, bucket]):
            return False
        
        # 实际验证OSS连接
        try:
            import oss2
            auth = oss2.Auth(access_key, secret_key)
            bucket_obj = oss2.Bucket(auth, endpoint, bucket)
            
            # 尝试列举bucket（只获取1个对象来测试连接）
            result = bucket_obj.list_objects(max_keys=1)
            # 访问result的属性来触发实际请求
            _ = result.object_list
            return True
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"OSS config verification failed: {e}")
            return False

    async def verify_wechat302_config(self) -> Tuple[bool, str]:
        """验证 302 微信抓取配置"""
        api_key = await self.get_config("WECHAT302_API_KEY", decrypt=True)
        enabled = await self.get_config("WECHAT302_ENABLED")
        base_url = await self.get_config("WECHAT302_BASE_URL")
        import requests

        enabled_bool = str(enabled or "true").strip().lower() not in {"false", "0", "no", "off"}
        if not enabled_bool:
            return True, "302 微信抓取已禁用"

        if not api_key:
            return False, "302 验证失败：缺少 API Key"

        base = (base_url or "https://api.302.ai").rstrip("/")
        endpoint = f"{base}/tools/wechat_mp/web/fetch_mp_article_detail_json"
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"url": "https://mp.weixin.qq.com/s/aH8IiY_gwmqOHlq9yxErZw"}

        try:
            resp = requests.get(endpoint, params=params, headers=headers, timeout=20)
            if resp.status_code >= 400:
                return False, f"302 验证失败：HTTP {resp.status_code}"
            data = resp.json() if resp.content else {}
            if not isinstance(data, dict) or "code" not in data:
                return False, "302 验证失败：响应格式异常"
            return True, "302 配置有效"
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"302 config verification failed: {e}")
            return False, f"302 验证失败：{str(e)}"
    
    async def verify_imap_config(self) -> Tuple[bool, str]:
        """验证IMAP配置，返回 (是否有效, 提示信息)"""
        host = await self.get_config("IMAP_HOST")
        port = await self.get_config("IMAP_PORT")
        user = await self.get_config("IMAP_USER")
        password = await self.get_config("IMAP_PASSWORD", decrypt=True)
        use_ssl = await self.get_config("IMAP_USE_SSL")
        timeout_seconds = await self.get_config("IMAP_TIMEOUT_SECONDS")
        
        host = (host or "").strip()
        user = (user or "").strip()
        if not host:
            return False, "请填写 IMAP 服务器地址"
        if not user:
            return False, "请填写 IMAP 用户名（邮箱）"
        if not password:
            return False, "请填写 IMAP 密码或授权码"
        
        port_int = int(port) if port else 993
        timeout_int = int(timeout_seconds) if timeout_seconds else 20
        use_ssl_bool = str(use_ssl).strip().lower() not in {"false", "0", "no", "off"}
        # 先尝试解析域名，区分「填错地址」和「环境 DNS 问题」
        import socket
        try:
            socket.gethostbyname(host)
        except (socket.gaierror, OSError) as e:
            err = str(e).strip()
            return False, (
                f"无法解析 IMAP 服务器地址「{host}」。若您确认地址无误（如 imap.qq.com、imap.163.com），"
                "多半是当前运行环境（Docker 容器）无法访问外网 DNS。请在宿主机为 Docker 配置 DNS："
                "编辑 /etc/docker/daemon.json 添加 \"dns\": [\"8.8.8.8\", \"114.114.114.114\"]，然后 sudo systemctl restart docker，"
                "再重建并启动 backend 与 celery_worker 容器。详见部署文档「IMAP 连接失败」故障排查。"
            )
        try:
            from imap_tools import MailBox, MailBoxUnencrypted

            mailbox_cls = MailBox if use_ssl_bool else MailBoxUnencrypted
            with mailbox_cls(host, port_int, timeout=timeout_int).login(
                user, password, initial_folder="INBOX"
            ):
                pass
            return True, "IMAP 配置有效，连接成功"
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"IMAP config verification failed: {e}")
            err = str(e).strip() or type(e).__name__
            err_lower = err.lower()
            if "name resolution" in err.lower() or "errno -3" in err.lower() or "nodename nor servname" in err.lower():
                return False, (
                    f"无法解析 IMAP 服务器地址「{host}」。若您确认地址无误，请在宿主机为 Docker 配置 DNS"
                    "（/etc/docker/daemon.json 添加 \"dns\": [\"8.8.8.8\", \"114.114.114.114\"] 后重启 Docker），"
                    "再重建 backend/celery_worker 容器。详见部署文档。"
                )
            if isinstance(e, (TimeoutError, socket.timeout)) or "timed out" in err_lower or "timeout" in err_lower:
                return False, (
                    f"IMAP 连接超时（{timeout_int}秒）。请检查服务器地址/端口、SSL设置、"
                    "防火墙放行（常见 993）以及服务器到 IMAP 服务的网络连通性。"
                )
            if (
                "authentication" in err_lower
                or "login failed" in err_lower
                or "invalid credentials" in err_lower
                or "auth" in err_lower
            ):
                return False, "IMAP 认证失败：请检查邮箱账号、密码/授权码，以及是否开启 IMAP 服务。"
            return False, f"IMAP 连接失败：{err}"
