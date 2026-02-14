"""
加密工具函数
"""
from cryptography.fernet import Fernet
from app.config import settings
import base64
import hashlib


def get_encryption_key() -> bytes:
    """
    从JWT密钥派生加密密钥
    """
    # 使用JWT密钥生成32字节的密钥
    key = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value: str) -> str:
    """
    加密字符串值
    """
    if not value:
        return value
    
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """
    解密字符串值
    """
    if not encrypted_value:
        return encrypted_value
    
    try:
        fernet = Fernet(get_encryption_key())
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception:
        # 解密失败返回原值
        return encrypted_value
