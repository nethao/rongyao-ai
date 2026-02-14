/**
 * Markdown转HTML（用于编辑器与左侧原文预览）
 */
export function markdownToHtml(markdown) {
  if (!markdown) return ''
  let html = markdown.trim()
  if (!html) return '<p></p>'

  // 转换图片：![图片N](URL) -> <img src="URL" />
  html = html.replace(/!\[图片\d+\]\(([^)]+)\)/g, (match, url) => {
    return `<img src="${url}" style="max-width: 100%; height: auto;" alt="" />`
  })

  // 按双换行分块，每块转为段落或保留图片
  const blocks = html.split(/\n\s*\n/)
  html = blocks
    .map((block) => {
      const trimmed = block.trim()
      if (!trimmed) return ''
      if (trimmed.startsWith('<img')) return trimmed
      return `<p>${trimmed.replace(/\n/g, '<br>')}</p>`
    })
    .filter(Boolean)
    .join('\n')

  return html || '<p></p>'
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
