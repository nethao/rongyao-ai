<template>
  <el-container class="layout-container">
    <el-header class="layout-header">
      <div class="header-left">
        <h1>荣耀AI审核发布系统</h1>
      </div>
      <div class="header-right">
        <el-menu
          mode="horizontal"
          :default-active="activeMenu"
          class="header-menu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="/submissions">
            <el-icon><Document /></el-icon>
            投稿列表
          </el-menu-item>
          <el-menu-item index="/analytics">
            <el-icon><DataAnalysis /></el-icon>
            数据分析
          </el-menu-item>
          <el-menu-item v-if="isAdmin" index="/users">
            <el-icon><UserFilled /></el-icon>
            用户管理
          </el-menu-item>
          <el-menu-item v-if="isAdmin" index="/config">
            <el-icon><Setting /></el-icon>
            系统配置
          </el-menu-item>
        </el-menu>
        <el-dropdown @command="handleCommand">
          <span class="user-dropdown">
            <el-icon><User /></el-icon>
            {{ username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-main class="layout-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  Setting,
  User,
  UserFilled,
  ArrowDown,
  SwitchButton,
  DataAnalysis
} from '@element-plus/icons-vue'
import { getUser, isAdmin as checkIsAdmin, logout } from '../utils/auth'

const router = useRouter()
const route = useRoute()

const username = ref(getUser()?.username || '用户')
const isAdmin = ref(checkIsAdmin())

// 当前激活的菜单
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/submissions') || path.startsWith('/audit')) {
    return '/submissions'
  }
  if (path.startsWith('/users')) {
    return '/users'
  }
  if (path.startsWith('/config')) {
    return '/config'
  }
  return path
})

// 监听路由变化
watch(() => route.path, () => {
  // 更新用户信息
  const user = getUser()
  if (user) {
    username.value = user.username
    isAdmin.value = checkIsAdmin()
  }
})

// 菜单选择
const handleMenuSelect = (index) => {
  router.push(index)
}

// 下拉菜单命令
const handleCommand = async (command) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm(
        '确定要退出登录吗？',
        '提示',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        }
      )
      
      logout()
      ElMessage.success('已退出登录')
      router.push('/login')
    } catch {
      // 用户取消
    }
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-menu {
  border-bottom: none;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 0 10px;
  height: 40px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-dropdown:hover {
  background-color: #f5f7fa;
}

.layout-main {
  padding: 0;
  background-color: #f5f7fa;
  overflow-y: auto;
}
</style>
