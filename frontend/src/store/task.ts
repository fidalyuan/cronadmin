import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'

export interface Task {
  id: number
  name: string
  script_path: string
  python_interpreter?: string
  cron_expression: string
  is_active: boolean
  config_hash?: string
  environment_params?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface TaskLog {
  id: number
  task_id: number
  start_time: string
  end_time?: string
  exit_code?: number
  stdout?: string
  stderr?: string
  status: string
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<Task[]>([])
  const isLoading = ref(false)

  async function fetchTasks() {
    isLoading.value = true
    try {
      const { data } = await apiClient.get<Task[]>('/tasks/')
      tasks.value = data
    } finally {
      isLoading.value = false
    }
  }

  async function toggleTask(id: number) {
    const { data } = await apiClient.post<Task>(`/tasks/${id}/toggle`)
    const index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) tasks.value[index] = data
  }

  async function runTaskNow(id: number) {
    await apiClient.post(`/tasks/${id}/run`)
  }

  async function createTask(task: Partial<Task>) {
    const { data } = await apiClient.post<Task>('/tasks/', task)
    tasks.value.push(data)
  }

  async function updateTask(id: number, task: Partial<Task>) {
    const { data } = await apiClient.put<Task>(`/tasks/${id}`, task)
    const index = tasks.value.findIndex(t => t.id === id)
    if (index !== -1) tasks.value[index] = data
  }

  async function fetchLogs(id: number) {
    const { data } = await apiClient.get<TaskLog[]>(`/tasks/${id}/logs`)
    return data
  }

  async function fetchLogContent(logId: number) {
    const { data } = await apiClient.get(`/tasks/logs/${logId}/file`, { responseType: 'text' })
    return data
  }

  return { tasks, isLoading, fetchTasks, toggleTask, runTaskNow, createTask, updateTask, fetchLogs, fetchLogContent }
})
