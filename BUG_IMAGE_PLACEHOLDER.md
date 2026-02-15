# BUG: 编辑器中图片占位符未替换为真实图片

**状态**: ✅ 已修复（2026-02-16）

## 问题描述
前端编辑器加载草稿后，显示的是 `[[IMG_1]]` 文本，而不是真实的图片。

---

## 修复记录（最终方案）

### 1. 后端统一 Hydration
- **文件**: `backend/app/api/drafts.py`
- GET 草稿时若有 `ai_content_md` + `media_map`，先调用 `ContentProcessor.hydrate()` 将 `[[IMG_N]]` 转为 `<img>`，再把得到的 HTML 作为 `current_content` 返回；前端直接使用，不再做占位符替换。

### 2. media_map 丢失的修复
- **保存时保留旧映射**: PUT 更新草稿时，若 `dehydrate` 得到的 `new_media_map` 里没有某占位符，但内容里仍含该占位符，则从 `draft.media_map` 保留该占位符→URL，避免因编辑器未显示图时保存而清空 media_map。
- **加载时从投稿恢复**: GET 草稿时若 `media_map` 为空但内容含 `[[IMG_N]]` 且该投稿有 `submission.images`，则按图片顺序重建 `media_map`（`[[IMG_1]]`→第 1 张 URL…），再用于 Hydration。需 `selectinload(Draft.submission).selectinload(Submission.images)`。

### 3. 输入已是 HTML 的兼容
- **文件**: `backend/app/utils/content_processor.py` 的 `hydrate()`
- 若 `md_text` 以 `<` 开头或含 `<p>`，视为已是 HTML，只做占位符替换（正则替换 `<p>[[IMG_N]]</p>`），不经过 markdown 解析。

### 4. 排版错乱修复
- **文件**: `backend/app/utils/content_processor.py` 的 `_sanitize_html()`
- 原逻辑会 unwrap `<li>` 内所有 `<p>` 并删除“空”`<li>`，导致列表和段落排版错乱。
- **修改**: 仅移除完全空的段落（`<p></p>`、`<p><br></p>`），不再对列表项做 unwrap，保留原有层级与排版。

### 相关文件汇总
- `backend/app/api/drafts.py`：GET 时 Hydration、media_map 恢复与保留
- `backend/app/utils/content_processor.py`：`hydrate()`、`_sanitize_html()`
- `frontend/src/views/AuditView.vue`：有 media_map 时直接使用 `response.current_content`，不再前端替换

---

## 当前状态（修复前描述，保留供参考）

### 后端数据 ✅ 正确
```bash
# 数据库验证
submission_id: 12
draft_id: 12

# ai_content_md (Markdown格式)
包含: [[IMG_1]]

# media_map (JSON格式)
{
  "[[IMG_1]]": "https://rongyao-ai-test.oss-cn-beijing.aliyuncs.com/submissions/12/20260215_173608_40794529.jpg"
}
```

### API响应 ✅ 正确
```javascript
// GET /api/drafts/12 返回
{
  "current_content": "## 标题\n\n[[IMG_1]]\n\n段落",
  "media_map": {
    "[[IMG_1]]": "https://rongyao-ai-test.oss-cn-beijing.aliyuncs.com/submissions/12/20260215_173608_40794529.jpg"
  }
}
```

### 前端处理逻辑
**文件**: `/frontend/src/views/AuditView.vue`

**loadDraft函数** (行 359-410):
```javascript
// 1. Markdown转HTML
processedContent = markdownToHtml(response.current_content)
// 结果: <p>[[IMG_1]]</p>

// 2. 替换占位符
for (const [placeholder, url] of Object.entries(response.media_map)) {
  const imgTag = `<img src="${url}" data-id="${placeholder}" style="max-width:100%; height:auto;" alt="图片" />`
  const escapedPlaceholder = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  
  // 替换 <p>[[IMG_N]]</p>
  processedContent = processedContent.replace(
    new RegExp(`<p>\\s*${escapedPlaceholder}\\s*</p>`, 'g'),
    imgTag
  )
  // 替换单独的 [[IMG_N]]
  processedContent = processedContent.replace(
    new RegExp(escapedPlaceholder, 'g'),
    imgTag
  )
}
```

**AI改写轮询逻辑** (行 660-685): 相同的替换逻辑

## 问题分析

### 可能原因1: 正则表达式转义问题
`[[IMG_1]]` 包含特殊字符 `[` `]`，需要正确转义。

**当前转义**:
```javascript
placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
// "[[IMG_1]]" -> "\\[\\[IMG_1\\]\\]"
```

**测试**:
```javascript
const placeholder = "[[IMG_1]]"
const escaped = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const regex = new RegExp(`<p>\\s*${escaped}\\s*</p>`, 'g')
const html = "<p>[[IMG_1]]</p>"
console.log(regex.test(html))  // 应该返回 true
```

### 可能原因2: marked解析器处理
`marked.parse()` 可能对 `[[IMG_1]]` 做了特殊处理（如转义、编码）。

**测试**:
```javascript
import { marked } from 'marked'
const md = "## 标题\n\n[[IMG_1]]\n\n段落"
const html = marked.parse(md)
console.log(html)
// 检查 [[IMG_1]] 是否被转义为 &lt;...&gt; 或其他形式
```

### 可能原因3: 替换时机问题
替换可能在Tiptap编辑器加载后被覆盖。

**检查顺序**:
```javascript
editableContent.value = processedContent  // 1. 设置值
editableHtml.value = processedContent     // 2. 设置HTML
// ... 后续是否有其他操作覆盖了内容？
```

### 可能原因4: 浏览器控制台未显示实际HTML
需要在浏览器开发者工具中检查：
1. Network标签：API返回的 `media_map` 是否正确
2. Console：`console.log(processedContent)` 查看替换后的HTML
3. Elements：检查DOM中是否有 `<img>` 标签

## 调试步骤

### 1. 添加前端日志
在 `AuditView.vue` 的 `loadDraft` 函数中添加：

```javascript
// 处理编辑器内容：Markdown + 占位符 → HTML
let processedContent = response.current_content

console.log('=== 调试开始 ===')
console.log('1. 原始Markdown:', response.current_content)
console.log('2. media_map:', response.media_map)

if (response.media_map && Object.keys(response.media_map).length > 0) {
  processedContent = markdownToHtml(response.current_content)
  console.log('3. Markdown转HTML后:', processedContent)
  
  for (const [placeholder, url] of Object.entries(response.media_map)) {
    console.log('4. 处理占位符:', placeholder, '-> URL:', url)
    
    const imgTag = `<img src="${url}" data-id="${placeholder}" style="max-width:100%; height:auto;" alt="图片" />`
    const escapedPlaceholder = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    
    console.log('5. 转义后的占位符:', escapedPlaceholder)
    console.log('6. 正则表达式:', `<p>\\s*${escapedPlaceholder}\\s*</p>`)
    
    const beforeReplace = processedContent
    processedContent = processedContent.replace(
      new RegExp(`<p>\\s*${escapedPlaceholder}\\s*</p>`, 'g'),
      imgTag
    )
    console.log('7. 第一次替换后是否变化:', beforeReplace !== processedContent)
    
    processedContent = processedContent.replace(
      new RegExp(escapedPlaceholder, 'g'),
      imgTag
    )
    console.log('8. 第二次替换后:', processedContent)
  }
}

console.log('9. 最终HTML:', processedContent)
console.log('=== 调试结束 ===')
```

### 2. 浏览器控制台检查
1. 打开浏览器开发者工具 (F12)
2. 刷新编辑器页面
3. 查看Console输出的调试信息
4. 检查步骤7是否返回 `true`（说明替换成功）
5. 检查步骤9的最终HTML是否包含 `<img>` 标签

### 3. 测试正则表达式
在浏览器Console中直接测试：

```javascript
const placeholder = "[[IMG_1]]"
const escaped = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const html = "<p>[[IMG_1]]</p>"
const regex = new RegExp(`<p>\\s*${escaped}\\s*</p>`, 'g')

console.log('转义后:', escaped)
console.log('正则:', regex)
console.log('测试结果:', regex.test(html))
console.log('替换结果:', html.replace(regex, '<img src="test.jpg" />'))
```

### 4. 检查marked输出
```javascript
import { marked } from 'marked'
const md = "[[IMG_1]]"
const html = marked.parse(md)
console.log('marked输出:', html)
console.log('是否包含[[IMG_1]]:', html.includes('[[IMG_1]]'))
```

## 预期结果
- 步骤7应该返回 `true`
- 步骤9的HTML应该包含 `<img src="https://rongyao-ai-test.oss-cn-beijing.aliyuncs.com/..."`
- 编辑器中应该显示图片，而不是 `[[IMG_1]]` 文本

## 相关文件
- `/frontend/src/views/AuditView.vue` (行 359-410, 660-685)
- `/frontend/src/utils/markdown.js` (markdownToHtml函数)
- `/backend/app/api/drafts.py` (行 50-80)

## 已验证的正确部分（修复后）
✅ 数据库存储正确  
✅ API 返回已 Hydration 的 HTML（含 `<img>`）  
✅ media_map 保存时保留、丢失时从 submission.images 恢复  
✅ 编辑器中图片正常显示  
✅ 仅移除空段落，列表/段落排版保留  

## 后续若再出现
- 检查 GET `/api/drafts/{id}` 响应里 `current_content` 是否含 `<img src="...">`、`media_map` 是否有对应键。
- 若排版再次错乱，检查是否又对 HTML 做了过度清洗（如 unwrap `<li>` 内 `<p>`）。
