import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import { useAuthStore } from './auth'

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
      const authStore = useAuthStore()
      if (authStore.systemMode === 'demo') {
        const cached = sessionStorage.getItem('demo_ports')
        if (cached) {
          ports.value = JSON.parse(cached)
        } else {
          const { data } = await apiClient.get<PortStatus[]>('/ports/status')
          sessionStorage.setItem('demo_ports', JSON.stringify(data))
          ports.value = data
        }
      } else {
        const { data } = await apiClient.get<PortStatus[]>('/ports/status')
        ports.value = data
      }
    } finally {
      isLoading.value = false
    }
  }

  async function restartService(port: number) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const index = ports.value.findIndex(p => p.port === port)
      if (index !== -1) {
        ports.value[index].status = 'UP'
        sessionStorage.setItem('demo_ports', JSON.stringify(ports.value))
      }
    } else {
      await apiClient.post(`/ports/${port}/restart`)
      await fetchPortStatus()
    }
  }

  async function updatePortName(port: number, serviceName: string) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const index = ports.value.findIndex(p => p.port === port)
      if (index !== -1) {
        ports.value[index].service_name = serviceName
        sessionStorage.setItem('demo_ports', JSON.stringify(ports.value))
      }
    } else {
      await apiClient.put(`/ports/${port}/name`, { service_name: serviceName })
      await fetchPortStatus()
    }
  }

  async function updatePortLabel(port: number, customLabel: string | null) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const index = ports.value.findIndex(p => p.port === port)
      if (index !== -1) {
        ports.value[index].custom_label = customLabel || undefined
        sessionStorage.setItem('demo_ports', JSON.stringify(ports.value))
      }
    } else {
      await apiClient.put(`/ports/${port}/label`, { custom_label: customLabel })
      await fetchPortStatus()
    }
  }

  async function updatePortManagement(port: number, payload: { is_monitored: boolean, recovery_task_id: number | null }) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const index = ports.value.findIndex(p => p.port === port)
      if (index !== -1) {
        ports.value[index].is_managed = payload.is_monitored
        ports.value[index].recovery_task_id = payload.recovery_task_id || undefined
        sessionStorage.setItem('demo_ports', JSON.stringify(ports.value))
      }
    } else {
      await apiClient.put(`/ports/${port}/management`, payload)
      await fetchPortStatus()
    }
  }

  return { ports, isLoading, fetchPortStatus, restartService, updatePortName, updatePortLabel, updatePortManagement }
})
