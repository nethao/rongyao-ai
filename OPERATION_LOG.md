# 操作记录 - 详细日志

## 2026-02-14 (第一天)

### 上午：基础功能实现

**08:00-10:00 图片上传OSS**
- 修改文件: `backend/app/tasks/email_tasks.py`
- 添加功能: 图片上传到阿里云OSS
- 测试结果: 投稿13，42张图片上传成功

**10:00-12:00 图片位置保留**
- 修改文件: `backend/app/services/web_fetcher.py`
- 实现方法: 使用`[IMAGE_N]`占位符
- 结果: 图文混排位置正确

### 下午：AI转换优化

**14:00-16:00 AI转换图片保护**
- 修改文件: `backend/app/tasks/transform_tasks.py`
- 添加功能: `[IMAGE_PLACEHOLDER_N]`占位符
- 修改文件: `backend/app/services/prompt_builder.py`
- 添加规则: 指示LLM保留占位符

**16:00-17:00 长度验证优化**
- 修改文件: `backend/app/services/llm_service.py`
- 添加逻辑: 图片数量>10时动态调整最小长度
- 公式: `min_length = max(100, estimated_text * 0.3)`

### 晚上：编辑器集成

**17:00-18:00 TinyMCE安装**
- 执行命令: `npm install tinymce@6.8.2`
- 创建文件: `frontend/src/utils/markdown.js`
- 功能: Markdown ↔ HTML转换

**18:00-19:00 AuditView更新**
- 修改文件: `frontend/src/views/AuditView.vue`
- 替换: Monaco → TinyMCE
- 配置: 公众号兼容参数

**19:00-20:00 修复错误**
- 问题: CSS语法错误（未闭合括号）
- 问题: `htmlToMarkdown`未导入
- 问题: bcrypt版本冲突
- 解决: 逐一修复

## 2026-02-14 晚上：工作流程调整

**20:00-21:00 修改工作流程**
- 需求: 邮件抓取 → 生成草稿 → 手动选择AI转换
- 修改文件: `backend/app/tasks/email_tasks.py`
- 移除: 自动触发AI转换
- 添加: 自动创建原文草稿

**21:00-22:00 前端按钮逻辑**
- 修改文件: `frontend/src/views/SubmissionsView.vue`
- 逻辑: 有草稿显示"查看草稿"+"AI转换"
- 逻辑: 无草稿显示"AI转换"

**22:00-23:00 创建模拟脚本**
- 创建文件: `backend/mock_email.py`
- 创建文件: `scripts/mock.sh`
- 功能: 快速模拟邮件抓取
- 用法: `./scripts/mock.sh "链接" "标题"`

## 2026-02-15 凌晨：排版引擎

**00:00-01:00 保存原始HTML**
- 修改文件: `backend/app/models/submission.py`
- 添加字段: `original_html TEXT`
- 执行SQL: `ALTER TABLE submissions ADD COLUMN original_html TEXT`

**01:00-02:00 HTML抓取优化**
- 修改文件: `backend/app/services/web_fetcher.py`
- 功能1: 移除`visibility: hidden`样式
- 功能2: 转换`data-src`为`src`
- 功能3: 保存完整HTML结构

**02:00-03:00 URL替换逻辑**
- 修改文件: `backend/app/tasks/email_tasks.py`
- 问题: original_html在替换OSS URL前保存
- 修复: 调整保存顺序
- 修复: 替换后再次转换data-src为src

**03:00-04:00 前端样式调整**
- 修改文件: `frontend/src/views/AuditView.vue`
- 添加: 公众号专用CSS
- 配置: 677px宽度，居中显示
- 配置: `box-sizing: border-box`

**04:00-05:00 排版引擎优化**
- 参考: 专业公众号排版引擎方案
- 修改: 注入微信官方基础样式
- 修改: TinyMCE支持SVG元素
- 修改: 移除`:deep()`选择器

## 关键命令记录

### 容器操作
```bash
# 重启后端
sudo docker-compose restart backend celery_worker

# 重启前端
sudo docker-compose restart frontend

# 重启所有
sudo docker-compose restart

# 查看日志
sudo docker-compose logs backend -f
sudo docker-compose logs celery_worker -f
```

### 数据库操作
```bash
# 清空数据
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def clear():
    async for db in get_db():
        await db.execute(text('DELETE FROM draft_versions'))
        await db.execute(text('DELETE FROM drafts'))
        await db.execute(text('DELETE FROM submission_images'))
        await db.execute(text('DELETE FROM submissions'))
        await db.commit()
        break

asyncio.run(clear())
"

# 添加字段
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def add_column():
    async for db in get_db():
        await db.execute(text('ALTER TABLE submissions ADD COLUMN IF NOT EXISTS original_html TEXT'))
        await db.commit()
        break

asyncio.run(add_column())
"

# 查看数据
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        result = await db.execute(text('SELECT id, email_subject, status FROM submissions ORDER BY id DESC LIMIT 5'))
        for row in result:
            print(f'ID: {row[0]}, 标题: {row[1]}, 状态: {row[2]}')
        break

asyncio.run(check())
"
```

### 测试命令
```bash
# 模拟抓取
./scripts/mock.sh "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ" "测试文章"

# 检查结果
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        result = await db.execute(text('SELECT id, email_subject, (SELECT COUNT(*) FROM drafts WHERE submission_id = submissions.id) as draft_count, (SELECT COUNT(*) FROM submission_images WHERE submission_id = submissions.id) as image_count FROM submissions ORDER BY id DESC LIMIT 1'))
        row = result.fetchone()
        if row:
            print(f'投稿ID: {row[0]}')
            print(f'标题: {row[1]}')
            print(f'草稿数: {row[2]}')
            print(f'图片数: {row[3]}')
        break

asyncio.run(check())
"
```

## 文件修改清单

### 后端文件
1. `backend/app/tasks/email_tasks.py` - 15次修改
   - 图片上传OSS
   - URL替换逻辑
   - 原始HTML保存
   - 移除自动AI转换
   - 自动创建草稿

2. `backend/app/tasks/transform_tasks.py` - 6次修改
   - 占位符保护
   - 图片位置保留

3. `backend/app/services/web_fetcher.py` - 3次修改
   - 图片位置保留
   - 原始HTML保存
   - 样式清理

4. `backend/app/services/llm_service.py` - 3次修改
   - 长度验证优化

5. `backend/app/services/prompt_builder.py` - 1次修改
   - 占位符保护规则

6. `backend/app/models/submission.py` - 2次修改
   - 添加original_html字段
   - 修复语法错误

7. `backend/app/api/drafts.py` - 2次修改
   - 返回original_html
   - 修复参数名

8. `backend/app/schemas/submission.py` - 1次修改
   - compressed字段允许None

### 前端文件
1. `frontend/src/views/AuditView.vue` - 20次修改
   - 替换Monaco为TinyMCE
   - 添加公众号样式
   - 快照系统
   - 版本管理

2. `frontend/src/views/SubmissionsView.vue` - 8次修改
   - 按钮逻辑调整
   - 显示优化

3. `frontend/src/utils/markdown.js` - 新建
   - Markdown转HTML
   - HTML转Markdown

### 脚本文件
1. `backend/mock_email.py` - 新建
2. `scripts/mock.sh` - 新建
3. `scripts/README.md` - 新建

### 文档文件
1. `docs/weixin-layout-engine.md` - 新建
2. `PROJECT_SUMMARY.md` - 新建
3. `OPERATION_LOG.md` - 本文件

## 测试记录

### 投稿测试
| 测试时间 | 投稿ID | 标题 | 结果 | 备注 |
|---------|--------|------|------|------|
| 14日上午 | 13 | 新年画展 | ✅ | 42图片上传成功 |
| 14日下午 | 14 | 新年画展2 | ✅ | 清空后测试 |
| 14日晚上 | 15 | 测试文章2 | ✅ | 新流程测试 |
| 14日晚上 | 17 | 完整流程测试 | ✅ | 自动创建草稿 |
| 15日凌晨 | 18 | 保留排版测试 | ✅ | HTML保存 |
| 15日凌晨 | 19 | 新流程测试 | ❌ | 失败 |
| 15日凌晨 | 20 | 最终排版测试 | ✅ | OSS URL |
| 15日凌晨 | 21 | 完美排版 | ✅ | 当前测试 |

### 功能测试
- ✅ 邮件抓取
- ✅ 图片上传OSS
- ✅ URL替换
- ✅ AI转换
- ✅ 草稿创建
- ✅ 版本管理
- ⚠️ 公众号排版（待验证）
- ❌ WordPress发布（未测试）

## 遇到的问题

### 问题1: CSS未闭合
**时间**: 14日晚上  
**错误**: `SyntaxError: unmatched ')'`  
**原因**: `.divider`样式块多了一个`)`  
**解决**: 移除多余括号

### 问题2: 函数未导入
**时间**: 14日晚上  
**错误**: `htmlToMarkdown is not defined`  
**原因**: 导入语句缺少该函数  
**解决**: 添加到import列表

### 问题3: 参数名不匹配
**时间**: 14日晚上  
**错误**: `got an unexpected keyword argument 'user_id'`  
**原因**: API传`user_id`，service要`created_by`  
**解决**: 统一参数名

### 问题4: 前端502错误
**时间**: 14日晚上  
**错误**: `502 Bad Gateway`  
**原因**: 前端容器IP变化，nginx缓存旧IP  
**解决**: `sudo docker restart nginx_proxy`

### 问题5: 图片URL未替换
**时间**: 15日凌晨  
**错误**: HTML中图片还是微信URL  
**原因**: original_html在替换前保存  
**解决**: 调整保存顺序

### 问题6: data-src未转换
**时间**: 15日凌晨  
**错误**: 图片不显示  
**原因**: 只有data-src，没有src  
**解决**: 替换后再次转换

### 问题7: 排版不显示
**时间**: 15日凌晨  
**错误**: 只显示简单图文  
**原因**: `:deep()`选择器不生效  
**解决**: 改用全局样式

### 问题8: 502 Bad Gateway（前端容器重建后）
**时间**: 15日下午  
**错误**: 访问 e.com 返回 502  
**原因**: 前端容器重建后 IP 变化，Nginx 仍缓存旧的 `frontend` 解析  
**解决**: `docker restart nginx_proxy`

## 性能数据

### 图片处理
- 单张图片上传时间: ~200ms
- 42张图片总时间: ~8秒
- OSS存储路径: `submissions/{id}/YYYYMMDD_HHMMSS_{hash}.jpg`

### AI转换
- 平均处理时间: 10-15秒
- 内容长度: 5000-8000字符
- 图片占位符: 42个

### 数据库
- 投稿记录: 21条
- 草稿记录: ~10条
- 图片记录: ~400条
- 版本记录: ~20条

## 配置变更

### 环境变量
- 添加: `OSS_ACCESS_KEY_ID`
- 添加: `OSS_ACCESS_KEY_SECRET`
- 添加: `OSS_ENDPOINT`
- 添加: `OSS_BUCKET_NAME`

### 数据库
- 添加字段: `submissions.original_html`
- 修改字段: `submissions.compressed` (允许NULL)

### 依赖包
- 前端: `tinymce@6.8.2` → 已移除，改用 Tiptap（见下方 2026-02-15 操作）
- 后端: `bcrypt==4.1.3` (降级)

---

## 2026-02-15 下午：中间栏编辑器替换与 502 修复

### 问题背景
- 用户反馈：审核页中间栏「AI转换内容」的 TinyMCE 编辑器无法铺满、甚至「编辑器直接没有了」。
- 原因：TinyMCE 在 flex 布局下 `height: 100%` 解析异常；后续用非 scoped CSS 强制 flex 导致 iframe 塌陷到 0 高度。

### 操作1：尝试修复 TinyMCE（未彻底解决）
- 修改文件: `frontend/src/views/AuditView.vue`
- 为中间栏容器添加 class `audit-view-tinymce-wrap`，增加非 scoped 兜底样式（`.tox-tinymce` / `.tox` / `[role="application"]`）。
- 用 JS：`ResizeObserver` 监听容器，动态设置 TinyMCE 根节点 `style.height` 像素值；`init_instance_callback` 内多次延时同步高度。
- 结果：删除对 TinyMCE 内部的 flex/min-height 覆盖后编辑器可显示，但用户反馈「还是不行」，故改为替换编辑器。

### 操作2：中间栏编辑器替换为 Tiptap（免费版）
- **安装依赖**（frontend）:
  - `@tiptap/vue-3`、`@tiptap/starter-kit`、`@tiptap/extension-image`、`@tiptap/extension-text-align`、`@tiptap/extension-underline`、`@tiptap/extension-link`、`@tiptap/pm`
  - 命令: `npm install @tiptap/vue-3 @tiptap/starter-kit ...`（在宿主机执行，Docker 构建时会重新安装）
- **新建文件**: `frontend/src/components/TiptapEditor.vue`
  - 基于 `useEditor` + `EditorContent`，扩展：StarterKit、Image、TextAlign、Underline、Link。
  - 工具栏：加粗/斜体/下划线/删除线、H1–H3、有序/无序列表、左/中/右对齐、引用、代码块、分割线、撤销/重做。
  - 接口：`v-model` 绑定 HTML、`@change` 事件；`defineExpose({ getHTML, setHTML, editor })`。
  - 布局：`display: flex; flex-direction: column; height: 100%`，编辑区 `flex: 1; min-height: 0`，无 iframe，自然铺满。
- **修改文件**: `frontend/src/views/AuditView.vue`
  - 移除所有 TinyMCE 相关：import、`initTinyMCE`、`editorResizeObserver`、`editor` 变量、`onBeforeUnmount` 中的 `tinymce.remove`。
  - 中间栏改为：`<TiptapEditor ref="tiptapRef" v-model="editableHtml" @change="handleContentChange" />`。
  - 所有 `editor.getContent()` → `tiptapRef.value.getHTML()`，`editor.setContent(html)` → `tiptapRef.value.setHTML(html)`。
  - 快照/保存/恢复版本/AI 改写/恢复 AI 版本 均改为通过 `tiptapRef` 读写的 HTML。
- **修改文件**: `frontend/package.json`
  - 移除依赖: `tinymce`。

### 操作3：重启前端服务
- 用户要求「重启」。
- 执行: `docker-compose up -d --build frontend` 时出现 `KeyError: 'ContainerConfig'`（docker-compose 与镜像元数据兼容问题）。
- 改执行: `docker-compose rm -sf frontend backend celery_worker` 后 `docker-compose up -d frontend backend celery_worker`，前端、后端、Celery 重建并启动成功，Vite 在 3000 端口正常。

### 操作4：502 Bad Gateway 处理
- 用户反馈访问出现 502。
- 原因：Nginx 容器（nginx_proxy）已长时间运行，缓存的 `frontend` 主机名为旧容器 IP；前端容器重建后 IP 变化，Nginx 仍连旧 IP 导致 502。
- 处理：`docker restart nginx_proxy`，使 Nginx 重新解析 `upstream frontend { server frontend:3000; }`。
- 结果：502 消失，前端通过 e.com 正常访问。

### 涉及文件汇总（本次）
| 文件 | 操作 |
|------|------|
| `frontend/src/components/TiptapEditor.vue` | 新建 |
| `frontend/src/views/AuditView.vue` | 重写中间栏逻辑，TinyMCE → Tiptap |
| `frontend/package.json` | 移除 tinymce，新增 Tiptap 相关依赖 |

### 依赖变更（本次）
- 前端移除: `tinymce`
- 前端新增: `@tiptap/vue-3`、`@tiptap/starter-kit`、`@tiptap/extension-image`、`@tiptap/extension-text-align`、`@tiptap/extension-underline`、`@tiptap/extension-link`、`@tiptap/pm`

---

**最后更新**: 2026-02-15（Tiptap 替换与 502 修复）  
**记录人**: Kiro AI Assistant
