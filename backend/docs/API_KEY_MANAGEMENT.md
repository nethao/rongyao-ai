# API密钥管理实现文档

## 概述

本文档描述了任务 4.1.2 的实现：为LLM服务实现API密钥管理功能。该实现集成了ConfigService来安全地存储和检索OpenAI API密钥，密钥在数据库中以加密形式存储。

## 实现的功能

### 1. 加密存储API密钥

ConfigService已经支持加密存储配置项。管理员可以通过以下方式设置OpenAI API密钥：

```python
config_service = ConfigService(db)
await config_service.set_config(
    key="openai_api_key",
    value="sk-your-api-key-here",
    encrypted=True,
    description="OpenAI API密钥用于AI语义转换"
)
```

### 2. LLM服务集成

#### 新增的工厂方法

在 `backend/app/services/llm_service.py` 中添加了 `from_config_service` 类方法：

```python
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
        ValueError: 如果API密钥未配置
    """
    from app.services.config_service import ConfigService
    
    config_service = ConfigService(db)
    api_key = await config_service.get_config("openai_api_key", decrypt=True)
    
    if not api_key:
        # 如果数据库中没有配置，尝试从环境变量获取
        api_key = settings.OPENAI_API_KEY
    
    if not api_key:
        raise ValueError("OpenAI API key is not configured in database or environment")
    
    logger.info("LLM Service created from ConfigService")
    return cls(api_key=api_key, model=model)
```

#### 使用示例

```python
# 在异步任务或API端点中使用
from app.services.llm_service import LLMService
from app.database import get_db

async def transform_content(db: AsyncSession, text: str):
    # 从ConfigService创建LLM服务
    llm_service = await LLMService.from_config_service(db)
    
    try:
        # 使用LLM服务进行转换
        transformed = await llm_service.transform_text(text)
        return transformed
    finally:
        await llm_service.close()
```

### 3. 改进的配置验证

更新了 `ConfigService.verify_llm_config()` 方法，现在会实际测试API密钥的有效性：

```python
async def verify_llm_config(self) -> bool:
    """
    验证LLM配置
    
    Returns:
        bool: 配置是否有效
    """
    api_key = await self.get_config("openai_api_key", decrypt=True)
    if not api_key:
        return False
    
    # 实际验证API密钥有效性
    try:
        from app.services.llm_service import LLMService
        llm_service = LLMService(api_key=api_key)
        is_valid = await llm_service.verify_connection()
        await llm_service.close()
        return is_valid
    except Exception as e:
        logger.error(f"LLM config verification failed: {e}")
        return False
```

## 架构设计

### 配置优先级

LLM服务按以下优先级获取API密钥：

1. **数据库配置** (最高优先级): 从 `system_configs` 表中的 `openai_api_key` 配置项
2. **环境变量** (回退): 从 `OPENAI_API_KEY` 环境变量
3. **无配置**: 抛出 `ValueError` 异常

### 安全性

- **加密存储**: API密钥在数据库中使用 Fernet 对称加密存储
- **加密密钥派生**: 从 JWT_SECRET_KEY 派生加密密钥
- **传输安全**: 密钥仅在内存中以明文形式存在，用于API调用
- **访问控制**: 只有管理员角色可以通过API设置和查看配置

### 数据流

```
管理员设置API密钥
    ↓
ConfigService.set_config(encrypted=True)
    ↓
加密密钥 (Fernet)
    ↓
存储到 system_configs 表
    ↓
LLM服务需要时
    ↓
LLMService.from_config_service(db)
    ↓
ConfigService.get_config(decrypt=True)
    ↓
解密密钥
    ↓
创建 OpenAI 客户端
```

## API端点

### 设置API密钥

```http
PUT /api/config
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "key": "openai_api_key",
  "value": "sk-your-api-key-here",
  "encrypted": true,
  "description": "OpenAI API密钥"
}
```

### 验证LLM配置

```http
POST /api/config/verify/llm
Authorization: Bearer <admin-token>

Response:
{
  "valid": true,
  "message": "LLM配置有效"
}
```

### 获取所有配置

```http
GET /api/config
Authorization: Bearer <admin-token>

Response:
{
  "configs": {
    "openai_api_key": "***encrypted***",
    "openai_model": "gpt-4",
    ...
  }
}
```

## 使用场景

### 场景1: 初始配置

管理员首次设置系统时：

1. 登录系统（获取管理员JWT令牌）
2. 通过配置管理界面或API设置 `openai_api_key`
3. 系统自动加密并存储到数据库
4. 验证配置有效性

### 场景2: AI转换任务

当Celery任务需要进行AI转换时：

```python
from app.services.llm_service import LLMService
from app.database import AsyncSessionLocal

async def ai_transform_task(submission_id: int):
    async with AsyncSessionLocal() as db:
        # 从数据库配置创建LLM服务
        llm_service = await LLMService.from_config_service(db)
        
        try:
            # 获取投稿内容
            submission = await get_submission(db, submission_id)
            
            # 执行AI转换
            transformed = await llm_service.transform_text(
                submission.original_content
            )
            
            # 创建草稿
            await create_draft(db, submission_id, transformed)
        finally:
            await llm_service.close()
```

### 场景3: 更新API密钥

当需要更换API密钥时：

1. 管理员通过API更新 `openai_api_key` 配置
2. 新密钥立即生效
3. 后续的LLM服务实例将使用新密钥
4. 无需重启服务

## 测试

### 单元测试

测试文件位于 `backend/app/services/test_api_key_management.py`，包含以下测试用例：

- ✓ 设置加密的API密钥
- ✓ 获取不存在的API密钥
- ✓ 从ConfigService创建LLM服务
- ✓ 从ConfigService创建LLM服务但没有配置密钥
- ✓ LLM服务回退到环境变量
- ✓ 验证有效的LLM配置
- ✓ 验证无效的LLM配置
- ✓ 验证LLM配置但没有密钥
- ✓ 验证LLM配置时发生异常
- ✓ 更新API密钥
- ✓ 加密解密往返
- ✓ 获取所有配置时隐藏加密值

### 运行测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest backend/app/services/test_api_key_management.py -v
```

### 集成测试

独立的集成测试位于 `backend/test_api_key_integration.py`，可以在不依赖完整应用环境的情况下验证功能。

## 验证需求

本实现满足以下需求：

### 需求 8.2: 加密存储API密钥

✓ **实现**: ConfigService 使用 Fernet 加密算法加密存储 API 密钥
✓ **验证**: 数据库中存储的是加密后的密文，不是明文

### 设计文档: ConfigService with encryption support

✓ **实现**: ConfigService 提供 `set_config()` 和 `get_config()` 方法，支持 `encrypted` 参数
✓ **实现**: LLMService 提供 `from_config_service()` 工厂方法
✓ **实现**: ConfigService 提供 `verify_llm_config()` 方法实际测试 API 密钥

## 相关文件

### 修改的文件

1. `backend/app/services/llm_service.py`
   - 添加 `from_config_service()` 类方法
   - 添加 `AsyncSession` 导入

2. `backend/app/services/config_service.py`
   - 改进 `verify_llm_config()` 方法
   - 添加 `logging` 导入

### 新增的文件

1. `backend/app/services/test_api_key_management.py`
   - 完整的单元测试套件

2. `backend/test_api_key_integration.py`
   - 独立的集成测试

3. `backend/docs/API_KEY_MANAGEMENT.md`
   - 本文档

## 后续任务

本任务完成后，可以继续执行：

- **任务 4.1.3**: 实现请求重试和错误处理
- **任务 4.1.4**: 实现响应解析
- **任务 4.2.x**: 转换提示词工程
- **任务 4.3.x**: AI转换任务实现

## 注意事项

1. **环境变量回退**: 系统支持从环境变量读取 API 密钥作为回退方案，便于开发和测试
2. **密钥轮换**: 更新 API 密钥后立即生效，无需重启服务
3. **错误处理**: 如果 API 密钥未配置，LLM 服务会抛出明确的 `ValueError` 异常
4. **日志记录**: 所有关键操作都有日志记录，便于调试和监控
5. **权限控制**: 只有管理员角色可以访问配置管理 API

## 总结

任务 4.1.2 已成功实现，提供了：

- ✅ 加密存储 OpenAI API 密钥到数据库
- ✅ LLM 服务与 ConfigService 的集成
- ✅ 从数据库配置创建 LLM 服务实例的工厂方法
- ✅ 改进的配置验证功能
- ✅ 完整的测试覆盖
- ✅ 详细的文档说明

系统现在可以安全地管理 LLM API 密钥，支持通过管理员界面动态配置，无需修改代码或重启服务。
