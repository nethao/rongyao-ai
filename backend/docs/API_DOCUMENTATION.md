# 荣耀AI审核发布系统 - API文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API版本**: v1.0
- **认证方式**: JWT Bearer Token

## 认证

所有需要认证的接口都需要在请求头中包含JWT令牌：

```
Authorization: Bearer <your-jwt-token>
```

### 登录

**POST** `/api/auth/login`

获取JWT令牌。

**请求体**:
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 登出

**POST** `/api/auth/logout`

登出当前用户。

**响应**:
```json
{
  "message": "登出成功"
}
```

## 投稿管理

### 获取投稿列表

**GET** `/api/submissions`

获取投稿列表，支持分页和筛选。

**查询参数**:
- `page` (int): 页码，默认1
- `size` (int): 每页数量，默认20
- `status` (string): 状态筛选 (pending/processing/completed/failed)

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "email_subject": "投稿标题",
      "email_from": "user@example.com",
      "email_date": "2024-01-01T10:00:00Z",
      "status": "completed",
      "created_at": "2024-01-01T10:05:00Z",
      "images": [
        {
          "id": 1,
          "oss_url": "https://bucket.oss.com/image.jpg",
          "original_filename": "image.jpg"
        }
      ]
    }
  ],
  "total": 100,
  "page": 1,
  "size": 20
}
```

### 获取投稿详情

**GET** `/api/submissions/{id}`

获取单个投稿的详细信息。

**响应**:
```json
{
  "id": 1,
  "email_subject": "投稿标题",
  "email_from": "user@example.com",
  "original_content": "原始内容...",
  "status": "completed",
  "images": [...],
  "drafts": [...]
}
```

### 触发AI转换

**POST** `/api/submissions/{id}/transform`

手动触发AI转换任务。

**响应**:
```json
{
  "task_id": "abc123-def456",
  "message": "AI转换任务已启动"
}
```

## 草稿管理

### 获取草稿详情

**GET** `/api/drafts/{id}`

获取草稿详情，包含原文和转换后的内容。

**响应**:
```json
{
  "id": 1,
  "submission_id": 1,
  "current_content": "转换后的内容...",
  "original_content": "原始内容...",
  "current_version": 3,
  "status": "draft",
  "created_at": "2024-01-01T10:10:00Z"
}
```

### 更新草稿

**PUT** `/api/drafts/{id}`

更新草稿内容，会自动创建新版本。

**请求体**:
```json
{
  "content": "修改后的内容..."
}
```

**响应**:
```json
{
  "id": 1,
  "current_content": "修改后的内容...",
  "current_version": 4,
  "updated_at": "2024-01-01T11:00:00Z"
}
```

### 获取版本历史

**GET** `/api/drafts/{id}/versions`

获取草稿的所有历史版本。

**响应**:
```json
{
  "versions": [
    {
      "id": 3,
      "version_number": 3,
      "content": "版本3的内容...",
      "created_at": "2024-01-01T10:50:00Z"
    },
    {
      "id": 2,
      "version_number": 2,
      "content": "版本2的内容...",
      "created_at": "2024-01-01T10:30:00Z"
    }
  ]
}
```

### 恢复版本

**POST** `/api/drafts/{id}/restore`

恢复到指定版本。

**请求体**:
```json
{
  "version_id": 2
}
```

### 恢复AI版本

**POST** `/api/drafts/{id}/restore-ai`

恢复到AI转换的原始版本（版本1）。

### 发布到WordPress

**POST** `/api/drafts/{id}/publish`

发布草稿到指定的WordPress站点。

**请求体**:
```json
{
  "site_id": 1
}
```

**响应**:
```json
{
  "success": true,
  "wordpress_post_id": 123,
  "message": "成功发布到 A站",
  "site_name": "A站"
}
```

## WordPress站点管理

### 获取站点列表

**GET** `/api/wordpress/sites`

获取所有WordPress站点。

**查询参数**:
- `active_only` (bool): 只返回激活的站点，默认false

**响应**:
```json
{
  "sites": [
    {
      "id": 1,
      "name": "A站",
      "url": "https://site-a.com",
      "active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 4
}
```

### 创建站点

**POST** `/api/wordpress/sites` (仅管理员)

创建新的WordPress站点。

**请求体**:
```json
{
  "name": "A站",
  "url": "https://site-a.com",
  "api_username": "admin",
  "api_password": "password123",
  "active": true
}
```

### 更新站点

**PUT** `/api/wordpress/sites/{id}` (仅管理员)

更新站点信息。

**请求体**:
```json
{
  "name": "A站（更新）",
  "active": false
}
```

### 删除站点

**DELETE** `/api/wordpress/sites/{id}` (仅管理员)

删除站点。

### 验证站点连接

**POST** `/api/wordpress/sites/{id}/verify` (仅管理员)

验证WordPress站点连接是否正常。

**响应**:
```json
{
  "valid": true,
  "message": "连接成功"
}
```

## 系统配置

### 获取配置

**GET** `/api/config` (仅管理员)

获取系统配置列表。

**响应**:
```json
{
  "configs": {
    "llm_api_key": "sk-***",
    "oss_bucket": "my-bucket",
    "imap_host": "imap.example.com"
  }
}
```

### 更新配置

**PUT** `/api/config` (仅管理员)

更新配置项。

**请求体**:
```json
{
  "key": "llm_api_key",
  "value": "sk-new-key",
  "encrypted": true
}
```

### 验证LLM配置

**POST** `/api/config/verify/llm` (仅管理员)

验证LLM API配置。

**响应**:
```json
{
  "valid": true,
  "message": "LLM API连接成功"
}
```

### 验证OSS配置

**POST** `/api/config/verify/oss` (仅管理员)

验证OSS配置。

### 验证IMAP配置

**POST** `/api/config/verify/imap` (仅管理员)

验证IMAP邮箱配置。

## 系统监控

### 获取任务日志

**GET** `/api/monitoring/logs` (仅管理员)

获取系统任务日志。

**查询参数**:
- `task_type` (string): 任务类型筛选
- `status` (string): 状态筛选
- `limit` (int): 返回数量，默认100
- `offset` (int): 偏移量，默认0

**响应**:
```json
{
  "logs": [
    {
      "id": 1,
      "task_type": "fetch_email",
      "task_id": "abc123",
      "status": "success",
      "message": "成功抓取5封邮件",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ],
  "total": 50
}
```

### 获取系统统计

**GET** `/api/monitoring/stats` (仅管理员)

获取系统统计信息。

**响应**:
```json
{
  "total_submissions": 150,
  "total_drafts": 145,
  "total_published": 120,
  "pending_submissions": 5,
  "failed_tasks_24h": 2,
  "successful_tasks_24h": 48
}
```

### 健康检查

**GET** `/api/monitoring/health`

系统健康检查端点。

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 错误响应

所有API错误都遵循统一格式：

```json
{
  "detail": "错误描述信息"
}
```

### HTTP状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `204 No Content`: 删除成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 无权限
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器错误

## 速率限制

- 普通用户: 100请求/分钟
- 管理员: 200请求/分钟

超过限制会返回 `429 Too Many Requests`。

## 交互式文档

访问 `http://localhost:8000/docs` 查看Swagger UI交互式API文档。
