import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'research',
      component: () => import('@/pages/ResearchPage.vue'),
    },
    {
      path: '/quick-search',
      name: 'quick-search',
      component: () => import('@/pages/QuickSearchPage.vue'),
    },
    {
      path: '/documents',
      name: 'documents',
      component: () => import('@/pages/DocumentsPage.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/pages/SettingsPage.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/pages/AdminPage.vue'),
      meta: { permission: 'user:manage' },
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.name === 'login') return true
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()
  if (!auth.user && !auth.isLoading) await auth.hydrate()
  if (auth.authRequired && !auth.user) return { name: 'login' }
  const permission = to.meta.permission as string | undefined
  if (permission && !auth.user?.permissions.includes(permission)) return { name: 'research' }
  return true
})

export default router
