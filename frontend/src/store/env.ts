import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import { useAuthStore } from './auth'

export interface RuntimeEnv {
  id: number
  name: string
  interpreter_path: string
  description?: string
}

export const useEnvStore = defineStore('env', () => {
  const envs = ref<RuntimeEnv[]>([])
  const isLoading = ref(false)

  async function fetchEnvs() {
    isLoading.value = true
    try {
      const authStore = useAuthStore()
      if (authStore.systemMode === 'demo') {
        const cached = sessionStorage.getItem('demo_envs')
        if (cached) {
          envs.value = JSON.parse(cached)
        } else {
          const { data } = await apiClient.get<RuntimeEnv[]>('/environments/')
          sessionStorage.setItem('demo_envs', JSON.stringify(data))
          envs.value = data
        }
      } else {
        const { data } = await apiClient.get<RuntimeEnv[]>('/environments/')
        envs.value = data
      }
    } finally {
      isLoading.value = false
    }
  }

  async function createEnv(env: Partial<RuntimeEnv>) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const newEnv: RuntimeEnv = {
        id: Math.max(...envs.value.map(e => e.id), 0) + 1,
        name: env.name || '',
        interpreter_path: env.interpreter_path || '',
        description: env.description || ''
      }
      envs.value.push(newEnv)
      sessionStorage.setItem('demo_envs', JSON.stringify(envs.value))
    } else {
      const { data } = await apiClient.post<RuntimeEnv>('/environments/', env)
      envs.value.push(data)
    }
  }

  async function deleteEnv(id: number) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      envs.value = envs.value.filter(e => e.id !== id)
      sessionStorage.setItem('demo_envs', JSON.stringify(envs.value))
    } else {
      await apiClient.delete(`/environments/${id}`)
      envs.value = envs.value.filter(e => e.id !== id)
    }
  }

  return { envs, isLoading, fetchEnvs, createEnv, deleteEnv }
})
