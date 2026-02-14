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
          path: 'config',
          name: 'config',
          component: () => import('../views/ConfigView.vue'),
          meta: { requiresAuth: true, requiresAdmin: true }
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
    next({ name: 'home' })
    return
  }

  // 已登录用户访问登录页，重定向到首页
  if (to.name === 'login' && authenticated) {
    next({ name: 'home' })
    return
  }

  next()
})

export default router
