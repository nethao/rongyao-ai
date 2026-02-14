# 荣耀AI审核发布系统 - 项目总结

## 项目概述

**项目名称**: 荣耀AI审核发布系统  
**开发时间**: 2026年2月13日-15日  
**技术栈**: Vue 3 + FastAPI + PostgreSQL + Redis + Celery + TinyMCE  
**部署方式**: Docker Compose  
**访问地址**: http://e.com

## 核心功能

### 1. 邮件抓取与内容处理
- ✅ 自动抓取QQ邮箱投稿
- ✅ 支持公众号链接、美篇链接、Word文档
- ✅ 图片自动上传到阿里云OSS
- ✅ 保留公众号原始HTML排版

### 2. AI内容转换
- ✅ 使用DeepSeek API进行内容优化
- ✅ 图片占位符保护机制
- ✅ 智能长度验证（考虑图片数量）
- ✅ 手动触发AI转换（非自动）

### 3. 富文本编辑器
- ✅ TinyMCE编辑器集成
- ✅ 三栏布局：原文预览 + 编辑器 + 版本历史
- ✅ 公众号排版引擎（677px标准宽度）
- ✅ 快照系统（本地快速回滚）
- ✅ 版本历史（数据库持久化）

### 4. 发布管理
- ✅ 多站点WordPress发布
- ✅ 站点配置管理
- ✅ 发布状态跟踪

## 当前状态

### ✅ 已完成功能

1. **邮件抓取系统**
   - 文件: `backend/app/tasks/email_tasks.py`
   - 状态: 完整实现
   - 功能: 抓取、解析、上传图片、创建草稿

2. **公众号排版引擎**
   - 文件: `frontend/src/views/AuditView.vue`
   - 状态: 已实现，待验证
   - 功能: 保留section嵌套、内联样式、SVG支持

3. **AI转换流程**
   - 文件: `backend/app/tasks/transform_tasks.py`
   - 状态: 完整实现
   - 功能: 占位符保护、图片位置保留

4. **草稿管理**
   - 文件: `backend/app/services/draft_service.py`
   - 状态: 完整实现
   - 功能: 创建、更新、版本管理

### ⚠️ 待验证功能

1. **公众号排版显示**
   - 状态: 已修复（2026-02-15）
   - 修复: 简化 iframe 注入样式，不覆盖正文内联样式；抓取增加浏览器请求头
   - 建议: 刷新草稿页验证「原始内容」与公众号一致

2. **TinyMCE中文语言包**
   - 状态: 已配置`language: 'zh_CN'`
   - 待验证: 是否需要下载语言文件

### ❌ 未实现功能

1. **WordPress发布功能**
   - 状态: API已实现，未测试
   - 文件: `backend/app/services/publish_service.py`

2. **用户权限管理**
   - 状态: 基础认证已实现
   - 待完善: 角色权限控制

## 数据库结构

### 核心表

1. **submissions** (投稿表)
   - `id`: 主键
   - `email_subject`: 邮件标题
   - `original_content`: Markdown格式原文
   - `original_html`: 公众号原始HTML（新增）
   - `cooperation_type`: 合作方式（投稿/合作）
   - `media_type`: 媒体类型（荣耀/时代/正贤等）
   - `source_unit`: 来稿单位
   - `status`: 状态（completed）

2. **drafts** (草稿表)
   - `id`: 主键
   - `submission_id`: 关联投稿
   - `current_content`: 当前内容
   - `current_version`: 当前版本号
   - `status`: 状态（draft/published）

3. **draft_versions** (版本历史表)
   - `id`: 主键
   - `draft_id`: 关联草稿
   - `version_number`: 版本号
   - `content`: 版本内容
   - `created_by`: 创建者

4. **submission_images** (图片表)
   - `id`: 主键
   - `submission_id`: 关联投稿
   - `oss_url`: OSS地址
   - `oss_key`: OSS键名

## 工作流程

### 当前流程（2026-02-15）

```
邮件抓取
    ↓
解析内容（公众号/Word/美篇）
    ↓
上传图片到OSS
    ↓
保存原始HTML（公众号）
    ↓
创建投稿记录（status: completed）
    ↓
自动创建原文草稿
    ↓
【编辑人员操作】
    ├─→ 点击"查看草稿" → 手动编辑
    └─→ 点击"AI转换" → AI优化内容
```

### 关键改动历史

1. **2026-02-14 上午**: 初始实现，AI自动转换
2. **2026-02-14 下午**: 改为手动触发AI转换
3. **2026-02-14 晚上**: 添加原始HTML保存
4. **2026-02-15 凌晨**: 修复公众号排版引擎
5. **2026-02-15**: 公众号排版与图片完整落地——DraftDetailSchema 增加 `original_html`；HTML 内图片按 `<img>` 顺序替换为 OSS 地址（BeautifulSoup 按序赋值，避免转义导致替换失败）；iframe 仅注入基础样式不覆盖内联

**邮件四种来源**：公众号(已实现) / 美篇 / Word / 视频。详见 `docs/weixin-layout-engine.md`。

## 技术细节

### 公众号排版引擎

**核心原理**:
- 盒模型: `box-sizing: border-box !important`
- 容器宽度: `max-width: 677px`
- 居中显示: `margin: 0 auto`
- 保留内联样式: 不删除任何`style`属性

**关键文件**:
- 前端: `frontend/src/views/AuditView.vue`
- 后端: `backend/app/services/web_fetcher.py`
- 文档: `docs/weixin-layout-engine.md`

**CSS关键配置**:
```css
.html-preview .rich_media_content {
  overflow: visible !important;
  max-width: 677px;
  margin: 0 auto;
  font-size: 17px;
}

.html-preview .rich_media_content * {
  box-sizing: border-box !important;
}
```

### 图片处理流程

1. **抓取阶段**: 
   - 提取`data-src`或`src`
   - 下载图片到内存

2. **上传阶段**:
   - 上传到OSS: `submissions/{id}/YYYYMMDD_HHMMSS_{hash}.jpg`
   - 记录URL映射

3. **替换阶段**:
   - Markdown: `![图片N](OSS_URL)`
   - HTML: `<img src="OSS_URL">`（同时保留`data-src`）

### AI转换机制

**占位符保护**:
```python
# 提取图片
images = re.findall(r'!\[图片\d+\]\([^)]+\)', content)
for i, img in enumerate(images):
    content = content.replace(img, f'[IMAGE_PLACEHOLDER_{i}]')

# AI处理
transformed = llm_service.transform(content)

# 还原图片
for i, img in enumerate(images):
    transformed = transformed.replace(f'[IMAGE_PLACEHOLDER_{i}]', img)
```

## 测试数据

### 投稿记录

| ID | 标题 | 状态 | 草稿数 | 图片数 | 备注 |
|----|------|------|--------|--------|------|
| 13 | 2026新生活·新风尚·新年画艺术展 | completed | 1 | 42 | 早期测试 |
| 14 | 2026新生活·新风尚·新年画艺术展（第二期） | completed | 0 | 42 | 清空后测试 |
| 15 | 测试文章2 | completed | 0 | 42 | 流程测试 |
| 17 | 完整流程测试 | completed | 1 | 42 | 新流程测试 |
| 18 | 保留排版测试 | completed | 1 | 42 | HTML保存测试 |
| 19 | 新流程测试 | pending | 0 | 42 | 失败案例 |
| 20 | 最终排版测试 | completed | 1 | 42 | OSS URL测试 |
| 21 | 完美排版 | completed | 1 | 42 | **当前测试用例** |

### 测试用公众号链接
```
https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ
```

## 快捷脚本

### 模拟邮件抓取
```bash
./scripts/mock.sh "公众号链接" "文章标题"

# 示例
./scripts/mock.sh "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ" "测试文章"
```

### 查看日志
```bash
# 后端日志
sudo docker-compose logs backend -f

# Celery日志
sudo docker-compose logs celery_worker -f

# 前端日志
sudo docker-compose logs frontend -f
```

### 重启服务
```bash
# 重启所有服务
sudo docker-compose restart

# 重启特定服务
sudo docker-compose restart backend
sudo docker-compose restart frontend
sudo docker-compose restart celery_worker
```

### 数据库操作
```bash
# 进入数据库
sudo docker-compose exec db psql -U postgres -d rongyao_ai

# 查看投稿
SELECT id, email_subject, status, 
       (SELECT COUNT(*) FROM drafts WHERE submission_id = submissions.id) as draft_count,
       (SELECT COUNT(*) FROM submission_images WHERE submission_id = submissions.id) as image_count
FROM submissions ORDER BY id DESC;

# 清空数据
DELETE FROM draft_versions;
DELETE FROM drafts;
DELETE FROM submission_images;
DELETE FROM submissions;
```

## 配置文件

### 环境变量 (.env)
```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/rongyao_ai

# Redis
REDIS_URL=redis://redis:6379/0

# OSS
OSS_ACCESS_KEY_ID=your_key
OSS_ACCESS_KEY_SECRET=your_secret
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BUCKET_NAME=rongyao-ai-test

# DeepSeek
DEEPSEEK_API_KEY=your_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# JWT
SECRET_KEY=your_secret_key
```

### Docker Compose服务
- `db`: PostgreSQL 14
- `redis`: Redis 7
- `backend`: FastAPI (端口8000)
- `frontend`: Vue 3 + Vite (端口3000)
- `celery_worker`: Celery异步任务
- `nginx_proxy`: Nginx反向代理
- `wp_a/b/c/d`: WordPress站点

## 已知问题

### 1. 公众号排版显示问题
**问题**: 投稿21显示为简单图文，未显示复杂排版  
**原因**: CSS选择器`:deep()`可能不生效  
**修复**: 已改为全局样式，待验证  
**验证方法**: 刷新页面，查看投稿21的"查看草稿"

### 2. TinyMCE语言包
**问题**: 可能缺少中文语言文件  
**状态**: 已配置`language: 'zh_CN'`  
**待验证**: 是否需要手动下载语言包

### 3. 前端容器IP变化
**问题**: 重启后前端IP变化导致nginx 502  
**解决**: 重启nginx_proxy  
**命令**: `sudo docker restart nginx_proxy`

## 下一步计划

### 优先级1（核心功能）
- [ ] 验证公众号排版显示
- [ ] 测试WordPress发布功能
- [ ] 完善错误处理和日志

### 优先级2（用户体验）
- [ ] 添加加载动画
- [ ] 优化图片加载速度
- [ ] 添加操作提示

### 优先级3（扩展功能）
- [ ] 支持美篇排版
- [ ] 支持Word文档排版
- [ ] 添加图片编辑功能

## 联系方式

**项目路径**: `/home/nethao/rongyao-ai`  
**访问地址**: http://e.com  
**数据库**: PostgreSQL (端口5432)  
**Redis**: 端口6379

## 备注

- 所有图片存储在阿里云OSS: `rongyao-ai-test`
- 测试账号: admin / admin123
- 公众号标准宽度: 677px
- 图片命名格式: `YYYYMMDD_HHMMSS_{hash}.jpg`

---

**最后更新**: 2026-02-15 01:07  
**文档版本**: 1.0  
**状态**: 开发中
