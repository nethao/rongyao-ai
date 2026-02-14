# 公众号排版引擎技术文档

## 核心原理

### 1. 盒模型修复
微信公众号使用 `box-sizing: border-box`，与普通网页的 `content-box` 不同。
必须强制所有元素使用 `border-box` 以防止容器被撑爆。

```css
.rich_media_content * {
  box-sizing: border-box !important;
}
```

### 2. 容器居中
公众号标准宽度：677px
必须使用 `margin: 0 auto` 居中显示

```css
.rich_media_content {
  max-width: 677px;
  margin: 0 auto;
}
```

### 3. 内联样式保护
公众号排版（如135编辑器）大量使用内联 `style` 属性。
**绝对不能删除任何 style 属性！**

### 4. SVG 支持
装饰性元素通常是 SVG，必须在 TinyMCE 中允许：
- `svg`, `path`, `g`, `defs`, `use`, `circle`, `rect`, `line`, `polyline`, `polygon`

### 5. Section 嵌套
公众号使用大量嵌套的 `<section>` 标签。
必须配置 `valid_children: '+section[*]'` 允许任意嵌套。

## 实现清单

### ✅ 前端 (AuditView.vue)

**左侧原文预览：使用 iframe 隔离渲染**
- 将 `original_html` 写入 iframe 的独立文档，避免父页 CSS（Element Plus、scoped 等）覆盖公众号内联样式。
- iframe 内只注入公众号基础样式（box-sizing、677px 容器、字体），不覆盖正文内联样式，从而还原与公众号一致的排版（背景色、section、SVG 等）。

**TinyMCE 编辑器：**
```javascript
extended_valid_elements: 'section[*],svg[*],path[*],...',
custom_elements: 'section,svg',
inline_styles: true,
verify_html: false,
valid_children: '+section[*]'
```

### ✅ 后端 (web_fetcher.py)

**保留完整HTML：**
```python
# 移除隐藏样式
style = style.replace('visibility: hidden;', '')

# 转换 data-src 为 src
for img in content_tag.find_all('img'):
    if img.get('data-src'):
        img['src'] = img.get('data-src')

# 保存原始HTML（保留所有style属性）
original_html = str(content_tag)
```

**替换图片URL：**
```python
# 替换为OSS URL后，再次转换 data-src
if content_type == ContentType.WEIXIN:
    soup = BeautifulSoup(original_html, 'html.parser')
    for img in soup.find_all('img'):
        if img.get('data-src'):
            img['src'] = img.get('data-src')
    original_html = str(soup)
```

## 常见问题

### Q: 为什么图片显示不出来？
A: 检查是否将 `data-src` 转换为 `src`，公众号图片使用懒加载。

### Q: 为什么背景色消失了？
A: 检查是否保留了内联 `style` 属性，不要在清洗时删除。

### Q: 为什么容器靠左？
A: 检查是否设置了 `max-width: 677px` 和 `margin: 0 auto`。

### Q: 为什么装饰元素不见了？
A: 检查是否允许 SVG 标签，配置 `extended_valid_elements`。

## 邮件获取的四种文章来源（约定）

通过邮件获取的内容有 **四种来源类型**（见 `email_parser.ContentType`）：

| 序号 | 类型 | 说明 | 排版/HTML 状态 |
|------|------|------|----------------|
| 1 | **公众号 (WEIXIN)** | 邮件正文为公众号链接 | ✅ 已实现：保留 `original_html`、iframe 还原排版、图片按顺序替换为 OSS |
| 2 | 美篇 (MEIPIAN) | 邮件正文为美篇链接 | 待扩展：可仿公众号做原始 HTML 保存 + OSS 图片按序替换 |
| 3 | Word (WORD) | 邮件附件为 .doc/.docx | 待扩展：按需保留版式或仅正文 |
| 4 | 视频 (VIDEO) | 邮件带视频附件 | 待扩展：上传与展示策略 |

**本次修改要点（公众号，后续其他来源可复用）：**

- **抓取**：保留完整正文 HTML（不删内联样式），`data-src` 转为 `src`；请求头尽量接近浏览器（Accept、Referer 等）。
- **图片替换**：上传后**按 HTML 中 `<img>` 出现顺序**用 BeautifulSoup 逐张赋 `src`/`data-src` 为 OSS URL，避免因 HTML 转义（如 `&`→`&amp;`）导致字符串替换失败。
- **接口**：草稿详情需返回 `original_html`（`DraftDetailSchema` 含该字段），前端用 iframe 渲染。
- **前端**：iframe 内只注入基础样式（盒模型、居中、图片约束），不覆盖正文内联样式。

**AI 改写与 WordPress 排版：**

- 公众号/美篇等来源经「AI改写」后，输出需适配 WordPress：在 `prompt_builder.build_transform_prompt()` 中已增加**排版要求**，要求抛弃堆叠样式、背景图、装饰性结构，仅保留简洁段落/标题/列表/图片，不输出版式说明。详见 `backend/app/services/prompt_builder.py`。

## 针对不同来源的扩展

```javascript
// 根据来源类型应用不同样式
if (submission.source === 'weixin') {
  // 公众号：677px，box-sizing: border-box
  applyWeixinStyles()
} else if (submission.source === 'word') {
  // Word：A4宽度，标准盒模型
  applyWordStyles()
} else if (submission.source === 'meipian') {
  // 美篇：自适应宽度
  applyMeipianStyles()
}
```

## 测试验证

使用投稿ID 21测试：
```bash
./scripts/mock.sh "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ" "排版测试"
```

检查点：
- ✅ 容器居中
- ✅ 图片正常显示
- ✅ 背景色保留
- ✅ SVG装饰元素显示
- ✅ 字体和间距正确
