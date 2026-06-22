import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../store/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/auth/Login.vue')
  },
  {
    path: '/',
    redirect: '/tasks'
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('../views/tasks/TaskList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ports',
    name: 'Ports',
    component: () => import('../views/ports/PortStatus.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/settings/EnvSettings.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

let configFetched = false
router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (!configFetched) {
    await authStore.fetchConfig()
    configFetched = true
  }
  if (to.meta.requiresAuth && !authStore.isAuthenticated()) {
    return '/login'
  } else if (to.path === '/login' && authStore.isAuthenticated()) {
    return '/'
  }
})

export default router
