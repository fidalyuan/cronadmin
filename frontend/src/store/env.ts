import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'

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
      const { data } = await apiClient.get<RuntimeEnv[]>('/environments/')
      envs.value = data
    } finally {
      isLoading.value = false
    }
  }

  async function createEnv(env: Partial<RuntimeEnv>) {
    const { data } = await apiClient.post<RuntimeEnv>('/environments/', env)
    envs.value.push(data)
  }

  async function deleteEnv(id: number) {
    await apiClient.delete(`/environments/${id}`)
    envs.value = envs.value.filter(e => e.id !== id)
  }

  return { envs, isLoading, fetchEnvs, createEnv, deleteEnv }
})
