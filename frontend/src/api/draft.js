/**
 * 草稿相关API
 */
import request from './request'

/**
 * 获取草稿详情（包含原文）
 * @param {number} id - 草稿ID
 */
export function getDraft(id) {
  return request({
    url: `/drafts/${id}`,
    method: 'get'
  })
}

/**
 * 更新草稿内容
 * @param {number} id - 草稿ID
 * @param {string} content - 新内容
 */
export function updateDraft(id, content) {
  return request({
    url: `/drafts/${id}`,
    method: 'put',
    data: { content }
  })
}

/**
 * 获取草稿版本历史
 * @param {number} id - 草稿ID
 */
export function getDraftVersions(id) {
  return request({
    url: `/drafts/${id}/versions`,
    method: 'get'
  })
}

/**
 * 恢复到指定版本
 * @param {number} id - 草稿ID
 * @param {number} versionId - 版本ID
 */
export function restoreVersion(id, versionId) {
  return request({
    url: `/drafts/${id}/restore`,
    method: 'post',
    data: { version_id: versionId }
  })
}

/**
 * 恢复到AI原始版本
 * @param {number} id - 草稿ID
 */
export function restoreAIVersion(id) {
  return request({
    url: `/drafts/${id}/restore-ai`,
    method: 'post'
  })
}

/**
 * 上传Word文档并转换为可编辑内容
 * @param {number} id - 草稿ID
 * @param {File} file - Word文件
 */
export function uploadWordToDraft(id, file) {
  const formData = new FormData()
  formData.append('word_file', file)
  return request({
    url: `/drafts/${id}/upload-word`,
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
