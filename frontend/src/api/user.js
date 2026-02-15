/**
 * 用户管理API（管理员）
 */
import request from './request'

/**
 * 获取用户列表
 */
export function getUsers(params) {
  return request({
    url: '/users/',
    method: 'get',
    params
  })
}

/**
 * 获取用户详情
 */
export function getUser(id) {
  return request({
    url: `/users/${id}`,
    method: 'get'
  })
}

/**
 * 新增用户
 */
export function createUser(data) {
  return request({
    url: '/users/',
    method: 'post',
    data
  })
}

/**
 * 更新用户（角色）
 */
export function updateUser(id, data) {
  return request({
    url: `/users/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除用户
 */
export function deleteUser(id) {
  return request({
    url: `/users/${id}`,
    method: 'delete'
  })
}

/**
 * 管理员重置用户密码
 */
export function resetUserPassword(id, data) {
  return request({
    url: `/users/${id}/reset-password`,
    method: 'post',
    data
  })
}
