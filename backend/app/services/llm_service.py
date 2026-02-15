"""
LLM API客户端服务
用于与OpenAI API通信，实现AI语义转换功能

错误处理策略:
- RateLimitError: 速率限制错误，使用指数退避重试最多3次
- APIConnectionError: 网络连接错误，使用指数退避重试最多3次
- APIError: API错误（如无效请求），不重试，直接抛出
- AuthenticationError: 认证错误（如无效API密钥），不重试，直接抛出
- Timeout: 超时错误，使用指数退避重试最多3次
- 其他OpenAIError: 记录错误并抛出

重试配置:
- 最大重试次数: 3次
- 等待策略: 指数退避，初始2秒，最大10秒
- 重试条件: RateLimitError, APIConnectionError, Timeout
"""
import asyncio
import logging
from typing import Optional
from openai import (
    AsyncOpenAI,
    OpenAIError,
    APIError,
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
    APITimeoutError,
    BadRequestError,
    InternalServerError
)
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.config import settings


logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """LLM服务基础异常类"""
    pass


class LLMConfigurationError(LLMServiceError):
    """LLM配置错误异常"""
    pass


class LLMTransformError(LLMServiceError):
    """LLM转换错误异常"""
    pass


class LLMService:
    """LLM API客户端服务"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        初始化LLM服务
        
        Args:
            api_key: OpenAI API密钥，如果为None则从配置读取
            model: 使用的模型名称，如果为None则从配置读取
            base_url: 自定义API端点，支持OpenRouter等中转API
        
        Raises:
            LLMConfigurationError: 如果API密钥未配置
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = base_url
        
        if not self.api_key:
            error_msg = "OpenAI API key is not configured"
            logger.error(error_msg)
            raise LLMConfigurationError(error_msg)
        
        # 创建客户端，支持自定义base_url
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            logger.info(f"Using custom API endpoint: {self.base_url}")
        
        self.client = AsyncOpenAI(**client_kwargs)
        logger.info(f"LLM Service initialized with model: {self.model}")
    
    @classmethod
    async def from_config_service(
        cls,
        db: AsyncSession,
        model: Optional[str] = None
    ) -> "LLMService":
        """
        从ConfigService创建LLM服务实例
        
        Args:
            db: 数据库会话
            model: 使用的模型名称，如果为None则从配置读取
        
        Returns:
            LLM服务实例
        
        Raises:
            LLMConfigurationError: 如果API密钥未配置
        """
        from app.services.config_service import ConfigService
        
        config_service = ConfigService(db)
        api_key = await config_service.get_config("OPENAI_API_KEY", decrypt=True)
        base_url = await config_service.get_config("OPENAI_BASE_URL")
        model_name = await config_service.get_config("OPENAI_MODEL")
        
        if not api_key:
            # 如果数据库中没有配置，尝试从环境变量获取
            api_key = settings.OPENAI_API_KEY
        
        if not api_key:
            error_msg = "OpenAI API key is not configured in database or environment"
            logger.error(error_msg)
            raise LLMConfigurationError(error_msg)
        
        logger.info(f"LLM Service created from ConfigService: base_url={base_url}, model={model_name or model}")
        return cls(api_key=api_key, base_url=base_url, model=model_name or model)
    
    def _validate_response_structure(self, response) -> None:
        """
        验证LLM响应结构的完整性
        
        Args:
            response: OpenAI API响应对象
        
        Raises:
            LLMTransformError: 响应结构无效
        """
        if not response:
            raise LLMTransformError("Response object is None")
        
        if not hasattr(response, 'choices'):
            raise LLMTransformError("Response missing 'choices' attribute")
        
        if not response.choices or len(response.choices) == 0:
            raise LLMTransformError("Response has no choices")
        
        if not hasattr(response.choices[0], 'message'):
            raise LLMTransformError("Response choice missing 'message' attribute")
        
        if not hasattr(response.choices[0].message, 'content'):
            raise LLMTransformError("Response message missing 'content' attribute")
    
    def _validate_transformed_content(self, original: str, transformed: str) -> None:
        """
        验证转换后内容的质量
        
        Args:
            original: 原始文本
            transformed: 转换后的文本
        
        Raises:
            LLMTransformError: 转换内容质量不符合要求
        """
        # 检查转换后内容不为空
        if not transformed or not transformed.strip():
            raise LLMTransformError("Transformed content is empty")
        
        # 检查转换后内容长度是否合理
        original_len = len(original.strip())
        transformed_len = len(transformed.strip())
        
        # 计算原文中的图片标记数量
        img_markers_count = original.count('![图片')
        
        # 如果原文包含大量图片标记，放宽长度限制
        if img_markers_count > 10:
            # 有大量图片时，只检查纯文本部分
            # 估算纯文本长度（假设每个图片标记约100字符）
            estimated_text_len = original_len - (img_markers_count * 100)
            min_length = max(100, int(estimated_text_len * 0.3))  # 至少30%的文本
        else:
            # 正常情况：允许±50%的长度变化
            min_length = int(original_len * 0.5)
        
        max_length = int(original_len * 1.5)
        
        if transformed_len < min_length:
            logger.warning(
                f"Transformed content is too short: {transformed_len} chars "
                f"(original: {original_len} chars, min expected: {min_length}, "
                f"img_markers: {img_markers_count})"
            )
            raise LLMTransformError(
                f"Transformed content is too short ({transformed_len} chars), "
                f"expected at least {min_length} chars"
            )
        
        if transformed_len > max_length:
            logger.warning(
                f"Transformed content is too long: {transformed_len} chars "
                f"(original: {original_len} chars, max expected: {max_length})"
            )
            # 长度过长只记录警告，不抛出异常（可能是合理的扩展）
        
        # 检查是否包含明显的错误标记
        error_markers = [
            "I cannot", "I can't", "I'm unable to",
            "Sorry", "I apologize",
            "As an AI", "As a language model"
        ]
        
        for marker in error_markers:
            if marker.lower() in transformed.lower():
                raise LLMTransformError(
                    f"Transformed content contains error marker: '{marker}'"
                )
    
    def _extract_response_metadata(self, response) -> dict:
        """
        从响应中提取元数据
        
        Args:
            response: OpenAI API响应对象
        
        Returns:
            包含元数据的字典
        """
        metadata = {}
        
        try:
            # 提取使用的token数量
            if hasattr(response, 'usage'):
                metadata['prompt_tokens'] = getattr(response.usage, 'prompt_tokens', None)
                metadata['completion_tokens'] = getattr(response.usage, 'completion_tokens', None)
                metadata['total_tokens'] = getattr(response.usage, 'total_tokens', None)
            
            # 提取模型信息
            if hasattr(response, 'model'):
                metadata['model'] = response.model
            
            # 提取finish_reason
            if response.choices and len(response.choices) > 0:
                metadata['finish_reason'] = getattr(response.choices[0], 'finish_reason', None)
            
            # 提取响应ID
            if hasattr(response, 'id'):
                metadata['response_id'] = response.id
            
        except Exception as e:
            logger.warning(f"Failed to extract response metadata: {e}")
        
        return metadata
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def transform_text(
        self,
        text: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        使用LLM转换文本
        
        此方法会自动重试以下错误类型（最多3次）：
        - RateLimitError: 速率限制错误
        - APIConnectionError: 网络连接错误
        - APITimeoutError: 请求超时错误
        
        以下错误不会重试，直接抛出：
        - AuthenticationError: 认证错误（无效API密钥）
        - BadRequestError: 请求参数错误
        - APIError: 其他API错误
        
        响应解析包括：
        - 验证响应结构完整性
        - 验证转换内容质量（长度、错误标记等）
        - 提取响应元数据（token使用量、模型信息等）
        
        Args:
            text: 要转换的文本内容
            system_prompt: 系统提示词，如果为None则使用默认提示词
            temperature: 生成温度，控制随机性（0.0-2.0）
            max_tokens: 最大生成token数
        
        Returns:
            转换后的文本
        
        Raises:
            ValueError: 输入文本为空
            AuthenticationError: API密钥无效
            BadRequestError: 请求参数错误
            RateLimitError: 速率限制错误（重试3次后仍失败）
            APIConnectionError: 网络连接错误（重试3次后仍失败）
            APITimeoutError: 请求超时（重试3次后仍失败）
            LLMTransformError: 响应解析失败或转换错误
        """
        if not text or not text.strip():
            error_msg = "Text content cannot be empty"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 使用默认的语义转换提示词
        if system_prompt is None:
            system_prompt = self._build_default_transform_prompt()
        
        try:
            logger.info(f"Calling LLM API with model: {self.model}, text length: {len(text)}")
            logger.info(f"=== AI输入 (System Prompt前500字符) ===\n{system_prompt[:500]}")
            logger.info(f"=== AI输入 (User Content) ===\n{text}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 验证响应结构
            self._validate_response_structure(response)
            
            # 提取转换后的文本
            transformed_text = response.choices[0].message.content
            
            logger.info(f"=== AI输出 ===\n{transformed_text}")
            
            # 验证转换内容质量
            self._validate_transformed_content(text, transformed_text)
            
            # 提取响应元数据并记录
            metadata = self._extract_response_metadata(response)
            logger.info(
                f"LLM transformation completed successfully. "
                f"Output length: {len(transformed_text)}, "
                f"Tokens used: {metadata.get('total_tokens', 'N/A')}, "
                f"Finish reason: {metadata.get('finish_reason', 'N/A')}"
            )
            
            return transformed_text.strip()
            
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded, will retry: {e}")
            raise
        except APIConnectionError as e:
            logger.warning(f"API connection error, will retry: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout error, will retry: {e}")
            raise
        except AuthenticationError as e:
            error_msg = f"Authentication failed - invalid API key: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except BadRequestError as e:
            error_msg = f"Bad request - invalid parameters: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except InternalServerError as e:
            error_msg = f"OpenAI server error: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except APIError as e:
            error_msg = f"OpenAI API error: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except LLMTransformError:
            # 重新抛出我们自己的验证错误
            raise
        except OpenAIError as e:
            error_msg = f"OpenAI error: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during LLM transformation: {e}"
            logger.error(error_msg, exc_info=True)
            raise LLMTransformError(error_msg) from e
    
    def _build_default_transform_prompt(self) -> str:
        """
        构建默认的语义转换提示词（占位符协议版本）
        
        Returns:
            系统提示词字符串
        """
        return """你是一个专业的内容编辑助手。你的任务是将第一人称叙述转换为第三人称叙述，同时保持内容的准确性和可读性。

**关键约束（CRITICAL）：**
1. 文本中包含图片占位符，格式为 [[IMG_1]], [[IMG_2]] 等
2. 你必须**完全保留**这些占位符，不得修改、移动或删除
3. 占位符的位置必须保持不变
4. 不要输出Markdown图片语法（如 ![](url)），只使用占位符
5. 返回结果必须是Markdown格式

**转换规则：**

请遵循以下规则：
1. 将所有第一人称代词（我、我们、我局、我司等）转换为第三人称或具体的组织名称
2. 保护引用内容：引号内的内容不要修改
3. 规范化时间表述：将相对时间（如"昨天"、"上周"）转换为具体日期格式（YYYY-MM-DD）
4. 保持原文的语气和风格
5. 不要添加或删除原文中的信息
6. 保持段落结构和格式

请直接返回转换后的文本，不要添加任何解释或说明。"""
    
    async def verify_connection(self) -> bool:
        """
        验证LLM API连接是否正常
        
        此方法会发送一个简单的测试请求来验证：
        1. API密钥是否有效
        2. 网络连接是否正常
        3. 模型是否可用
        
        Returns:
            True表示连接正常，False表示连接失败
        """
        try:
            logger.info(f"Verifying LLM API connection with model: {self.model}")
            
            # 发送一个简单的测试请求
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=10,
                timeout=10.0  # 10秒超时
            )
            
            if response.choices and response.choices[0].message.content:
                logger.info("LLM API connection verified successfully")
                return True
            
            logger.warning("LLM API returned empty response during verification")
            return False
            
        except AuthenticationError as e:
            logger.error(f"LLM API authentication failed - invalid API key: {e}")
            return False
        except RateLimitError as e:
            logger.error(f"LLM API rate limit exceeded during verification: {e}")
            return False
        except APIConnectionError as e:
            logger.error(f"LLM API connection error during verification: {e}")
            return False
        except APITimeoutError as e:
            logger.error(f"LLM API timeout during verification: {e}")
            return False
        except BadRequestError as e:
            logger.error(f"LLM API bad request during verification (invalid model?): {e}")
            return False
        except OpenAIError as e:
            logger.error(f"LLM API error during verification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during LLM API verification: {e}", exc_info=True)
            return False
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.close()
        logger.info("LLM Service client closed")


# 全局LLM服务实例
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    获取全局LLM服务实例
    
    Returns:
        LLM服务实例
    """
    global _llm_service
    
    if _llm_service is None:
        _llm_service = LLMService()
    
    return _llm_service


async def close_llm_service():
    """关闭全局LLM服务实例"""
    global _llm_service
    
    if _llm_service is not None:
        await _llm_service.close()
        _llm_service = None
