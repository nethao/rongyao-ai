"""
API密钥管理演示脚本
展示LLM服务与ConfigService的集成
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base
from app.services.config_service import ConfigService
from app.services.llm_service import LLMService
from app.utils.encryption import encrypt_value, decrypt_value


async def demo_api_key_management():
    """演示API密钥管理功能"""
    
    print("=" * 60)
    print("API密钥管理演示")
    print("=" * 60)
    
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
    
    async with async_session() as session:
        config_service = ConfigService(session)
        
        # 1. 测试加密存储API密钥
        print("\n1. 设置加密的OpenAI API密钥...")
        test_api_key = "sk-test-key-1234567890abcdef"
        await config_service.set_config(
            key="openai_api_key",
            value=test_api_key,
            encrypted=True,
            description="OpenAI API密钥用于AI语义转换"
        )
        print(f"   ✓ 原始密钥: {test_api_key}")
        
        # 2. 获取加密后的值（不解密）
        print("\n2. 获取加密后的值（数据库中存储的）...")
        encrypted_value = await config_service.get_config("openai_api_key", decrypt=False)
        print(f"   ✓ 加密后的值: {encrypted_value[:50]}...")
        print(f"   ✓ 验证: 加密值与原始值不同 = {encrypted_value != test_api_key}")
        
        # 3. 获取解密后的值
        print("\n3. 获取解密后的值...")
        decrypted_value = await config_service.get_config("openai_api_key", decrypt=True)
        print(f"   ✓ 解密后的值: {decrypted_value}")
        print(f"   ✓ 验证: 解密值与原始值相同 = {decrypted_value == test_api_key}")
        
        # 4. 从ConfigService创建LLM服务
        print("\n4. 从ConfigService创建LLM服务...")
        try:
            llm_service = await LLMService.from_config_service(session)
            print(f"   ✓ LLM服务创建成功")
            print(f"   ✓ 使用的API密钥: {llm_service.api_key}")
            print(f"   ✓ 使用的模型: {llm_service.model}")
            await llm_service.close()
        except Exception as e:
            print(f"   ✗ 创建失败: {e}")
        
        # 5. 更新API密钥
        print("\n5. 更新API密钥...")
        new_api_key = "sk-new-key-0987654321fedcba"
        await config_service.set_config(
            key="openai_api_key",
            value=new_api_key,
            encrypted=True
        )
        updated_value = await config_service.get_config("openai_api_key", decrypt=True)
        print(f"   ✓ 新密钥: {new_api_key}")
        print(f"   ✓ 更新后的值: {updated_value}")
        print(f"   ✓ 验证: 更新成功 = {updated_value == new_api_key}")
        
        # 6. 获取所有配置（隐藏加密值）
        print("\n6. 获取所有配置（隐藏加密值）...")
        await config_service.set_config(
            key="openai_model",
            value="gpt-4",
            encrypted=False
        )
        all_configs = await config_service.get_all_configs(include_encrypted=False)
        print(f"   ✓ 配置列表:")
        for key, value in all_configs.items():
            print(f"      - {key}: {value}")
        
        # 7. 测试加密解密往返
        print("\n7. 测试加密解密往返...")
        original = "sk-test-roundtrip-key"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        print(f"   ✓ 原始值: {original}")
        print(f"   ✓ 加密后: {encrypted[:50]}...")
        print(f"   ✓ 解密后: {decrypted}")
        print(f"   ✓ 验证: 往返成功 = {original == decrypted}")
        
        # 8. 测试不存在的配置
        print("\n8. 测试获取不存在的配置...")
        nonexistent = await config_service.get_config("nonexistent_key")
        print(f"   ✓ 返回值: {nonexistent}")
        print(f"   ✓ 验证: 返回None = {nonexistent is None}")
    
    # 清理
    await engine.dispose()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n总结:")
    print("✓ API密钥可以加密存储到数据库")
    print("✓ ConfigService正确处理加密和解密")
    print("✓ LLM服务可以从ConfigService获取API密钥")
    print("✓ 支持更新和查询配置")
    print("✓ 加密值在数据库中安全存储")


if __name__ == "__main__":
    asyncio.run(demo_api_key_management())
