/**
 * HTTP请求封装
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, logout } from '../utils/auth'
import router from '../router'

// 创建axios实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 验证码接口不携带 token，避免未登录/过期 token 导致 401 影响验证码显示
    const isCaptcha = (config.url || '').includes('/auth/captcha')
    if (!isCaptcha) {
      const token = getToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('响应错误:', error)
    
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // 未认证，跳转到登录页
          ElMessage.error('登录已过期，请重新登录')
          logout()
          router.push('/login')
          break
        case 403:
          ElMessage.error(data.detail || '没有权限执行此操作')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误，请稍后重试')
          break
        default:
          ElMessage.error(data.detail || '请求失败')
      }
    } else {
      const msg = error.code === 'ECONNABORTED'
        ? '请求超时，请检查网络或稍后重试'
        : (error.message || '网络错误，请检查网络连接')
      ElMessage.error(msg)
    }
    
    return Promise.reject(error)
  }
)

export default request
