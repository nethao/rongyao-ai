# 待修复BUG清单

## 🔴 高优先级

### BUG-001: 公众号排版显示问题
**状态**: 已修复  
**发现时间**: 2026-02-15 01:04  
**修复时间**: 2026-02-15  
**描述**: 投稿21显示为简单图文（图片+文字），未显示复杂排版效果（背景色、装饰元素等）

**复现步骤**:
1. 访问 http://e.com
2. 登录系统
3. 点击投稿21"查看草稿"
4. 查看左侧原文预览

**预期结果**: 显示完整公众号排版，包括背景色块、装饰元素、section嵌套效果

**实际结果**: 只显示图片和文字，排版效果丢失

**根因**: 数据库中原 HTML 完整（含「新生活」「新年画」、section、background）。iframe 注入的样式覆盖了正文内联样式（如对 section 强制 `display: block`、对容器强设 padding/字体），导致复杂排版被压成简单版。

**已修复**:
- ✅ 简化 iframe 内注入样式：仅保留盒模型、677px 居中、图片/SVG 约束，不再对 `.rich_media_content` 设置 padding/font/section 的 display，避免覆盖公众号内联样式
- ✅ 增加 viewport meta，便于缩放一致
- ✅ 抓取时增加 Accept / Accept-Language / Referer 请求头，更接近浏览器

**相关文件**:
- `frontend/src/views/AuditView.vue` (CSS样式)
- `backend/app/services/web_fetcher.py` (HTML抓取)
- `docs/weixin-layout-engine.md` (技术文档)

**调试方法**:
```bash
# 检查HTML内容
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        result = await db.execute(text('SELECT original_html FROM submissions WHERE id = 21'))
        row = result.fetchone()
        if row and row[0]:
            html = row[0]
            print('包含背景色:', 'background-color' in html or 'background:' in html)
            print('section数量:', html.count('<section'))
            print('内联样式:', 'style=' in html)
        break

asyncio.run(check())
"
```

---

### BUG-002: TinyMCE中文语言包
**状态**: 待验证  
**发现时间**: 2026-02-14  
**描述**: TinyMCE编辑器可能缺少中文语言文件

**复现步骤**:
1. 打开编辑器
2. 查看工具栏提示

**预期结果**: 所有提示为中文

**实际结果**: 可能显示英文

**已配置**: `language: 'zh_CN'`

**可能解决方案**:
```bash
# 下载中文语言包
cd /home/nethao/rongyao-ai/frontend
wget https://cdn.tiny.cloud/1/no-api-key/tinymce/6/langs/zh_CN.js
mv zh_CN.js public/tinymce/langs/
```

**相关文件**:
- `frontend/src/views/AuditView.vue`

---

## 🟡 中优先级

### BUG-003: 前端容器IP变化导致502
**状态**: 已知解决方案  
**发现时间**: 2026-02-14  
**描述**: 重启服务后前端容器IP变化，nginx缓存旧IP导致502错误

**复现步骤**:
1. 重启frontend容器
2. 访问网站

**预期结果**: 正常访问

**实际结果**: 502 Bad Gateway

**解决方案**:
```bash
sudo docker restart nginx_proxy
```

**根本解决**: 修改nginx配置使用服务名而非IP
```nginx
# 当前配置（使用IP）
upstream frontend {
    server 172.18.0.11:3000;
}

# 建议配置（使用服务名）
upstream frontend {
    server frontend:3000;
}
```

**相关文件**:
- `nginx/conf.d/default.conf`

---

### BUG-004: 图片加载速度慢
**状态**: 待优化  
**发现时间**: 2026-02-14  
**描述**: 42张图片加载较慢，影响用户体验

**可能原因**:
- OSS带宽限制
- 图片未压缩
- 未使用CDN

**优化方案**:
1. 启用OSS CDN加速
2. 图片上传时自动压缩
3. 使用懒加载
4. 添加加载动画

**相关文件**:
- `backend/app/services/oss_service.py`
- `frontend/src/views/AuditView.vue`

---

## 🟢 低优先级

### BUG-005: WordPress发布功能未测试
**状态**: 未测试  
**发现时间**: 2026-02-14  
**描述**: WordPress发布API已实现但未测试

**测试步骤**:
1. 配置WordPress站点
2. 创建测试草稿
3. 点击"发布"按钮
4. 检查WordPress后台

**相关文件**:
- `backend/app/services/publish_service.py`
- `backend/app/api/drafts.py`

---

### BUG-006: 错误提示不够友好
**状态**: 待优化  
**发现时间**: 2026-02-14  
**描述**: 部分错误提示为英文或技术术语

**优化方案**:
- 统一错误提示格式
- 翻译为中文
- 添加操作建议

**示例**:
```javascript
// 当前
ElMessage.error('Request failed with status code 500')

// 建议
ElMessage.error('服务器错误，请稍后重试或联系管理员')
```

---

### BUG-007: 缺少加载动画
**状态**: 待实现  
**发现时间**: 2026-02-14  
**描述**: AI转换、图片上传等操作缺少加载提示

**实现方案**:
- 添加全局loading组件
- 显示进度百分比
- 添加操作提示文字

---

## 📝 功能增强建议

### FEATURE-001: 支持美篇排版
**优先级**: 中  
**描述**: 当前只优化了公众号排版，美篇排版未处理

**实现方案**:
```javascript
if (submission.source === 'weixin') {
  applyWeixinStyles()
} else if (submission.source === 'meipian') {
  applyMeipianStyles()
}
```

---

### FEATURE-002: 图片编辑功能
**优先级**: 低  
**描述**: 支持裁剪、旋转、滤镜等

**技术方案**: 集成Cropper.js

---

### FEATURE-003: 批量操作
**优先级**: 低  
**描述**: 支持批量删除、批量发布

---

## 🔧 调试工具

### 查看投稿HTML
```bash
sudo docker-compose exec backend python -c "
import asyncio
from app.database import get_db
from sqlalchemy import text

async def check():
    async for db in get_db():
        result = await db.execute(text('SELECT original_html FROM submissions WHERE id = 21'))
        row = result.fetchone()
        if row and row[0]:
            print(row[0][:2000])
        break

asyncio.run(check())
"
```

### 查看CSS应用情况
在浏览器开发者工具中：
1. 检查`.html-preview .rich_media_content`样式
2. 查看是否有样式冲突
3. 检查`box-sizing`是否生效

### 重新抓取测试
```bash
./scripts/mock.sh "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ" "新测试"
```

---

## 📞 联系方式

**项目路径**: `/home/nethao/rongyao-ai`  
**文档位置**: 
- 项目总结: `PROJECT_SUMMARY.md`
- 操作日志: `OPERATION_LOG.md`
- BUG清单: `BUGS.md` (本文件)
- 技术文档: `docs/weixin-layout-engine.md`

**测试账号**: admin / admin123  
**测试链接**: https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ

---

**最后更新**: 2026-02-15 01:07  
**维护人**: 待交接
