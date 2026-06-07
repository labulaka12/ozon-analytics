import { createRouter, createWebHistory } from 'vue-router'
import AuthLayout from '@/layouts/AuthLayout.vue'
import AppLayout from '@/layouts/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: AuthLayout,
      children: [
        { path: '', name: 'Login', component: () => import('@/views/login/LoginView.vue') },
      ],
    },
    {
      path: '/register',
      component: AuthLayout,
      children: [
        { path: '', name: 'Register', component: () => import('@/views/login/RegisterView.vue') },
      ],
    },
    {
      path: '/',
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/dashboard/DashboardView.vue') },
        { path: 'orders', name: 'Orders', component: () => import('@/views/orders/OrdersView.vue') },
        { path: 'profit', name: 'Profit', component: () => import('@/views/profit/ProfitView.vue') },
        { path: 'settings', name: 'Settings', component: () => import('@/views/settings/SettingsView.vue') },
        { path: 'alerts', name: 'Alerts', component: () => import('@/views/alert/AlertView.vue') },
        // ---- SaaS 新增路由 ----
        { path: 'pricing', name: 'Pricing', component: () => import('@/views/pricing/PricingView.vue') },
        { path: 'subscription', name: 'Subscription', component: () => import('@/views/subscription/SubscriptionView.vue') },
        { path: 'account', name: 'Account', component: () => import('@/views/account/AccountView.vue') },
        { path: 'admin', name: 'Admin', component: () => import('@/views/admin/AdminView.vue'), meta: { requiresAdmin: true } },
      ],
    },
    // 密码重置（无需登录）
    {
      path: '/reset-password',
      component: AuthLayout,
      children: [
        { path: '', name: 'ResetPassword', component: () => import('@/views/login/ResetPasswordView.vue') },
      ],
    },
    // 邮箱验证（无需登录）
    {
      path: '/verify-email',
      component: AuthLayout,
      children: [
        { path: '', name: 'VerifyEmail', component: () => import('@/views/login/VerifyEmailView.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/login' },
  ],
})

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if ((to.path === '/login' || to.path === '/register') && token) {
    next('/dashboard')
  } else if (to.meta.requiresAdmin) {
    // 简单的角色检查（从 token payload 解析 role）
    try {
      const payload = JSON.parse(atob(token!.split('.')[1]))
      if (payload.role !== 'admin') {
        next('/dashboard')
        return
      }
    } catch {
      next('/login')
      return
    }
    next()
  } else {
    next()
  }
})

export default router
