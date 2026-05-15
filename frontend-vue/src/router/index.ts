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
  ],
})

export default router
