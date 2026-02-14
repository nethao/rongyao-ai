"""
LLM服务单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import (
    APIError,
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    APITimeoutError,
    BadRequestError,
    InternalServerError
)
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from app.services.llm_service import (
    LLMService,
    LLMConfigurationError,
    LLMTransformError
)


@pytest.fixture
def mock_openai_response():
    """创建模拟的OpenAI响应"""
    message = ChatCompletionMessage(
        role="assistant",
        content="这是转换后的文本内容"
    )
    choice = Choice(
        index=0,
        message=message,
        finish_reason="stop"
    )
    return ChatCompletion(
        id="test-id",
        model="gpt-4",
        object="chat.completion",
        created=1234567890,
        choices=[choice]
    )


@pytest.fixture
def llm_service():
    """创建LLM服务实例"""
    return LLMService(api_key="test-api-key", model="gpt-4")


@pytest.mark.asyncio
async def test_llm_service_initialization():
    """测试LLM服务初始化"""
    service = LLMService(api_key="test-key", model="gpt-4")
    assert service.api_key == "test-key"
    assert service.model == "gpt-4"
    assert service.client is not None


@pytest.mark.asyncio
async def test_llm_service_initialization_without_api_key():
    """测试没有API密钥时初始化失败"""
    with patch('app.services.llm_service.settings') as mock_settings:
        mock_settings.OPENAI_API_KEY = None
        mock_settings.OPENAI_MODEL = "gpt-4"
        
        with pytest.raises(LLMConfigurationError, match="OpenAI API key is not configured"):
            LLMService()


@pytest.mark.asyncio
async def test_transform_text_success(llm_service, mock_openai_response):
    """测试文本转换成功"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response
        
        result = await llm_service.transform_text("我是一名工程师")
        
        assert result == "这是转换后的文本内容"
        mock_create.assert_called_once()
        
        # 验证调用参数
        call_args = mock_create.call_args
        assert call_args.kwargs['model'] == "gpt-4"
        assert len(call_args.kwargs['messages']) == 2
        assert call_args.kwargs['messages'][0]['role'] == "system"
        assert call_args.kwargs['messages'][1]['role'] == "user"
        assert call_args.kwargs['messages'][1]['content'] == "我是一名工程师"


@pytest.mark.asyncio
async def test_transform_text_with_custom_prompt(llm_service, mock_openai_response):
    """测试使用自定义提示词转换文本"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response
        
        custom_prompt = "这是自定义提示词"
        result = await llm_service.transform_text(
            "测试文本",
            system_prompt=custom_prompt
        )
        
        assert result == "这是转换后的文本内容"
        
        # 验证使用了自定义提示词
        call_args = mock_create.call_args
        assert call_args.kwargs['messages'][0]['content'] == custom_prompt


@pytest.mark.asyncio
async def test_transform_text_empty_input(llm_service):
    """测试空输入时抛出异常"""
    with pytest.raises(ValueError, match="Text content cannot be empty"):
        await llm_service.transform_text("")
    
    with pytest.raises(ValueError, match="Text content cannot be empty"):
        await llm_service.transform_text("   ")


@pytest.mark.asyncio
async def test_transform_text_empty_response(llm_service):
    """测试LLM返回空响应时抛出异常"""
    empty_response = ChatCompletion(
        id="test-id",
        model="gpt-4",
        object="chat.completion",
        created=1234567890,
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(role="assistant", content=""),
                finish_reason="stop"
            )
        ]
    )
    
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = empty_response
        
        with pytest.raises(LLMTransformError, match="Transformed content is empty"):
            await llm_service.transform_text("测试文本")


@pytest.mark.asyncio
async def test_transform_text_rate_limit_error(llm_service):
    """测试速率限制错误时重试"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟速率限制错误
        mock_create.side_effect = RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None
        )
        
        with pytest.raises(RateLimitError):
            await llm_service.transform_text("测试文本")
        
        # 验证重试了3次
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_transform_text_api_connection_error(llm_service):
    """测试API连接错误时重试"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟连接错误
        mock_create.side_effect = APIConnectionError(request=MagicMock())
        
        with pytest.raises(APIConnectionError):
            await llm_service.transform_text("测试文本")
        
        # 验证重试了3次
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_transform_text_api_error(llm_service):
    """测试API错误时不重试并包装为LLMTransformError"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟API错误
        mock_create.side_effect = APIError(
            "API error",
            request=MagicMock(),
            body=None
        )
        
        with pytest.raises(LLMTransformError, match="OpenAI API error"):
            await llm_service.transform_text("测试文本")
        
        # 验证只调用了1次，没有重试
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_transform_text_authentication_error(llm_service):
    """测试认证错误时不重试并包装为LLMTransformError"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟认证错误
        mock_create.side_effect = AuthenticationError(
            "Invalid API key",
            response=MagicMock(status_code=401),
            body=None
        )
        
        with pytest.raises(LLMTransformError, match="Authentication failed"):
            await llm_service.transform_text("测试文本")
        
        # 验证只调用了1次，没有重试
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_transform_text_bad_request_error(llm_service):
    """测试请求参数错误时不重试并包装为LLMTransformError"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟请求参数错误
        mock_create.side_effect = BadRequestError(
            "Invalid parameters",
            response=MagicMock(status_code=400),
            body=None
        )
        
        with pytest.raises(LLMTransformError, match="Bad request"):
            await llm_service.transform_text("测试文本")
        
        # 验证只调用了1次，没有重试
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_transform_text_timeout_error(llm_service):
    """测试超时错误时重试"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟超时错误
        mock_create.side_effect = APITimeoutError(request=MagicMock())
        
        with pytest.raises(APITimeoutError):
            await llm_service.transform_text("测试文本")
        
        # 验证重试了3次
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_transform_text_internal_server_error(llm_service):
    """测试服务器内部错误时不重试并包装为LLMTransformError"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 模拟服务器内部错误
        mock_create.side_effect = InternalServerError(
            "Internal server error",
            response=MagicMock(status_code=500),
            body=None
        )
        
        with pytest.raises(LLMTransformError, match="OpenAI server error"):
            await llm_service.transform_text("测试文本")
        
        # 验证只调用了1次，没有重试
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_transform_text_retry_then_success(llm_service, mock_openai_response):
    """测试重试后成功的场景"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        # 前两次失败，第三次成功
        mock_create.side_effect = [
            RateLimitError("Rate limit", response=MagicMock(status_code=429), body=None),
            APIConnectionError(request=MagicMock()),
            mock_openai_response
        ]
        
        result = await llm_service.transform_text("测试文本")
        
        assert result == "这是转换后的文本内容"
        # 验证调用了3次
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_verify_connection_success(llm_service, mock_openai_response):
    """测试连接验证成功"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_openai_response
        
        result = await llm_service.verify_connection()
        
        assert result is True
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_verify_connection_failure(llm_service):
    """测试连接验证失败"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = APIError(
            "Connection failed",
            request=MagicMock(),
            body=None
        )
        
        result = await llm_service.verify_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_verify_connection_authentication_error(llm_service):
    """测试连接验证时认证失败"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = AuthenticationError(
            "Invalid API key",
            response=MagicMock(status_code=401),
            body=None
        )
        
        result = await llm_service.verify_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_verify_connection_rate_limit_error(llm_service):
    """测试连接验证时速率限制"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = RateLimitError(
            "Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None
        )
        
        result = await llm_service.verify_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_verify_connection_timeout_error(llm_service):
    """测试连接验证时超时"""
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = APITimeoutError(request=MagicMock())
        
        result = await llm_service.verify_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_verify_connection_empty_response(llm_service):
    """测试连接验证时返回空响应"""
    empty_response = ChatCompletion(
        id="test-id",
        model="gpt-4",
        object="chat.completion",
        created=1234567890,
        choices=[]
    )
    
    with patch.object(llm_service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = empty_response
        
        result = await llm_service.verify_connection()
        
        assert result is False


@pytest.mark.asyncio
async def test_build_default_transform_prompt(llm_service):
    """测试默认提示词构建"""
    prompt = llm_service._build_default_transform_prompt()
    
    assert "第一人称" in prompt
    assert "第三人称" in prompt
    assert "引号" in prompt or "引用" in prompt
    assert "时间" in prompt


@pytest.mark.asyncio
async def test_close_service(llm_service):
    """测试关闭服务"""
    with patch.object(llm_service.client, 'close', new_callable=AsyncMock) as mock_close:
        await llm_service.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_get_llm_service():
    """测试获取全局服务实例"""
    from app.services.llm_service import get_llm_service, close_llm_service
    
    with patch('app.services.llm_service.settings') as mock_settings:
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.OPENAI_MODEL = "gpt-4"
        
        service1 = get_llm_service()
        service2 = get_llm_service()
        
        # 验证返回的是同一个实例
        assert service1 is service2
        
        # 清理
        await close_llm_service()
