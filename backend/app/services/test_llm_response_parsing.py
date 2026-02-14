# -*- coding: utf-8 -*-
"""
测试LLM响应解析功能

测试覆盖：
1. 响应结构验证
2. 转换内容质量验证
3. 响应元数据提取
4. 各种异常情况处理
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.services.llm_service import LLMService, LLMTransformError


# 测试用的虚拟API密钥
TEST_API_KEY = "sk-test-key-for-testing-only"


class TestResponseStructureValidation:
    """测试响应结构验证"""
    
    def test_validate_response_structure_valid(self):
        """测试有效的响应结构"""
        service = LLMService(api_key=TEST_API_KEY)
        
        # 创建有效的响应对象
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = "转换后的文本"
        
        # 不应该抛出异常
        service._validate_response_structure(response)
    
    def test_validate_response_structure_none(self):
        """测试None响应"""
        service = LLMService(api_key=TEST_API_KEY)
        
        with pytest.raises(LLMTransformError, match="Response object is None"):
            service._validate_response_structure(None)
    
    def test_validate_response_structure_no_choices(self):
        """测试缺少choices属性"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock(spec=[])  # 没有choices属性
        
        with pytest.raises(LLMTransformError, match="missing 'choices' attribute"):
            service._validate_response_structure(response)
    
    def test_validate_response_structure_empty_choices(self):
        """测试空的choices列表"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock()
        response.choices = []
        
        with pytest.raises(LLMTransformError, match="has no choices"):
            service._validate_response_structure(response)
    
    def test_validate_response_structure_no_message(self):
        """测试缺少message属性"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock()
        response.choices = [Mock(spec=[])]  # 没有message属性
        
        with pytest.raises(LLMTransformError, match="missing 'message' attribute"):
            service._validate_response_structure(response)
    
    def test_validate_response_structure_no_content(self):
        """测试缺少content属性"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock(spec=[])  # 没有content属性
        
        with pytest.raises(LLMTransformError, match="missing 'content' attribute"):
            service._validate_response_structure(response)


class TestTransformedContentValidation:
    """测试转换内容质量验证"""
    
    def test_validate_transformed_content_valid(self):
        """测试有效的转换内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本，包含一些内容。"
        transformed = "这是一段转换后的文本，包含相似的内容。"
        
        # 不应该抛出异常
        service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_empty(self):
        """测试空的转换内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本"
        transformed = ""
        
        with pytest.raises(LLMTransformError, match="Transformed content is empty"):
            service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_whitespace_only(self):
        """测试只包含空白字符的转换内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本"
        transformed = "   \n\t  "
        
        with pytest.raises(LLMTransformError, match="Transformed content is empty"):
            service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_too_short(self):
        """测试转换内容过短"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段很长的原始文本，包含很多内容和细节。" * 10
        transformed = "短文本"
        
        with pytest.raises(LLMTransformError, match="too short"):
            service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_too_long_warning(self):
        """测试转换内容过长（应该只记录警告，不抛出异常）"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "短文本"
        transformed = "这是一段很长的转换后文本，包含很多扩展内容和详细说明。" * 10
        
        # 不应该抛出异常，只记录警告
        service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_error_marker_cannot(self):
        """测试包含错误标记 'I cannot'"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本"
        transformed = "I cannot process this request because..."
        
        with pytest.raises(LLMTransformError, match="error marker"):
            service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_error_marker_sorry(self):
        """测试包含错误标记 'Sorry'"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本"
        transformed = "Sorry, I cannot help with that."
        
        with pytest.raises(LLMTransformError, match="error marker"):
            service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_error_marker_as_ai(self):
        """测试包含错误标记 'As an AI'"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本"
        transformed = "As an AI language model, I cannot..."
        
        with pytest.raises(LLMTransformError, match="error marker"):
            service._validate_transformed_content(original, transformed)
    
    def test_validate_transformed_content_case_insensitive(self):
        """测试错误标记检测是大小写不敏感的"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段原始文本"
        transformed = "i CaNnOt process this request"
        
        with pytest.raises(LLMTransformError, match="error marker"):
            service._validate_transformed_content(original, transformed)


class TestResponseMetadataExtraction:
    """测试响应元数据提取"""
    
    def test_extract_response_metadata_complete(self):
        """测试提取完整的元数据"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock()
        response.usage = Mock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.total_tokens = 150
        response.model = "gpt-3.5-turbo"
        response.id = "chatcmpl-123456"
        response.choices = [Mock()]
        response.choices[0].finish_reason = "stop"
        
        metadata = service._extract_response_metadata(response)
        
        assert metadata['prompt_tokens'] == 100
        assert metadata['completion_tokens'] == 50
        assert metadata['total_tokens'] == 150
        assert metadata['model'] == "gpt-3.5-turbo"
        assert metadata['response_id'] == "chatcmpl-123456"
        assert metadata['finish_reason'] == "stop"
    
    def test_extract_response_metadata_partial(self):
        """测试提取部分元数据"""
        service = LLMService(api_key=TEST_API_KEY)
        
        # 使用spec限制Mock对象只有特定属性
        response = Mock(spec=['model', 'choices'])
        response.model = "gpt-3.5-turbo"
        response.choices = []
        
        metadata = service._extract_response_metadata(response)
        
        assert metadata['model'] == "gpt-3.5-turbo"
        assert 'prompt_tokens' not in metadata
        assert 'finish_reason' not in metadata
    
    def test_extract_response_metadata_empty(self):
        """测试从空响应提取元数据"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock(spec=[])
        
        metadata = service._extract_response_metadata(response)
        
        assert metadata == {}
    
    def test_extract_response_metadata_exception_handling(self):
        """测试元数据提取异常处理"""
        service = LLMService(api_key=TEST_API_KEY)
        
        response = Mock()
        response.usage = Mock()
        # 模拟访问属性时抛出异常
        type(response.usage).prompt_tokens = property(lambda self: (_ for _ in ()).throw(Exception("Test error")))
        
        # 不应该抛出异常，应该返回空字典
        metadata = service._extract_response_metadata(response)
        
        assert isinstance(metadata, dict)


@pytest.mark.asyncio
class TestTransformTextWithParsing:
    """测试transform_text方法的响应解析集成"""
    
    async def test_transform_text_with_valid_response(self):
        """测试有效响应的完整流程"""
        service = LLMService(api_key=TEST_API_KEY)
        
        # 创建模拟响应
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "这是转换后的文本内容，长度适中。"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 30
        mock_response.usage.total_tokens = 80
        mock_response.model = "gpt-3.5-turbo"
        mock_response.id = "chatcmpl-test"
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await service.transform_text("这是原始文本内容。")
            
            assert result == "这是转换后的文本内容，长度适中。"
            mock_create.assert_called_once()
    
    async def test_transform_text_with_invalid_structure(self):
        """测试响应结构无效"""
        service = LLMService(api_key=TEST_API_KEY)
        
        # 创建无效响应（缺少choices）
        mock_response = Mock(spec=[])
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            with pytest.raises(LLMTransformError, match="missing 'choices' attribute"):
                await service.transform_text("这是原始文本")
    
    async def test_transform_text_with_empty_content(self):
        """测试返回空内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = ""
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            with pytest.raises(LLMTransformError, match="Transformed content is empty"):
                await service.transform_text("这是原始文本")
    
    async def test_transform_text_with_error_marker(self):
        """测试返回包含错误标记的内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "I cannot process this request because it violates policy."
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            with pytest.raises(LLMTransformError, match="error marker"):
                await service.transform_text("这是原始文本")
    
    async def test_transform_text_with_too_short_content(self):
        """测试返回过短的内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是一段很长的原始文本，包含很多内容和细节。" * 20
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "短"
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            with pytest.raises(LLMTransformError, match="too short"):
                await service.transform_text(original)
    
    async def test_transform_text_empty_input(self):
        """测试空输入"""
        service = LLMService(api_key=TEST_API_KEY)
        
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            await service.transform_text("")
    
    async def test_transform_text_whitespace_input(self):
        """测试只包含空白字符的输入"""
        service = LLMService(api_key=TEST_API_KEY)
        
        with pytest.raises(ValueError, match="Text content cannot be empty"):
            await service.transform_text("   \n\t  ")


@pytest.mark.asyncio
class TestEdgeCases:
    """测试边界情况"""
    
    async def test_transform_text_with_exact_min_length(self):
        """测试转换后内容刚好达到最小长度"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是原始文本" * 10  # 60字符
        transformed = "转换文本" * 8  # 32字符，刚好超过50%
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = transformed
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 50
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await service.transform_text(original)
            assert result == transformed
    
    async def test_transform_text_with_unicode_content(self):
        """测试包含Unicode字符的内容"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是包含中文、emoji 😀 和特殊字符的文本 ©®™"
        transformed = "这是转换后包含中文、emoji 😀 和特殊字符的文本 ©®™"
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = transformed
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 50
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await service.transform_text(original)
            assert result == transformed
    
    async def test_transform_text_strips_whitespace(self):
        """测试自动去除首尾空白字符"""
        service = LLMService(api_key=TEST_API_KEY)
        
        original = "这是原始文本内容"
        transformed = "  \n这是转换后的文本内容\n  "
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = transformed
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 50
        
        with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await service.transform_text(original)
            assert result == "这是转换后的文本内容"
            assert not result.startswith(" ")
            assert not result.endswith(" ")
