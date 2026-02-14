"""
测试API密钥管理集成
验证LLM服务与ConfigService的集成
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.config_service import ConfigService
from app.services.llm_service import LLMService
from app.models.system_config import SystemConfig
from app.utils.encryption import encrypt_value, decrypt_value


class TestAPIKeyManagement:
    """测试API密钥管理功能"""
    
    @pytest.mark.asyncio
    async def test_set_encrypted_api_key(self, db_session: AsyncSession):
        """测试设置加密的API密钥"""
        config_service = ConfigService(db_session)
        
        # 设置加密的API密钥
        test_key = "sk-test-key-12345"
        await config_service.set_config(
            key="openai_api_key",
            value=test_key,
            encrypted=True,
            description="OpenAI API密钥"
        )
        
        # 获取加密后的值（不解密）
        encrypted_value = await config_service.get_config("openai_api_key", decrypt=False)
        
        # 验证存储的是加密值
        assert encrypted_value != test_key
        assert encrypted_value is not None
        
        # 获取解密后的值
        decrypted_value = await config_service.get_config("openai_api_key", decrypt=True)
        
        # 验证解密后的值正确
        assert decrypted_value == test_key
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_api_key(self, db_session: AsyncSession):
        """测试获取不存在的API密钥"""
        config_service = ConfigService(db_session)
        
        # 获取不存在的配置
        value = await config_service.get_config("nonexistent_key", decrypt=True)
        
        # 应该返回None
        assert value is None
    
    @pytest.mark.asyncio
    async def test_llm_service_from_config_service(self, db_session: AsyncSession):
        """测试从ConfigService创建LLM服务"""
        config_service = ConfigService(db_session)
        
        # 设置API密钥
        test_key = "sk-test-key-12345"
        await config_service.set_config(
            key="openai_api_key",
            value=test_key,
            encrypted=True
        )
        
        # 从ConfigService创建LLM服务
        llm_service = await LLMService.from_config_service(db_session)
        
        # 验证服务创建成功
        assert llm_service is not None
        assert llm_service.api_key == test_key
        
        # 清理
        await llm_service.close()
    
    @pytest.mark.asyncio
    async def test_llm_service_from_config_service_no_key(self, db_session: AsyncSession):
        """测试从ConfigService创建LLM服务但没有配置密钥"""
        from app.services.llm_service import LLMConfigurationError
        
        # 不设置任何密钥，且环境变量也没有
        with patch('app.services.llm_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            # 应该抛出LLMConfigurationError
            with pytest.raises(LLMConfigurationError, match="OpenAI API key is not configured"):
                await LLMService.from_config_service(db_session)
    
    @pytest.mark.asyncio
    async def test_llm_service_fallback_to_env(self, db_session: AsyncSession):
        """测试LLM服务回退到环境变量"""
        # 数据库中没有配置，但环境变量有
        env_key = "sk-env-key-67890"
        
        with patch('app.services.llm_service.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = env_key
            mock_settings.OPENAI_MODEL = "gpt-4"
            
            # 从ConfigService创建（数据库中没有配置）
            llm_service = await LLMService.from_config_service(db_session)
            
            # 应该使用环境变量的密钥
            assert llm_service.api_key == env_key
            
            # 清理
            await llm_service.close()
    
    @pytest.mark.asyncio
    async def test_config_service_verify_llm_valid_key(self, db_session: AsyncSession):
        """测试验证有效的LLM配置"""
        config_service = ConfigService(db_session)
        
        # 设置API密钥
        await config_service.set_config(
            key="openai_api_key",
            value="sk-test-key-12345",
            encrypted=True
        )
        
        # Mock LLM服务的验证方法
        with patch('app.services.llm_service.LLMService') as mock_llm_class:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.verify_connection = AsyncMock(return_value=True)
            mock_llm_instance.close = AsyncMock()
            mock_llm_class.return_value = mock_llm_instance
            
            # 验证配置
            is_valid = await config_service.verify_llm_config()
            
            # 应该返回True
            assert is_valid is True
            
            # 验证调用了正确的方法
            mock_llm_class.assert_called_once()
            mock_llm_instance.verify_connection.assert_called_once()
            mock_llm_instance.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_config_service_verify_llm_invalid_key(self, db_session: AsyncSession):
        """测试验证无效的LLM配置"""
        config_service = ConfigService(db_session)
        
        # 设置API密钥
        await config_service.set_config(
            key="openai_api_key",
            value="invalid-key",
            encrypted=True
        )
        
        # Mock LLM服务的验证方法返回False
        with patch('app.services.llm_service.LLMService') as mock_llm_class:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.verify_connection = AsyncMock(return_value=False)
            mock_llm_instance.close = AsyncMock()
            mock_llm_class.return_value = mock_llm_instance
            
            # 验证配置
            is_valid = await config_service.verify_llm_config()
            
            # 应该返回False
            assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_config_service_verify_llm_no_key(self, db_session: AsyncSession):
        """测试验证LLM配置但没有密钥"""
        config_service = ConfigService(db_session)
        
        # 不设置任何密钥
        is_valid = await config_service.verify_llm_config()
        
        # 应该返回False
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_config_service_verify_llm_exception(self, db_session: AsyncSession):
        """测试验证LLM配置时发生异常"""
        config_service = ConfigService(db_session)
        
        # 设置API密钥
        await config_service.set_config(
            key="openai_api_key",
            value="sk-test-key",
            encrypted=True
        )
        
        # Mock LLM服务抛出异常
        with patch('app.services.llm_service.LLMService') as mock_llm_class:
            mock_llm_class.side_effect = Exception("Connection error")
            
            # 验证配置
            is_valid = await config_service.verify_llm_config()
            
            # 应该返回False
            assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_update_api_key(self, db_session: AsyncSession):
        """测试更新API密钥"""
        config_service = ConfigService(db_session)
        
        # 设置初始密钥
        old_key = "sk-old-key-12345"
        await config_service.set_config(
            key="openai_api_key",
            value=old_key,
            encrypted=True
        )
        
        # 验证初始密钥
        value = await config_service.get_config("openai_api_key", decrypt=True)
        assert value == old_key
        
        # 更新密钥
        new_key = "sk-new-key-67890"
        await config_service.set_config(
            key="openai_api_key",
            value=new_key,
            encrypted=True
        )
        
        # 验证更新后的密钥
        value = await config_service.get_config("openai_api_key", decrypt=True)
        assert value == new_key
    
    @pytest.mark.asyncio
    async def test_encryption_decryption_roundtrip(self):
        """测试加密解密往返"""
        original_value = "sk-test-key-12345-abcdef"
        
        # 加密
        encrypted = encrypt_value(original_value)
        
        # 验证加密后的值不同
        assert encrypted != original_value
        
        # 解密
        decrypted = decrypt_value(encrypted)
        
        # 验证解密后的值相同
        assert decrypted == original_value
    
    @pytest.mark.asyncio
    async def test_get_all_configs_hides_encrypted(self, db_session: AsyncSession):
        """测试获取所有配置时隐藏加密值"""
        config_service = ConfigService(db_session)
        
        # 设置加密和非加密配置
        await config_service.set_config(
            key="openai_api_key",
            value="sk-secret-key",
            encrypted=True
        )
        await config_service.set_config(
            key="openai_model",
            value="gpt-4",
            encrypted=False
        )
        
        # 获取所有配置（不包含加密值）
        configs = await config_service.get_all_configs(include_encrypted=False)
        
        # 验证加密配置被隐藏
        assert configs["openai_api_key"] == "***encrypted***"
        assert configs["openai_model"] == "gpt-4"
        
        # 获取所有配置（包含加密值）
        configs_with_encrypted = await config_service.get_all_configs(include_encrypted=True)
        
        # 验证加密配置显示（但仍是加密的）
        assert configs_with_encrypted["openai_api_key"] != "***encrypted***"
        assert configs_with_encrypted["openai_api_key"] != "sk-secret-key"  # 仍是加密的
        assert configs_with_encrypted["openai_model"] == "gpt-4"


# Pytest fixtures
@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from app.database import Base
    
    # 使用内存SQLite数据库进行测试
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
    
    async with async_session() as session:
        yield session
    
    # 清理
    await engine.dispose()
