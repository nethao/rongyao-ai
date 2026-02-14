# LLM服务错误处理文档

## 概述

LLM服务实现了全面的错误处理和自动重试机制，确保在各种故障场景下系统的稳定性和可靠性。

## 错误类型

### 自定义异常类

```python
from app.services.llm_service import (
    LLMServiceError,        # 基础异常类
    LLMConfigurationError,  # 配置错误
    LLMTransformError       # 转换错误
)
```

#### LLMServiceError
- **描述**: LLM服务的基础异常类
- **用途**: 所有LLM相关异常的父类
- **何时抛出**: 不直接抛出，用于异常继承

#### LLMConfigurationError
- **描述**: LLM配置错误异常
- **用途**: API密钥未配置或配置无效
- **何时抛出**: 
  - 初始化LLMService时API密钥为空
  - 从ConfigService创建实例时API密钥未配置
- **示例**:
  ```python
  try:
      service = LLMService()
  except LLMConfigurationError as e:
      print(f"配置错误: {e}")
  ```

#### LLMTransformError
- **描述**: LLM转换错误异常
- **用途**: 文本转换过程中发生的各种错误
- **何时抛出**:
  - 认证失败（无效API密钥）
  - 请求参数错误
  - OpenAI服务器错误
  - 其他API错误
  - 未预期的异常
- **示例**:
  ```python
  try:
      result = await service.transform_text("测试文本")
  except LLMTransformError as e:
      print(f"转换失败: {e}")
  ```

### OpenAI原生异常

以下OpenAI异常会被自动处理：

#### 会自动重试的异常（最多3次）

1. **RateLimitError** - 速率限制错误
   - **原因**: API调用频率超过限制
   - **重试策略**: 指数退避，初始等待2秒，最大10秒
   - **最终行为**: 3次重试后仍失败则抛出原始异常

2. **APIConnectionError** - 网络连接错误
   - **原因**: 网络连接失败或超时
   - **重试策略**: 指数退避，初始等待2秒，最大10秒
   - **最终行为**: 3次重试后仍失败则抛出原始异常

3. **APITimeoutError** - 请求超时错误
   - **原因**: API请求超时
   - **重试策略**: 指数退避，初始等待2秒，最大10秒
   - **最终行为**: 3次重试后仍失败则抛出原始异常

#### 不会重试的异常（立即失败）

1. **AuthenticationError** - 认证错误
   - **原因**: API密钥无效或过期
   - **处理**: 包装为LLMTransformError并立即抛出
   - **建议**: 检查API密钥配置

2. **BadRequestError** - 请求参数错误
   - **原因**: 请求参数无效（如无效的模型名称）
   - **处理**: 包装为LLMTransformError并立即抛出
   - **建议**: 检查请求参数

3. **InternalServerError** - 服务器内部错误
   - **原因**: OpenAI服务器内部错误
   - **处理**: 包装为LLMTransformError并立即抛出
   - **建议**: 稍后重试或联系OpenAI支持

4. **APIError** - 其他API错误
   - **原因**: 其他未分类的API错误
   - **处理**: 包装为LLMTransformError并立即抛出
   - **建议**: 查看错误详情

## 重试机制

### 配置参数

```python
@retry(
    stop=stop_after_attempt(3),                    # 最多重试3次
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避
    retry=retry_if_exception_type((                # 仅重试特定异常
        RateLimitError,
        APIConnectionError,
        APITimeoutError
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),  # 重试前记录日志
    reraise=True                                   # 重试失败后抛出原始异常
)
```

### 等待时间计算

指数退避策略的等待时间：
- 第1次重试: 2秒
- 第2次重试: 4秒
- 第3次重试: 8秒（不超过10秒上限）

### 重试流程示例

```
请求 → 失败(RateLimitError) → 等待2秒 → 重试1
     → 失败(RateLimitError) → 等待4秒 → 重试2
     → 失败(RateLimitError) → 等待8秒 → 重试3
     → 失败 → 抛出RateLimitError
```

## 日志记录

### 日志级别

- **INFO**: 正常操作（初始化、成功转换、连接验证）
- **WARNING**: 可重试的错误（速率限制、连接错误、超时）
- **ERROR**: 不可重试的错误（认证失败、参数错误、服务器错误）

### 日志示例

```python
# 成功场景
INFO: LLM Service initialized with model: gpt-4
INFO: Calling LLM API with model: gpt-4, text length: 1234
INFO: LLM transformation completed successfully, output length: 1456

# 重试场景
WARNING: Rate limit exceeded, will retry: Rate limit exceeded
WARNING: Retrying in 2 seconds...
INFO: LLM transformation completed successfully, output length: 1456

# 失败场景
ERROR: Authentication failed - invalid API key: Invalid API key
ERROR: Unexpected error during LLM transformation: ...
```

## 使用示例

### 基本使用

```python
from app.services.llm_service import LLMService, LLMTransformError

try:
    service = LLMService(api_key="your-api-key")
    result = await service.transform_text("我是一名工程师")
    print(f"转换结果: {result}")
except LLMTransformError as e:
    print(f"转换失败: {e}")
finally:
    await service.close()
```

### 处理特定错误

```python
from openai import RateLimitError, AuthenticationError
from app.services.llm_service import LLMService, LLMTransformError

try:
    service = LLMService()
    result = await service.transform_text("测试文本")
except RateLimitError:
    # 速率限制错误（已重试3次）
    print("API调用频率过高，请稍后重试")
except LLMTransformError as e:
    # 其他转换错误
    if "Authentication failed" in str(e):
        print("API密钥无效，请检查配置")
    else:
        print(f"转换失败: {e}")
```

### 从ConfigService创建

```python
from app.services.llm_service import LLMService, LLMConfigurationError
from app.database import get_db

try:
    async with get_db() as db:
        service = await LLMService.from_config_service(db)
        result = await service.transform_text("测试文本")
except LLMConfigurationError:
    print("LLM未配置，请先配置API密钥")
except Exception as e:
    print(f"错误: {e}")
```

### 验证连接

```python
from app.services.llm_service import LLMService

service = LLMService(api_key="your-api-key")
is_valid = await service.verify_connection()

if is_valid:
    print("连接正常")
else:
    print("连接失败，请检查API密钥和网络")

await service.close()
```

## 最佳实践

### 1. 始终使用try-except处理异常

```python
# 好的做法
try:
    result = await service.transform_text(text)
except LLMTransformError as e:
    logger.error(f"转换失败: {e}")
    # 处理错误...

# 不好的做法
result = await service.transform_text(text)  # 可能抛出未捕获的异常
```

### 2. 正确关闭服务

```python
# 好的做法
service = LLMService()
try:
    result = await service.transform_text(text)
finally:
    await service.close()

# 或使用全局实例
from app.services.llm_service import get_llm_service
service = get_llm_service()
# 应用关闭时调用 close_llm_service()
```

### 3. 记录详细的错误信息

```python
try:
    result = await service.transform_text(text)
except LLMTransformError as e:
    logger.error(f"转换失败: {e}", exc_info=True)  # 包含堆栈跟踪
    # 向用户返回友好的错误消息
    return {"error": "AI转换服务暂时不可用，请稍后重试"}
```

### 4. 在Celery任务中处理错误

```python
from celery import Task
from app.services.llm_service import LLMService, LLMTransformError

@celery_app.task(bind=True, max_retries=3)
def transform_content_task(self, submission_id: int):
    try:
        service = LLMService()
        # 执行转换...
    except LLMTransformError as e:
        logger.error(f"任务失败: {e}")
        # Celery会自动重试
        raise self.retry(exc=e, countdown=60)
    finally:
        await service.close()
```

### 5. 监控和告警

```python
import time
from app.services.llm_service import LLMService, LLMTransformError

async def transform_with_monitoring(text: str):
    start_time = time.time()
    try:
        service = LLMService()
        result = await service.transform_text(text)
        
        # 记录成功指标
        duration = time.time() - start_time
        logger.info(f"转换成功，耗时: {duration:.2f}秒")
        
        return result
    except LLMTransformError as e:
        # 记录失败指标
        duration = time.time() - start_time
        logger.error(f"转换失败，耗时: {duration:.2f}秒，错误: {e}")
        
        # 发送告警（如果是认证错误）
        if "Authentication failed" in str(e):
            send_alert("LLM API密钥无效")
        
        raise
    finally:
        await service.close()
```

## 故障排查

### 问题: 频繁出现RateLimitError

**原因**: API调用频率超过限制

**解决方案**:
1. 增加请求之间的间隔
2. 使用任务队列限制并发数
3. 升级OpenAI API套餐
4. 实现请求缓存

### 问题: APIConnectionError持续失败

**原因**: 网络连接问题

**解决方案**:
1. 检查网络连接
2. 检查防火墙设置
3. 验证DNS解析
4. 检查代理配置

### 问题: AuthenticationError

**原因**: API密钥无效或过期

**解决方案**:
1. 验证API密钥是否正确
2. 检查API密钥是否过期
3. 确认API密钥有足够的权限
4. 重新生成API密钥

### 问题: 转换结果为空

**原因**: LLM返回空响应

**解决方案**:
1. 检查输入文本是否有效
2. 调整temperature参数
3. 增加max_tokens限制
4. 检查提示词是否合理

## 相关文档

- [API密钥管理文档](./API_KEY_MANAGEMENT.md)
- [OpenAI API文档](https://platform.openai.com/docs/api-reference)
- [Tenacity重试库文档](https://tenacity.readthedocs.io/)
