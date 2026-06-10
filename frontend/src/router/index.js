import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { title: '注册', guest: true },
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '实时看板', requiresAuth: true },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue'),
    meta: { title: '历史趋势', requiresAuth: true },
  },
  {
    path: '/cluster',
    name: 'Cluster',
    component: () => import('../views/Cluster.vue'),
    meta: { title: '聚类分析', requiresAuth: true },
  },
  {
    path: '/health-report',
    name: 'HealthReport',
    component: () => import('../views/HealthReport.vue'),
    meta: { title: '健康报告', requiresAuth: true },
  },
  {
    path: '/assistant',
    name: 'SmartAssistant',
    component: () => import('../views/SmartAssistant.vue'),
    meta: { title: '智能客服', requiresAuth: true },
  },
  {
    path: '/posture-calendar',
    name: 'PostureCalendar',
    component: () => import('../views/PostureCalendar.vue'),
    meta: { title: '14天坐姿分析', requiresAuth: true },
  },
  {
    path: '/calendar',
    name: 'CalendarView',
    component: () => import('../views/CalendarView.vue'),
    meta: { title: '坐姿日历', requiresAuth: true },
  },
  {
    path: '/activities',
    name: 'Activities',
    component: () => import('../views/Activities.vue'),
    meta: { title: '活动中心', requiresAuth: true },
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { title: '个人中心', requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    next('/dashboard')
  } else {
    next()
  }
})

// 设置页面标题
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - 智能坐姿监测` : '智能坐姿监测系统'
})

export default router
