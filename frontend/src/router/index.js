import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated, isAdmin, getUserInfo } from '../utils/auth'
import { getProfileCompleteStatus } from '../api/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/profile-complete',
      name: 'profile-complete',
      component: () => import('../views/ProfileCompleteView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      component: () => import('../components/Layout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/submissions'
        },
        {
          path: 'submissions',
          name: 'submissions',
          component: () => import('../views/SubmissionsView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'audit/:draftId',
          name: 'audit',
          component: () => import('../views/AuditView.vue'),
          meta: { requiresAuth: true }
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('../views/UsersView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'config',
          name: 'config',
          component: () => import('../views/ConfigView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: () => import('../views/AnalyticsView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'editor-workload',
          name: 'editor-workload',
          component: () => import('../views/EditorWorkloadView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'editor-workload/detail',
          name: 'editor-workload-detail',
          component: () => import('../views/EditorWorkloadDetailView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'copy-editor-workload',
          name: 'copy-editor-workload',
          component: () => import('../views/CopyEditorWorkloadView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'copy-editor-workload/detail',
          name: 'copy-editor-workload-detail',
          component: () => import('../views/CopyEditorWorkloadDetailView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'duplicate-logs',
          name: 'duplicate-logs',
          component: () => import('../views/DuplicateLogsView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
        },
        {
          path: 'profile',
          name: 'profile',
          component: () => import('../views/ProfileView.vue'),
          meta: { requiresAuth: true }
        }
      ]
    }
  ]
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authenticated = isAuthenticated()
  const admin = isAdmin()

  // 需要认证的路由
  if (to.meta.requiresAuth && !authenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // 已登录用户访问登录页，重定向到首页
  if (to.name === 'login' && authenticated) {
    next({ name: 'submissions' })
    return
  }

  // 编辑人员首次登录强制完善：未完成则只能访问 profile-complete
  if (authenticated && to.name !== 'profile-complete' && to.meta.requiresAuth) {
    const user = getUserInfo()
    if (user?.role !== 'editor') {
      // 非编辑无需首次完善检查
      // 继续后续权限判断
    } else {
      try {
        const res = await getProfileCompleteStatus()
        if (res && res.complete === false) {
          next({ name: 'profile-complete' })
          return
        }
      } catch (_) {
        // 编辑用户检查失败时不放行，避免首次登录绕过
        next({ name: 'profile-complete' })
        return
      }
    }
  }

  // 需要管理员权限的路由
  if (to.meta.requiresAdmin && !admin) {
    next({ path: '/submissions' })
    return
  }

  next()
})

export default router
