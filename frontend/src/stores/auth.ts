import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, fetchUserInfo } from '@/api/auth'
import type { LoginData, RegisterData, UserInfo } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  // ---- state ----
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<UserInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- getters ----
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  // ---- actions ----
  async function login(credentials: LoginData) {
    loading.value = true
    error.value = null
    try {
      const res = await apiLogin(credentials)
      token.value = res.access_token
      localStorage.setItem('access_token', res.access_token)
      user.value = res.user
      router.push('/dashboard')
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '登录失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function register(credentials: RegisterData) {
    loading.value = true
    error.value = null
    try {
      const res = await apiRegister(credentials)
      token.value = res.access_token
      localStorage.setItem('access_token', res.access_token)
      user.value = res.user
      router.push('/dashboard')
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '注册失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      user.value = await fetchUserInfo()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    error.value = null
    localStorage.removeItem('access_token')
    router.push('/login')
  }

  function clearError() {
    error.value = null
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    fetchUser,
    logout,
    clearError,
  }
})
