import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'

export interface PortStatus {
  port: number
  service_name: string
  custom_label?: string
  status: 'UP' | 'DOWN'
  recovery_task_id?: number
  is_managed: boolean
  is_container: boolean
  process_name?: string
}

export const usePortStore = defineStore('port', () => {
  const ports = ref<PortStatus[]>([])
  const isLoading = ref(false)

  async function fetchPortStatus() {
    isLoading.value = true
    try {
      const { data } = await apiClient.get<PortStatus[]>('/ports/status')
      ports.value = data
    } finally {
      isLoading.value = false
    }
  }

  async function restartService(port: number) {
    await apiClient.post(`/ports/${port}/restart`)
    await fetchPortStatus()
  }

  async function updatePortName(port: number, serviceName: string) {
    await apiClient.put(`/ports/${port}/name`, { service_name: serviceName })
    await fetchPortStatus()
  }

  async function updatePortLabel(port: number, customLabel: string | null) {
    await apiClient.put(`/ports/${port}/label`, { custom_label: customLabel })
    await fetchPortStatus()
  }

  async function updatePortManagement(port: number, payload: { is_monitored: boolean, recovery_task_id: number | null }) {
    await apiClient.put(`/ports/${port}/management`, payload)
    await fetchPortStatus()
  }

  return { ports, isLoading, fetchPortStatus, restartService, updatePortName, updatePortLabel, updatePortManagement }
})
