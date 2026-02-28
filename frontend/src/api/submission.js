/**
 * 投稿相关API
 */
import request from './request'

/**
 * 获取投稿列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.size - 每页数量
 * @param {string} params.status - 状态筛选
 * @param {string} params.search - 搜索关键词
 */
export function getSubmissions(params) {
  return request({
    url: '/submissions/',
    method: 'get',
    params
  })
}

/**
 * 获取投稿详情
 * @param {number} id - 投稿ID
 */
export function getSubmission(id) {
  return request({
    url: `/submissions/${id}`,
    method: 'get'
  })
}

/**
 * 删除投稿
 * @param {number} id - 投稿ID
 */
export function deleteSubmission(id) {
  return request({
    url: `/submissions/${id}`,
    method: 'delete'
  })
}

/**
 * 预览/解析内容（不创建投稿）
 * @param {FormData} formData - 包含文章类型、链接或文件
 */
export function previewContent(formData) {
  return request({
    url: '/submissions/preview',
    method: 'post',
    data: formData
  })
}

/**
 * 手动创建投稿
 * @param {Object} data - 投稿数据（已解析的内容和元数据）
 */
export function createSubmission(data) {
  return request({
    url: '/submissions/',
    method: 'post',
    data,
    headers: { 'Content-Type': 'application/json' }
  })
}

/**
 * 认领投稿
 * @param {number} id - 投稿ID
 */
export function claimSubmission(id) {
  return request({
    url: `/submissions/${id}/claim`,
    method: 'post'
  })
}

/**
 * 触发AI转换任务
 * @param {number} id - 投稿ID
 */
export function triggerTransform(id) {
  return request({
    url: `/submissions/${id}/transform`,
    method: 'post'
  })
}

/**
 * 查询该投稿的 AI 改写任务最新状态（用于轮询判断完成或失败）
 * @param {number} submissionId - 投稿ID
 */
export function getTransformStatus(submissionId) {
  return request({
    url: `/submissions/${submissionId}/transform-status`,
    method: 'get'
  })
}
