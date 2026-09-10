import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sa-token') || '')
  const userInfo = ref((() => {
    try {
      const raw = localStorage.getItem('user-info')
      return raw && raw !== 'undefined' ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })())

  const isLoggedIn = computed(() => !!token.value && !!userInfo.value)

  async function login(operatorId) {
    const res = await authApi.login({ operatorId })
    const data = res.data
    token.value = data.token
    userInfo.value = {
      username: data.username,
      role: data.role,
      operatorId: data.operatorId,
      storeId: data.storeId,
    }
    localStorage.setItem('sa-token', token.value)
    localStorage.setItem('user-info', JSON.stringify(userInfo.value))
    return data
  }

  function clearAuth() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('sa-token')
    localStorage.removeItem('user-info')
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      clearAuth()
      const { default: router } = await import('@/router')
      router.push('/login')
    }
  }

  return { token, userInfo, isLoggedIn, login, logout, clearAuth }
})
