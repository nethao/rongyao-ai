"""
LLM API客户端服务
通过阿里云百炼（DashScope）OpenAI 兼容接口调用通义千问，实现AI语义转换功能。

重试策略:
- RateLimitError / APIConnectionError / Timeout: 指数退避重试最多3次
- AuthenticationError / BadRequestError: 不重试，直接抛出
"""
import asyncio
import logging
import re
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
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = base_url or settings.OPENAI_BASE_URL
        
        if not self.api_key:
            raise LLMConfigurationError("百炼 API Key 未配置")
        
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"LLM Service initialized: model={self.model}, endpoint={self.base_url}")
    
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
            api_key = settings.OPENAI_API_KEY
        
        if not api_key:
            raise LLMConfigurationError("百炼 API Key 未配置（数据库和环境变量均为空）")
        
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

        def _strip_media(text: str) -> str:
            if not text:
                return ""
            # markdown 图片语法
            text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', ' ', text)
            # 图片占位符
            text = re.sub(r'\[\[IMG_\d+\]\]', ' ', text)
            # video 占位符
            text = re.sub(r'\[\[VIDEO_BLOCK_\d+\]\]', ' ', text)
            # img/video 标签
            text = re.sub(r'<img\b[^>]*>', ' ', text, flags=re.IGNORECASE)
            text = re.sub(r'<video\b[^>]*>.*?</video>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
            # 去掉其余HTML标签，保留文本
            text = re.sub(r'<[^>]+>', ' ', text)
            return text
        
        # 计算原文中的图片/视频标记数量
        img_markers_count = original.count('![图片')
        img_placeholders_count = len(re.findall(r'\[\[IMG_\d+\]\]', original))
        img_tags_count = len(re.findall(r'<img\b', original, re.IGNORECASE))
        video_tags_count = len(re.findall(r'<video\b', original, re.IGNORECASE))
        media_markers_count = (
            img_markers_count + img_placeholders_count + img_tags_count + video_tags_count
        )

        # 如果原文包含图片/视频，使用“纯文本长度”做校验，避免因媒体占位符过多导致误判
        if media_markers_count >= 1:
            original_text_len = len(_strip_media(original).strip())
            transformed_text_len = len(_strip_media(transformed).strip())
            if original_text_len < 300:
                min_length = max(50, int(original_text_len * 0.3))
            else:
                min_length = max(100, int(original_text_len * 0.5))
            if transformed_text_len < min_length:
                logger.warning(
                    f"Transformed content is too short (text-only): {transformed_text_len} chars "
                    f"(original text: {original_text_len} chars, min expected: {min_length}, "
                    f"media_markers: {media_markers_count})"
                )
                raise LLMTransformError(
                    f"Transformed content is too short ({transformed_len} chars), "
                    f"expected at least {min_length} chars"
                )
        else:
            # 正常情况：允许±50%的长度变化
            min_length = int(original_len * 0.5)
        
        max_length = int(original_len * 1.5)
        
        if transformed_len < min_length:
            logger.warning(
                f"Transformed content is too short: {transformed_len} chars "
                f"(original: {original_len} chars, min expected: {min_length}, "
                f"media_markers: {media_markers_count})"
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
            error_msg = f"百炼认证失败（API Key 无效）: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except BadRequestError as e:
            error_msg = f"请求参数错误: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except InternalServerError as e:
            error_msg = f"百炼服务端错误: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except APIError as e:
            error_msg = f"百炼 API 错误: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except LLMTransformError:
            raise
        except OpenAIError as e:
            error_msg = f"百炼调用异常: {e}"
            logger.error(error_msg)
            raise LLMTransformError(error_msg) from e
        except Exception as e:
            error_msg = f"LLM 转换异常: {e}"
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
            logger.info(f"验证百炼 API 连接: model={self.model}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                timeout=10.0,
            )
            
            if response.choices and response.choices[0].message.content:
                logger.info("百炼 API 连接验证成功")
                return True
            
            logger.warning("百炼 API 返回空响应")
            return False
            
        except (AuthenticationError, RateLimitError, APIConnectionError,
                APITimeoutError, BadRequestError, OpenAIError) as e:
            logger.error(f"百炼 API 验证失败: {e}")
            return False
        except Exception as e:
            logger.error(f"百炼 API 验证异常: {e}", exc_info=True)
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
