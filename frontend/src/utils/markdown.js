import { marked } from 'marked'

/**
 * Markdown转HTML（用于编辑器与左侧原文预览）
 */
export function markdownToHtml(markdown) {
  if (!markdown) return ''
  
  try {
    // 使用marked库解析标准Markdown
    const html = marked.parse(markdown, {
      breaks: false,  // 不自动转换单个换行为<br>
      gfm: true,      // 支持GitHub风格Markdown
    })
    return html
  } catch (error) {
    console.error('Markdown解析失败:', error)
    return `<p>${markdown}</p>`
  }
}

const TEMP_PLACEHOLDER_PREFIX = '\u2063\u2063IMG'  // 不可见字符，避免与正文冲突
const TEMP_PLACEHOLDER_SUFFIX = '\u2063\u2063'

/**
 * 在已有 HTML 中把占位符替换为 <img>（只替换 <p>占位符</p>，不碰属性里的占位符）
 * 用于 API 返回的 current_content 本身就是 HTML 的情况
 */
function replacePlaceholdersInHtml(html, mediaMap) {
  if (!html || !mediaMap || Object.keys(mediaMap).length === 0) return html
  let out = html
  for (const [placeholder, url] of Object.entries(mediaMap)) {
    const imgTag = `<img src="${url}" data-id="${placeholder}" style="max-width:100%; height:auto;" alt="图片" />`
    const escaped = placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    out = out.replace(new RegExp(`<p>\\s*${escaped}\\s*</p>`, 'g'), imgTag)
  }
  return out
}

/**
 * Markdown + media_map（占位符→URL）→ 带 <img> 的 HTML
 * 若 content 已是 HTML（含 <p>、<h2> 等），则只在 HTML 内替换占位符；否则按 Markdown 解析后再替换
 */
export function markdownWithPlaceholdersToHtml(content, mediaMap) {
  if (!content) return ''
  if (!mediaMap || Object.keys(mediaMap).length === 0) {
    return content.trim().startsWith('<') ? content : markdownToHtml(content)
  }
  // 已是 HTML：直接替换占位符
  if (content.trim().startsWith('<') || content.includes('<p>')) {
    return replacePlaceholdersInHtml(content, mediaMap)
  }
  // Markdown：先占位再 parse 再还原，避免 marked 破坏占位符、二次替换破坏 data-id
  const entries = Object.entries(mediaMap)
  let md = content
  const tempToImg = {}
  entries.forEach(([placeholder, url], index) => {
    const temp = `${TEMP_PLACEHOLDER_PREFIX}_${index}_${TEMP_PLACEHOLDER_SUFFIX}`
    md = md.split(placeholder).join(temp)
    tempToImg[temp] = `<img src="${url}" data-id="${placeholder}" style="max-width:100%; height:auto;" alt="图片" />`
  })
  let html = markdownToHtml(md)
  entries.forEach((_, index) => {
    const temp = `${TEMP_PLACEHOLDER_PREFIX}_${index}_${TEMP_PLACEHOLDER_SUFFIX}`
    html = html.split(temp).join(tempToImg[temp])
  })
  return html
}

/**
 * HTML转Markdown（保存时使用）
 */
export function htmlToMarkdown(html) {
  if (!html) return ''
  
  let markdown = html
  
  // 转换图片
  let imgIndex = 1
  markdown = markdown.replace(/<img[^>]+src="([^"]+)"[^>]*>/gi, (match, url) => {
    return `\n![图片${imgIndex++}](${url})\n`
  })
  
  // 移除HTML标签
  markdown = markdown.replace(/<p[^>]*>/gi, '\n')
  markdown = markdown.replace(/<\/p>/gi, '\n')
  markdown = markdown.replace(/<br\s*\/?>/gi, '\n')
  markdown = markdown.replace(/<section[^>]*>/gi, '')
  markdown = markdown.replace(/<\/section>/gi, '')
  markdown = markdown.replace(/<div[^>]*>/gi, '')
  markdown = markdown.replace(/<\/div>/gi, '')
  markdown = markdown.replace(/<span[^>]*>/gi, '')
  markdown = markdown.replace(/<\/span>/gi, '')
  markdown = markdown.replace(/<h(\d)>/gi, '\n### ')
  markdown = markdown.replace(/<\/h\d>/gi, '\n')
  
  // 清理多余空行
  markdown = markdown.replace(/\n{3,}/g, '\n\n').trim()
  
  return markdown
}
