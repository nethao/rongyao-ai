/**
 * 系统监控API（管理员）
 */
import request from './request'

/**
 * 手动触发邮件抓取
 */
export function triggerFetchEmails() {
  return request({
    url: '/monitoring/fetch-emails',
    method: 'post'
  })
}

/**
 * 获取邮件抓取任务状态
 */
export function getFetchEmailsStatus() {
  return request({
    url: '/monitoring/fetch-emails/status',
    method: 'get'
  })
}
