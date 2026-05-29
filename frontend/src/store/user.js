import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)  // { username, user_id, role, ... }
  const profile = ref(null)   // 完整个人信息

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin' || userInfo.value?.role === 'super_admin')

  async function login(username, password) {
    const { data } = await authApi.login({ username, password })
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    userInfo.value = {
      username: data.username,
      user_id: data.user_id,
      role: data.role,
    }
    localStorage.setItem('user_info', JSON.stringify(userInfo.value))
  }

  async function register(username, email, password) {
    await authApi.register({ username, email, password })
  }

  async function fetchProfile() {
    try {
      const { data } = await authApi.getProfile()
      profile.value = data
      userInfo.value = {
        username: data.username,
        user_id: data.id,
        role: data.role,
      }
    } catch { /* ignore */ }
  }

  async function updateProfile(updates) {
    await authApi.updateProfile(updates)
    await fetchProfile()
  }

  async function changePassword(oldPwd, newPwd) {
    await authApi.changePassword(oldPwd, newPwd)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    profile.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user_info')
  }

  // 从 localStorage 恢复登录状态（刷新页面后）
  function restoreSession() {
    const saved = localStorage.getItem('user_info')
    if (saved && token.value) {
      try { userInfo.value = JSON.parse(saved) } catch { /* ignore */ }
    }
  }
  restoreSession()

  return {
    token, userInfo, profile, isLoggedIn, isAdmin,
    login, register, fetchProfile, updateProfile, changePassword, logout,
  }
})
