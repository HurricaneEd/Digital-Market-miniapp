import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/admin' },
    { path: '/admin/login', name: 'admin-login', component: () => import('@/views/AdminLogin.vue') },
    {
      path: '/admin',
      name: 'admin-dashboard',
      component: () => import('@/views/AdminDashboard.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/products',
      name: 'admin-products',
      component: () => import('@/views/AdminProducts.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/orders',
      name: 'admin-orders',
      component: () => import('@/views/AdminOrders.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/AdminUsers.vue'),
      meta: { requiresAdmin: true },
    },
    {
      path: '/admin/profile',
      name: 'admin-profile',
      component: () => import('@/views/AdminProfile.vue'),
      meta: { requiresAdmin: true },
    },
    { path: '/:pathMatch(.*)*', redirect: '/admin' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem('user_info') || 'null')
  } catch {
    return null
  }
}

router.beforeEach((to) => {
  const token = localStorage.getItem('auth_token')
  const user = readStoredUser()
  const isAdmin = Boolean(user?.is_staff)

  if (to.meta.requiresAdmin && (!token || !isAdmin)) {
    return {
      name: 'admin-login',
      query: {
        ...(token ? { reason: 'forbidden' } : {}),
        redirect: to.fullPath,
      },
    }
  }

  if (to.name === 'admin-login' && token && isAdmin) {
    return { name: 'admin-dashboard' }
  }

  return true
})

export default router
