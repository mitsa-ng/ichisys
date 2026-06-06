import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('./views/Home.vue'),
  },
  {
    path: '/pool/:id',
    component: () => import('./views/PoolDetail.vue'),
  },
  {
    path: '/pool/:id/prizes',
    component: () => import('./views/PoolPrizes.vue'),
  },
  {
    path: '/warehouse/:userId',
    component: () => import('./views/Warehouse.vue'),
  },
  {
    path: '/admin/setup',
    component: () => import('./views/admin/SetupAdmin.vue'),
  },
  {
    path: '/admin/login',
    component: () => import('./views/admin/Login.vue'),
  },
  {
    path: '/admin',
    component: () => import('./views/admin/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin/pools/new',
    component: () => import('./views/admin/PoolForm.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin/pools/:id',
    component: () => import('./views/admin/PoolDetail.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth && !localStorage.getItem('admin_token')) {
    next('/admin/login')
  } else {
    next()
  }
})

export default router
