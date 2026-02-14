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
 * 触发AI转换任务
 * @param {number} id - 投稿ID
 */
export function triggerTransform(id) {
  return request({
    url: `/submissions/${id}/transform`,
    method: 'post'
  })
}
