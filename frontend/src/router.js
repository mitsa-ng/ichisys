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
    path: '/warehouse/:userId',
    component: () => import('./views/Warehouse.vue'),
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

export default createRouter({
  history: createWebHistory(),
  routes,
})
