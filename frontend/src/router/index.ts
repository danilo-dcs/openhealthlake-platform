import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/userStore'
import { unauthorizedRequestHandler } from '@/shared/api/unauthorizedRequestHandler'

const lakehouseApiUrl = import.meta.env.DEV
  ? '/api/lakehouse'
  : import.meta.env.VITE_APP_MAIN_LAKEHOUSE_API_URL

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
    },
    {
      path: '/catalog',
      name: 'catalog',
      component: () => import('../views/CatalogView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
    {
      path: '/passports',
      name: 'passports',
      component: () => import('../views/PassportsView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // The access token is deliberately memory-only. Recreate it from the
  // HttpOnly refresh cookie after a full page reload.
  if (!userStore.accessToken) {
    try {
      await unauthorizedRequestHandler(lakehouseApiUrl)
    } catch {
      userStore.clearUser()
    }
  }

  const isAuthenticated = !!userStore.accessToken

  if (to.path === '/login' && isAuthenticated) return '/'
  if (to.path !== '/login' && !isAuthenticated) return '/login'
})

export default router
