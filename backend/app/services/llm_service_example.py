"""
LLM服务使用示例
演示如何使用LLM服务进行文本转换
"""
import asyncio
from app.services.llm_service import LLMService


async def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建LLM服务实例
    llm_service = LLMService(
        api_key="your-api-key-here",
        model="gpt-4"
    )
    
    # 原始文本（第一人称）
    original_text = """
    我是一名软件工程师，在我们公司工作了三年。昨天我完成了一个重要的项目，
    我局领导对我的工作表示了肯定。我认为这是一个很好的学习机会。
    """
    
    try:
        # 转换文本
        transformed_text = await llm_service.transform_text(original_text)
        
        print("原始文本:")
        print(original_text)
        print("\n转换后文本:")
        print(transformed_text)
        
    except Exception as e:
        print(f"转换失败: {e}")
    
    finally:
        await llm_service.close()


async def example_custom_prompt():
    """自定义提示词示例"""
    print("\n=== 自定义提示词示例 ===")
    
    llm_service = LLMService(
        api_key="your-api-key-here",
        model="gpt-4"
    )
    
    # 自定义提示词
    custom_prompt = """
    你是一个新闻编辑。请将以下第一人称的内容改写为新闻报道风格的第三人称叙述。
    保持客观中立的语气，使用标准的新闻写作格式。
    """
    
    original_text = "我今天参加了公司的年会，我感到非常激动。"
    
    try:
        transformed_text = await llm_service.transform_text(
            original_text,
            system_prompt=custom_prompt,
            temperature=0.5  # 降低随机性，使输出更稳定
        )
        
        print("原始文本:")
        print(original_text)
        print("\n转换后文本:")
        print(transformed_text)
        
    except Exception as e:
        print(f"转换失败: {e}")
    
    finally:
        await llm_service.close()


async def example_verify_connection():
    """验证连接示例"""
    print("\n=== 验证连接示例 ===")
    
    llm_service = LLMService(
        api_key="your-api-key-here",
        model="gpt-4"
    )
    
    try:
        is_connected = await llm_service.verify_connection()
        
        if is_connected:
            print("✓ LLM API连接正常")
        else:
            print("✗ LLM API连接失败")
        
    except Exception as e:
        print(f"验证失败: {e}")
    
    finally:
        await llm_service.close()


async def example_global_service():
    """使用全局服务实例示例"""
    print("\n=== 全局服务实例示例 ===")
    
    from app.services.llm_service import get_llm_service, close_llm_service
    
    try:
        # 获取全局服务实例
        llm_service = get_llm_service()
        
        # 使用服务
        result = await llm_service.transform_text("我是一名开发者")
        print(f"转换结果: {result}")
        
    except Exception as e:
        print(f"操作失败: {e}")
    
    finally:
        # 关闭全局服务
        await close_llm_service()


async def main():
    """运行所有示例"""
    print("LLM服务使用示例")
    print("=" * 50)
    
    # 注意：这些示例需要有效的OpenAI API密钥才能运行
    # 请在实际使用时替换 "your-api-key-here" 为真实的API密钥
    
    print("\n提示：这些示例需要有效的OpenAI API密钥")
    print("请在代码中设置正确的API密钥后运行\n")
    
    # 取消注释以下行来运行示例
    # await example_basic_usage()
    # await example_custom_prompt()
    # await example_verify_connection()
    # await example_global_service()


if __name__ == "__main__":
    asyncio.run(main())
