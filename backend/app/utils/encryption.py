"""
加密工具函数
使用独立的 ENCRYPTION_KEY 进行 Fernet 加解密，与 JWT 签名密钥完全分离。
"""
import logging
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    从独立的 ENCRYPTION_KEY 获取 Fernet 密钥。
    ENCRYPTION_KEY 必须是 url-safe base64 编码的 32 字节密钥。
    """
    return settings.ENCRYPTION_KEY.encode()


def encrypt_value(value: str) -> str:
    """加密字符串值"""
    if not value:
        return value
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """
    解密字符串值。
    解密失败时抛出异常，不再静默返回密文。
    """
    if not encrypted_value:
        return encrypted_value
    try:
        fernet = Fernet(get_encryption_key())
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except (InvalidToken, Exception) as e:
        logger.error(f"解密失败: {type(e).__name__}")
        raise ValueError("数据解密失败，请检查 ENCRYPTION_KEY 是否正确") from e
