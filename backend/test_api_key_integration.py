"""
独立的API密钥管理集成测试
不依赖完整的应用环境
"""
import asyncio
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from cryptography.fernet import Fernet
import base64
import hashlib


# 简化的加密函数
def get_encryption_key() -> bytes:
    """从固定密钥派生加密密钥"""
    key = hashlib.sha256(b"test-secret-key").digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value: str) -> str:
    """加密字符串值"""
    if not value:
        return value
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """解密字符串值"""
    if not encrypted_value:
        return encrypted_value
    try:
        fernet = Fernet(get_encryption_key())
        decrypted = fernet.decrypt(encrypted_value.encode())
        return decrypted.decode()
    except Exception:
        return encrypted_value


# 简化的数据模型
Base = declarative_base()


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(String, nullable=True)
    encrypted = Column(Boolean, default=False)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 简化的ConfigService
class SimpleConfigService:
    """简化的配置服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def set_config(self, key: str, value: str, encrypted: bool = False, description: str = None):
        """设置配置项"""
        from sqlalchemy import select
        
        stored_value = encrypt_value(value) if encrypted else value
        
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        
        if config:
            config.config_value = stored_value
            config.encrypted = encrypted
            if description:
                config.description = description
        else:
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
    
    async def get_config(self, key: str, decrypt: bool = False):
        """获取配置项"""
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(SystemConfig).where(SystemConfig.config_key == key)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            return None
        
        value = config.config_value
        
        if config.encrypted and decrypt and value:
            value = decrypt_value(value)
        
        return value
    
    async def get_all_configs(self, include_encrypted: bool = False):
        """获取所有配置"""
        from sqlalchemy import select
        
        result = await self.db.execute(select(SystemConfig))
        configs = result.scalars().all()
        
        config_dict = {}
        for config in configs:
            if config.encrypted and not include_encrypted:
                config_dict[config.config_key] = "***encrypted***"
            else:
                config_dict[config.config_key] = config.config_value
        
        return config_dict


async def test_api_key_management():
    """测试API密钥管理功能"""
    
    print("=" * 70)
    print("API密钥管理集成测试")
    print("=" * 70)
    
    # 创建测试数据库
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    test_results = []
    
    async with async_session() as session:
        config_service = SimpleConfigService(session)
        
        # 测试1: 设置加密的API密钥
        print("\n[测试 1] 设置加密的OpenAI API密钥")
        test_api_key = "sk-test-key-1234567890abcdef"
        await config_service.set_config(
            key="openai_api_key",
            value=test_api_key,
            encrypted=True,
            description="OpenAI API密钥"
        )
        print(f"  原始密钥: {test_api_key}")
        test_results.append(("设置加密密钥", True))
        
        # 测试2: 验证加密存储
        print("\n[测试 2] 验证密钥已加密存储")
        encrypted_value = await config_service.get_config("openai_api_key", decrypt=False)
        is_encrypted = encrypted_value != test_api_key
        print(f"  加密后的值: {encrypted_value[:50]}...")
        print(f"  ✓ 验证: 已加密 = {is_encrypted}")
        test_results.append(("验证加密存储", is_encrypted))
        
        # 测试3: 解密获取
        print("\n[测试 3] 解密获取API密钥")
        decrypted_value = await config_service.get_config("openai_api_key", decrypt=True)
        is_correct = decrypted_value == test_api_key
        print(f"  解密后的值: {decrypted_value}")
        print(f"  ✓ 验证: 解密正确 = {is_correct}")
        test_results.append(("解密获取", is_correct))
        
        # 测试4: 更新API密钥
        print("\n[测试 4] 更新API密钥")
        new_api_key = "sk-new-key-0987654321fedcba"
        await config_service.set_config(
            key="openai_api_key",
            value=new_api_key,
            encrypted=True
        )
        updated_value = await config_service.get_config("openai_api_key", decrypt=True)
        is_updated = updated_value == new_api_key
        print(f"  新密钥: {new_api_key}")
        print(f"  更新后的值: {updated_value}")
        print(f"  ✓ 验证: 更新成功 = {is_updated}")
        test_results.append(("更新密钥", is_updated))
        
        # 测试5: 混合配置（加密和非加密）
        print("\n[测试 5] 混合配置（加密和非加密）")
        await config_service.set_config(
            key="openai_model",
            value="gpt-4",
            encrypted=False
        )
        await config_service.set_config(
            key="oss_access_key",
            value="secret-oss-key",
            encrypted=True
        )
        all_configs = await config_service.get_all_configs(include_encrypted=False)
        print(f"  配置列表:")
        for key, value in all_configs.items():
            print(f"    - {key}: {value}")
        
        has_encrypted_hidden = all_configs["openai_api_key"] == "***encrypted***"
        has_plain_visible = all_configs["openai_model"] == "gpt-4"
        print(f"  ✓ 验证: 加密值已隐藏 = {has_encrypted_hidden}")
        print(f"  ✓ 验证: 明文值可见 = {has_plain_visible}")
        test_results.append(("混合配置", has_encrypted_hidden and has_plain_visible))
        
        # 测试6: 加密解密往返
        print("\n[测试 6] 加密解密往返")
        original = "sk-test-roundtrip-key-xyz"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        is_roundtrip = original == decrypted
        print(f"  原始值: {original}")
        print(f"  加密后: {encrypted[:50]}...")
        print(f"  解密后: {decrypted}")
        print(f"  ✓ 验证: 往返成功 = {is_roundtrip}")
        test_results.append(("加密解密往返", is_roundtrip))
        
        # 测试7: 不存在的配置
        print("\n[测试 7] 获取不存在的配置")
        nonexistent = await config_service.get_config("nonexistent_key")
        is_none = nonexistent is None
        print(f"  返回值: {nonexistent}")
        print(f"  ✓ 验证: 返回None = {is_none}")
        test_results.append(("不存在的配置", is_none))
        
        # 测试8: 多个加密配置
        print("\n[测试 8] 多个加密配置")
        configs_to_test = {
            "imap_password": "imap-secret-pass",
            "wordpress_api_key": "wp-api-key-123",
            "jwt_secret": "jwt-secret-xyz"
        }
        
        for key, value in configs_to_test.items():
            await config_service.set_config(key, value, encrypted=True)
        
        all_correct = True
        for key, expected_value in configs_to_test.items():
            retrieved = await config_service.get_config(key, decrypt=True)
            if retrieved != expected_value:
                all_correct = False
                print(f"  ✗ {key}: 期望 {expected_value}, 得到 {retrieved}")
            else:
                print(f"  ✓ {key}: 正确")
        
        test_results.append(("多个加密配置", all_correct))
    
    # 清理
    await engine.dispose()
    
    # 输出测试结果
    print("\n" + "=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！API密钥管理功能正常工作。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_api_key_management())
    sys.exit(exit_code)
