/**
 * 重复稿件 API
 */
import request from './request'

/**
 * 获取重复稿件列表
 * @param {Object} params - 查询参数
 */
export function getDuplicateLogs(params) {
  return request({
    url: '/duplicate-logs/',
    method: 'get',
    params
  })
}
