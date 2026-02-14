/**
 * 认证工具函数
 */

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

/**
 * 保存令牌
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 获取令牌
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 移除令牌
 */
export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

/**
 * 保存用户信息
 */
export function setUserInfo(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/**
 * 获取用户信息
 */
export function getUserInfo() {
  const userStr = localStorage.getItem(USER_KEY)
  return userStr ? JSON.parse(userStr) : null
}

/**
 * 获取用户信息（别名）
 */
export function getUser() {
  return getUserInfo()
}

/**
 * 移除用户信息
 */
export function removeUserInfo() {
  localStorage.removeItem(USER_KEY)
}

/**
 * 检查是否已登录
 */
export function isAuthenticated() {
  return !!getToken()
}

/**
 * 检查是否是管理员
 */
export function isAdmin() {
  const user = getUserInfo()
  return user && user.role === 'admin'
}

/**
 * 检查是否是编辑人员
 */
export function isEditor() {
  const user = getUserInfo()
  return user && (user.role === 'editor' || user.role === 'admin')
}

/**
 * 登出
 */
export function logout() {
  removeToken()
  removeUserInfo()
}
