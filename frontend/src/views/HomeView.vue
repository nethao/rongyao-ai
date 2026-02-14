<template>
  <div class="home">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>荣耀AI审核发布系统</h1>
          <div class="user-info">
            <el-dropdown @command="handleCommand">
              <span class="user-dropdown">
                <el-icon><User /></el-icon>
                {{ userInfo?.username }}
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item disabled>
                    角色: {{ roleText }}
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon>
                    登出
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-header>
      
      <el-main>
        <el-card>
          <template #header>
            <span>欢迎使用</span>
          </template>
          <el-space direction="vertical" :size="20" style="width: 100%">
            <el-alert
              title="系统正在开发中..."
              type="info"
              :closable="false"
            />
            
            <div v-if="userInfo?.role === 'admin'">
              <h3>管理员功能</h3>
              <el-button type="primary" @click="$router.push('/config')">
                系统配置
              </el-button>
            </div>
            
            <div>
              <h3>用户信息</h3>
              <p>用户名: {{ userInfo?.username }}</p>
              <p>角色: {{ roleText }}</p>
            </div>
          </el-space>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { getUserInfo, logout as logoutUtil } from '../utils/auth'
import { logout as logoutApi } from '../api/auth'

const router = useRouter()
const userInfo = ref(null)

const roleText = computed(() => {
  if (!userInfo.value) return ''
  return userInfo.value.role === 'admin' ? '管理员' : '编辑人员'
})

onMounted(() => {
  userInfo.value = getUserInfo()
})

const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要登出吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      
      // 调用登出API
      await logoutApi()
      
      // 清除本地数据
      logoutUtil()
      
      ElMessage.success('已登出')
      router.push('/login')
    } catch (error) {
      if (error !== 'cancel') {
        console.error('登出失败:', error)
      }
    }
  }
}
</script>

<style scoped>
.home {
  height: 100vh;
}

.el-header {
  background-color: #409eff;
  color: white;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h1 {
  margin: 0;
  font-size: 20px;
}

.user-info {
  display: flex;
  align-items: center;
}

.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-dropdown:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.el-main {
  padding: 20px;
  background-color: #f5f5f5;
}
</style>
