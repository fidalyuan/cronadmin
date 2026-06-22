import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const username = ref<string | null>(localStorage.getItem('username'))
  const systemMode = ref<string>('prod')

  async function fetchConfig() {
    try {
      const { data } = await apiClient.get<{ mode: string }>('/auth/config')
      systemMode.value = data.mode
    } catch (err) {
      console.error('Failed to fetch system mode config:', err)
    }
  }

  function setAuth(newToken: string, newUsername: string) {
    token.value = newToken
    username.value = newUsername
    localStorage.setItem('token', newToken)
    localStorage.setItem('username', newUsername)
  }

  function clearAuth() {
    token.value = null
    username.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    sessionStorage.clear() // 退出登录时数据清空还原
  }

  const isAuthenticated = () => !!token.value

  return { token, username, systemMode, fetchConfig, setAuth, clearAuth, isAuthenticated }
})
