# 需求文档 - 荣耀AI审核发布系统

## 简介

荣耀AI审核发布系统 (Glory AI Audit System) 是一个独立的内容中转与自动化处理平台，旨在解决多站点（A/B/C/D站）Wordpress 投稿处理效率低下的痛点。系统通过自动化邮件抓取、AI智能语义转换和独立审核分发后台，实现从投稿接收到内容发布的全流程自动化处理。

## 术语表

- **System**: 荣耀AI审核发布系统
- **IMAP_Fetcher**: 邮件抓取引擎模块
- **AI_Transformer**: AI智能语义转换模块
- **Audit_Dashboard**: 审核分发后台模块
- **Administrator**: 系统管理员，负责底层配置
- **Editor**: 编辑人员，负责审核和发布内容
- **Submission**: 投稿内容，包含文档和图片
- **OSS**: 阿里云对象存储服务
- **WordPress_Site**: 目标发布站点（A/B/C/D站）
- **Draft**: 草稿，AI转换后待审核的内容
- **Original_Content**: 原始投稿内容
- **Transformed_Content**: AI转换后的内容

## 需求

### 需求 1: 邮件抓取与内容提取

**用户故事:** 作为系统，我需要自动监听邮箱并提取投稿内容，以便编辑人员无需手动处理邮件。

#### 验收标准

1. WHEN 邮箱收到新邮件 THEN THE IMAP_Fetcher SHALL 在5分钟内检测到新邮件
2. WHEN 邮件包含.doc附件 THEN THE IMAP_Fetcher SHALL 将其转换为.docx格式
3. WHEN 邮件包含.docx附件 THEN THE IMAP_Fetcher SHALL 提取文档中的文本内容和图片
4. WHEN 文档中包含图片 THEN THE IMAP_Fetcher SHALL 上传图片到OSS并记录URL
5. WHEN 提取完成 THEN THE System SHALL 创建Submission记录并存储到数据库

### 需求 2: 文档格式转换

**用户故事:** 作为系统，我需要支持多种文档格式，以便处理不同格式的投稿。

#### 验收标准

1. WHEN 接收到.doc格式文档 THEN THE System SHALL 使用LibreOffice转换为.docx格式
2. WHEN 转换失败 THEN THE System SHALL 记录错误日志并通知管理员
3. WHEN 转换成功 THEN THE System SHALL 保留原始文件并标记转换状态

### 需求 3: AI智能语义转换

**用户故事:** 作为编辑人员，我需要AI自动将第一人称内容转换为第三人称，以便符合发布规范。

#### 验收标准

1. WHEN Submission创建完成 THEN THE AI_Transformer SHALL 自动触发语义转换任务
2. WHEN 进行语义转换 THEN THE AI_Transformer SHALL 将第一人称叙述转换为第三人称叙述
3. WHEN 内容包含引用标记 THEN THE AI_Transformer SHALL 保护引用内容不被修改
4. WHEN 内容包含时间表述 THEN THE AI_Transformer SHALL 规范化时间格式（如"昨天"转换为具体日期）
5. WHEN 转换完成 THEN THE System SHALL 创建Draft记录并关联Original_Content

### 需求 4: 图片处理与存储

**用户故事:** 作为系统，我需要自动处理和存储图片，以便减少手动上传工作。

#### 验收标准

1. WHEN 提取到图片 THEN THE System SHALL 上传图片到阿里云OSS
2. WHEN 上传成功 THEN THE System SHALL 记录图片URL和元数据
3. WHEN 上传失败 THEN THE System SHALL 重试最多3次
4. WHEN 重试仍失败 THEN THE System SHALL 记录错误并标记Submission状态

### 需求 5: 审核对比界面

**用户故事:** 作为编辑人员，我需要双栏对比界面查看原文和AI改写版本，以便快速审核内容质量。

#### 验收标准

1. WHEN 编辑人员打开Draft THEN THE Audit_Dashboard SHALL 显示左栏原文和右栏改写版本
2. WHEN 显示内容 THEN THE Audit_Dashboard SHALL 高亮显示差异部分
3. WHEN 编辑人员修改右栏内容 THEN THE System SHALL 实时保存修改
4. WHEN 编辑人员点击"恢复原文" THEN THE System SHALL 将右栏内容恢复为AI转换版本

### 需求 6: 版本管理

**用户故事:** 作为编辑人员，我需要查看和恢复历史版本，以便在需要时回退修改。

#### 验收标准

1. WHEN 编辑人员保存修改 THEN THE System SHALL 创建新版本记录
2. WHEN 编辑人员查看版本历史 THEN THE System SHALL 显示所有历史版本及时间戳
3. WHEN 编辑人员选择历史版本 THEN THE System SHALL 恢复该版本内容到编辑器
4. THE System SHALL 保留最近30个版本记录

### 需求 7: WordPress站点发布

**用户故事:** 作为编辑人员，我需要一键发布内容到指定WordPress站点，以便快速完成发布流程。

#### 验收标准

1. WHEN 编辑人员点击"发布" THEN THE System SHALL 显示可用WordPress_Site列表
2. WHEN 编辑人员选择目标站点 THEN THE System SHALL 使用WordPress REST API发布内容
3. WHEN 发布成功 THEN THE System SHALL 记录发布时间和目标站点
4. WHEN 发布失败 THEN THE System SHALL 显示错误信息并保留Draft状态
5. WHEN 内容包含图片 THEN THE System SHALL 在发布时使用OSS图片URL

### 需求 8: 系统配置管理

**用户故事:** 作为管理员，我需要配置API密钥和站点信息，以便系统正常运行。

#### 验收标准

1. WHERE 管理员权限 THEN THE System SHALL 提供配置管理界面
2. WHEN 管理员配置LLM API密钥 THEN THE System SHALL 加密存储密钥
3. WHEN 管理员配置WordPress站点信息 THEN THE System SHALL 验证连接可用性
4. WHEN 管理员配置OSS信息 THEN THE System SHALL 验证存储桶访问权限
5. WHEN 管理员配置IMAP信息 THEN THE System SHALL 验证邮箱连接

### 需求 9: 用户认证与授权

**用户故事:** 作为系统，我需要验证用户身份和权限，以便保护系统安全。

#### 验收标准

1. WHEN 用户登录 THEN THE System SHALL 验证用户名和密码
2. WHEN 验证成功 THEN THE System SHALL 生成JWT令牌
3. WHEN 用户访问受保护资源 THEN THE System SHALL 验证JWT令牌有效性
4. WHERE 管理员权限 THEN THE System SHALL 允许访问配置管理功能
5. WHERE 编辑人员权限 THEN THE System SHALL 允许访问审核和发布功能

### 需求 10: 数据清理策略

**用户故事:** 作为管理员，我需要自动清理历史数据，以便控制存储成本。

#### 验收标准

1. WHEN 图片存储超过365天 THEN THE System SHALL 压缩图片质量到原始的60%
2. WHEN 数据存储超过730天 THEN THE System SHALL 删除Submission和Draft记录
3. WHEN 执行清理操作 THEN THE System SHALL 记录清理日志
4. THE System SHALL 每天凌晨2点执行清理任务

### 需求 11: 异步任务处理

**用户故事:** 作为系统，我需要异步处理耗时任务，以便不阻塞用户操作。

#### 验收标准

1. WHEN 触发邮件抓取任务 THEN THE System SHALL 使用Celery异步执行
2. WHEN 触发AI转换任务 THEN THE System SHALL 使用Celery异步执行
3. WHEN 任务执行中 THEN THE System SHALL 更新任务状态到Redis
4. WHEN 任务完成 THEN THE System SHALL 通知前端更新界面
5. WHEN 任务失败 THEN THE System SHALL 记录错误并支持手动重试

### 需求 12: 系统监控与日志

**用户故事:** 作为管理员，我需要查看系统运行状态和日志，以便及时发现和解决问题。

#### 验收标准

1. WHEN 系统运行 THEN THE System SHALL 记录所有关键操作日志
2. WHEN 发生错误 THEN THE System SHALL 记录详细错误堆栈
3. WHERE 管理员权限 THEN THE System SHALL 提供日志查询界面
4. THE System SHALL 显示当前任务队列状态和系统资源使用情况

### 需求 13: 性能要求

**用户故事:** 作为用户，我需要系统快速响应，以便提高工作效率。

#### 验收标准

1. WHEN 用户访问审核界面 THEN THE System SHALL 在2秒内加载完成
2. WHEN 用户保存修改 THEN THE System SHALL 在1秒内完成保存
3. WHEN 系统处理单个投稿 THEN THE System SHALL 在10分钟内完成AI转换
4. THE System SHALL 支持至少10个并发用户同时操作

### 需求 14: 系统资源要求

**用户故事:** 作为系统管理员，我需要了解系统资源需求，以便准备合适的硬件环境。

#### 验收标准

1. THE System SHALL 在至少8GB内存的环境中运行
2. THE System SHALL 需要至少20GB磁盘空间用于临时文件
3. WHEN 安装LibreOffice THEN THE System SHALL 需要额外2GB磁盘空间
4. THE System SHALL 支持Linux操作系统环境
