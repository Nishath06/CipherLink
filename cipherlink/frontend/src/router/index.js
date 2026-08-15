import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  // Public pages
  { path: '/', name: 'Landing', component: () => import('@/views/LandingPage.vue') },
  { path: '/login', name: 'Login', component: () => import('@/views/LoginPage.vue') },
  { path: '/register', name: 'Register', component: () => import('@/views/RegisterPage.vue') },

  // Dashboard (authenticated)
  {
    path: '/dashboard',
    component: () => import('@/layouts/DashboardLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'DashboardOverview', component: () => import('@/views/dashboard/OverviewPage.vue') },
      { path: 'applications', name: 'Applications', component: () => import('@/views/dashboard/ApplicationsPage.vue') },
      { path: 'keys', name: 'Keys', component: () => import('@/views/dashboard/KeysPage.vue') },
      { path: 'encryption', name: 'Encryption', component: () => import('@/views/dashboard/EncryptionPage.vue') },
      { path: 'files', name: 'Files', component: () => import('@/views/dashboard/FilesPage.vue') },
      { path: 'audit', name: 'Audit', component: () => import('@/views/dashboard/AuditPage.vue') },
      { path: 'usage', name: 'Usage', component: () => import('@/views/dashboard/UsagePage.vue') },
      { path: 'api-docs', name: 'ApiDocs', component: () => import('@/views/dashboard/ApiDocsPage.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else {
    next()
  }
})

export default router
