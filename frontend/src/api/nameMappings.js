/**
 * 采编/文编名称映射 API
 */
import request from './request'

export function listEditorMappings() {
  return request({ url: '/name-mappings/editors', method: 'get' })
}

/** 采编映射表单：邮箱/前缀 下拉选项（投稿历史 + 已配置邮箱） */
export function getEditorEmailOptions() {
  return request({ url: '/name-mappings/editor-email-options', method: 'get' })
}

export function createEditorMapping(data) {
  return request({ url: '/name-mappings/editors', method: 'post', data })
}

export function updateEditorMapping(id, data) {
  return request({ url: `/name-mappings/editors/${id}`, method: 'put', data })
}

export function deleteEditorMapping(id) {
  return request({ url: `/name-mappings/editors/${id}`, method: 'delete' })
}

export function listCopyEditorMappings(userId = null) {
  const params = userId != null ? { user_id: userId } : {}
  return request({ url: '/name-mappings/copy-editors', method: 'get', params })
}

export function createCopyEditorMapping(data) {
  return request({ url: '/name-mappings/copy-editors', method: 'post', data })
}

export function updateCopyEditorMapping(id, data) {
  return request({ url: `/name-mappings/copy-editors/${id}`, method: 'put', data })
}

export function deleteCopyEditorMapping(id) {
  return request({ url: `/name-mappings/copy-editors/${id}`, method: 'delete' })
}

export function getMyProfile() {
  return request({ url: '/name-mappings/my/profile', method: 'get' })
}

export function changeMyPassword(data) {
  return request({ url: '/name-mappings/my/change-password', method: 'post', data })
}
