<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <div class="login-header">
          <h2>荣耀AI审核发布系统</h2>
          <p>Glory AI Audit System</p>
        </div>
      </template>
      
      <el-form
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="captcha_code">
          <div class="captcha-row">
            <el-input
              v-model="loginForm.captcha_code"
              placeholder="请输入验证码"
              size="large"
              class="captcha-input"
              @keyup.enter="handleLogin"
            />
            <img
              class="captcha-image"
              :src="captchaImage"
              alt="验证码"
              @click="refreshCaptcha"
            />
          </div>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            style="width: 100%"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="login-tips">
        <el-alert
          title="默认账号: admin / admin123"
          type="info"
          :closable="false"
          show-icon
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login as loginApi, getCaptcha } from '../api/auth'
import { setToken, setUserInfo } from '../utils/auth'

const router = useRouter()
const route = useRoute()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: '',
  captcha_id: '',
  captcha_code: ''
})

const captchaImage = ref('')

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  captcha_code: [
    { required: true, message: '请输入验证码', trigger: 'blur' }
  ]
}

const refreshCaptcha = async () => {
  try {
    const res = await getCaptcha()
    captchaImage.value = res.captcha_image
    loginForm.captcha_id = res.captcha_id
  } catch (error) {
    console.error('获取验证码失败:', error)
  }
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  if (loading.value) return

  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    if (loading.value) return

    loading.value = true

    try {
      const response = await loginApi({
        username: loginForm.username,
        password: loginForm.password,
        captcha_id: loginForm.captcha_id,
        captcha_code: loginForm.captcha_code
      })

      // 保存令牌和用户信息
      setToken(response.access_token)
      setUserInfo(response.user)

      ElMessage.success('登录成功')

      // 跳转到目标页面或首页
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } catch (error) {
      console.error('登录失败:', error)
      const msg = error.response?.data?.detail || error.message || '登录失败'
      ElMessage.error(msg)
      await refreshCaptcha()
    } finally {
      loading.value = false
    }
  })
}

refreshCaptcha()
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 450px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.login-header {
  text-align: center;
}

.login-header h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 24px;
}

.login-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.login-tips {
  margin-top: 16px;
}

.captcha-row {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.captcha-input {
  flex: 1;
}

.captcha-image {
  width: 140px;
  height: 48px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  background: #fff;
}

:deep(.el-card__header) {
  padding: 24px 20px;
}

:deep(.el-card__body) {
  padding: 20px 30px 30px;
}
</style>
