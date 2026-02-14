/**
 * 文本差异计算工具
 * 简单的字符级差异标记
 */

/**
 * 计算两个文本之间的差异
 * @param {string} text1 - 原始文本
 * @param {string} text2 - 修改后的文本
 * @returns {Array} 差异数组
 */
export function computeDiff(text1, text2) {
  // 简单实现：按行分割并比较
  const lines1 = text1.split('\n')
  const lines2 = text2.split('\n')
  
  const diff = []
  const maxLen = Math.max(lines1.length, lines2.length)
  
  for (let i = 0; i < maxLen; i++) {
    const line1 = lines1[i] || ''
    const line2 = lines2[i] || ''
    
    if (line1 === line2) {
      diff.push({ type: 'equal', content: line1 })
    } else {
      if (line1) {
        diff.push({ type: 'delete', content: line1 })
      }
      if (line2) {
        diff.push({ type: 'insert', content: line2 })
      }
    }
  }
  
  return diff
}

/**
 * 高亮显示文本差异
 * @param {string} text - 文本内容
 * @param {Array} highlights - 需要高亮的位置数组
 * @returns {string} 带HTML标记的文本
 */
export function highlightDiff(text, highlights = []) {
  if (!highlights || highlights.length === 0) {
    return escapeHtml(text)
  }
  
  let result = ''
  let lastIndex = 0
  
  highlights.forEach(({ start, end, type }) => {
    // 添加未高亮部分
    result += escapeHtml(text.substring(lastIndex, start))
    
    // 添加高亮部分
    const className = type === 'insert' ? 'diff-insert' : 'diff-delete'
    result += `<span class="${className}">${escapeHtml(text.substring(start, end))}</span>`
    
    lastIndex = end
  })
  
  // 添加剩余部分
  result += escapeHtml(text.substring(lastIndex))
  
  return result
}

/**
 * 转义HTML特殊字符
 * @param {string} text - 原始文本
 * @returns {string} 转义后的文本
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, m => map[m])
}

/**
 * 简单的字符串相似度计算（用于高亮相似部分）
 * @param {string} str1 - 字符串1
 * @param {string} str2 - 字符串2
 * @returns {number} 相似度 (0-1)
 */
export function similarity(str1, str2) {
  const longer = str1.length > str2.length ? str1 : str2
  const shorter = str1.length > str2.length ? str2 : str1
  
  if (longer.length === 0) {
    return 1.0
  }
  
  const editDistance = levenshteinDistance(longer, shorter)
  return (longer.length - editDistance) / longer.length
}

/**
 * 计算编辑距离（Levenshtein距离）
 * @param {string} str1 - 字符串1
 * @param {string} str2 - 字符串2
 * @returns {number} 编辑距离
 */
function levenshteinDistance(str1, str2) {
  const matrix = []
  
  for (let i = 0; i <= str2.length; i++) {
    matrix[i] = [i]
  }
  
  for (let j = 0; j <= str1.length; j++) {
    matrix[0][j] = j
  }
  
  for (let i = 1; i <= str2.length; i++) {
    for (let j = 1; j <= str1.length; j++) {
      if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
        matrix[i][j] = matrix[i - 1][j - 1]
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // 替换
          matrix[i][j - 1] + 1,     // 插入
          matrix[i - 1][j] + 1      // 删除
        )
      }
    }
  }
  
  return matrix[str2.length][str1.length]
}
