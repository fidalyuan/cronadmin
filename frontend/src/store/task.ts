import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '../api/client'
import { useAuthStore } from './auth'

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
      const authStore = useAuthStore()
      if (authStore.systemMode === 'demo') {
        const cached = sessionStorage.getItem('demo_tasks')
        if (cached) {
          tasks.value = JSON.parse(cached)
        } else {
          const { data } = await apiClient.get<Task[]>('/tasks/')
          sessionStorage.setItem('demo_tasks', JSON.stringify(data))
          tasks.value = data
        }
      } else {
        const { data } = await apiClient.get<Task[]>('/tasks/')
        tasks.value = data
      }
    } finally {
      isLoading.value = false
    }
  }

  async function toggleTask(id: number) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value[index].is_active = !tasks.value[index].is_active
        sessionStorage.setItem('demo_tasks', JSON.stringify(tasks.value))
      }
    } else {
      const { data } = await apiClient.post<Task>(`/tasks/${id}/toggle`)
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) tasks.value[index] = data
    }
  }

  async function runTaskNow(id: number) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const cachedLogs = sessionStorage.getItem('demo_logs')
      let logsList: TaskLog[] = cachedLogs ? JSON.parse(cachedLogs) : []
      const newLog: TaskLog = {
        id: Math.max(...logsList.map(l => l.id), 0) + 1,
        task_id: id,
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        exit_code: 0,
        stdout: `[Demo 模式] 任务手动触发成功！\n模拟执行脚本...\n执行完毕，返回码 0。`,
        stderr: '',
        status: 'success'
      }
      logsList.unshift(newLog)
      sessionStorage.setItem('demo_logs', JSON.stringify(logsList))
    } else {
      await apiClient.post(`/tasks/${id}/run`)
    }
  }

  async function createTask(task: Partial<Task>) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const newTask: Task = {
        id: Math.max(...tasks.value.map(t => t.id), 0) + 1,
        name: task.name || '',
        script_path: task.script_path || '',
        python_interpreter: task.python_interpreter || '',
        cron_expression: task.cron_expression || '* * * * *',
        is_active: task.is_active ?? true,
        environment_params: task.environment_params || {},
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      tasks.value.push(newTask)
      sessionStorage.setItem('demo_tasks', JSON.stringify(tasks.value))
    } else {
      const { data } = await apiClient.post<Task>('/tasks/', task)
      tasks.value.push(data)
    }
  }

  async function updateTask(id: number, task: Partial<Task>) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        const updated = {
          ...tasks.value[index],
          ...task,
          updated_at: new Date().toISOString()
        }
        tasks.value[index] = updated
        sessionStorage.setItem('demo_tasks', JSON.stringify(tasks.value))
      }
    } else {
      const { data } = await apiClient.put<Task>(`/tasks/${id}`, task)
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) tasks.value[index] = data
    }
  }

  async function fetchLogs(id: number) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const cachedLogs = sessionStorage.getItem('demo_logs')
      let logsList: TaskLog[] = cachedLogs ? JSON.parse(cachedLogs) : []
      const filtered = logsList.filter(l => l.task_id === id)
      if (filtered.length > 0) {
        return filtered
      }
      try {
        const { data } = await apiClient.get<TaskLog[]>(`/tasks/${id}/logs`)
        const combined = [...logsList, ...data.filter(d => !logsList.some(l => l.id === d.id))]
        sessionStorage.setItem('demo_logs', JSON.stringify(combined))
        return combined.filter(l => l.task_id === id)
      } catch {
        return []
      }
    } else {
      const { data } = await apiClient.get<TaskLog[]>(`/tasks/${id}/logs`)
      return data
    }
  }

  async function fetchLogContent(logId: number) {
    const authStore = useAuthStore()
    if (authStore.systemMode === 'demo') {
      const cachedLogs = sessionStorage.getItem('demo_logs')
      const logsList: TaskLog[] = cachedLogs ? JSON.parse(cachedLogs) : []
      const log = logsList.find(l => l.id === logId)
      if (log) {
        return log.stdout || ''
      }
    }
    const { data } = await apiClient.get(`/tasks/logs/${logId}/file`, { responseType: 'text' })
    return data
  }

  return { tasks, isLoading, fetchTasks, toggleTask, runTaskNow, createTask, updateTask, fetchLogs, fetchLogContent }
})
