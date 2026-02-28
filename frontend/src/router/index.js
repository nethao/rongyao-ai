import { createRouter, createWebHistory } from 'vue-router'
import { isAuthenticated, isAdmin } from '../utils/auth'

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
router.beforeEach((to, from, next) => {
  const authenticated = isAuthenticated()
  const admin = isAdmin()

  // 需要认证的路由
  if (to.meta.requiresAuth && !authenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // 需要管理员权限的路由
  if (to.meta.requiresAdmin && !admin) {
    next({ path: '/submissions' })
    return
  }

  // 已登录用户访问登录页，重定向到首页
  if (to.name === 'login' && authenticated) {
    next({ name: 'home' })
    return
  }

  // 编辑人员首次可引导至个人中心完善文编映射（可选：若需要强制首次填写，可在此判断并 next({ name: 'profile', query: { first: '1' } })）
  next()
})

export default router
