<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { usePortStore, type PortStatus } from '../../store/port'
import { useTaskStore } from '../../store/task'
import { RefreshCw, Activity, ShieldCheck, ShieldAlert, Container, Info, Globe, Lock, Terminal as TerminalIcon, LayoutGrid, List, Edit2, RotateCcw, Settings, Plus } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useWindowSize } from '@vueuse/core'

const portStore = usePortStore()
const taskStore = useTaskStore()
let timer: number | null = null
const filterManaged = ref(false)
const viewMode = ref<'grid' | 'list'>('list')
const isGrouped = ref(true)
const { width } = useWindowSize()

const showManageDialog = ref(false)
const selectedPortForManage = ref<PortStatus | null>(null)
const manageForm = ref({
  is_monitored: false,
  recovery_task_id: null as number | null
})

const groupedPorts = computed(() => {
  const ports = filterManaged.value ? portStore.ports.filter(p => p.is_managed) : portStore.ports
  const groups: Record<string, PortStatus[]> = {}
  ports.forEach(port => {
    const name = port.custom_label || port.process_name || '系统进程'
    if (!groups[name]) groups[name] = []
    groups[name].push(port)
  })
  return groups
})

const flatPorts = computed(() => {
  return filterManaged.value ? portStore.ports.filter(p => p.is_managed) : portStore.ports
})

onMounted(() => {
  portStore.fetchPortStatus()
  taskStore.fetchTasks()
  timer = window.setInterval(() => {
    portStore.fetchPortStatus()
  }, 10000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

const handleEditName = (port: PortStatus) => {
  ElMessageBox.prompt('请输入新的端口用途名称', '编辑端口用途', {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputValue: port.service_name !== 'unknown' ? port.service_name : '',
    inputPattern: /\S+/,
    inputErrorMessage: '名称不能为空',
    confirmButtonClass: 'bg-blue-600 border-none px-6 rounded-lg font-bold text-white',
    cancelButtonClass: 'text-slate-500 dark:text-slate-400 font-bold hover:bg-slate-100 dark:hover:bg-slate-800',
    customClass: 'custom-dialog',
  }).then(async ({ value }) => {
    try {
      await portStore.updatePortName(port.port, value)
      ElMessage.success('用途名称已保存')
    } catch (err) {
      ElMessage.error('保存失败')
    }
  }).catch(() => {})
}

const handleEditLabel = (port: PortStatus) => {
  ElMessageBox.prompt('请输入新的自定义分组标签', '编辑分组标签', {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputValue: port.custom_label || '',
    inputPlaceholder: '例如：核心数据库、前端网关...',
    confirmButtonClass: 'bg-blue-600 border-none px-6 rounded-lg font-bold text-white',
    cancelButtonClass: 'text-slate-500 dark:text-slate-400 font-bold hover:bg-slate-100 dark:hover:bg-slate-800',
    customClass: 'custom-dialog',
  }).then(async ({ value }) => {
    try {
      await portStore.updatePortLabel(port.port, value || null)
      ElMessage.success('分组标签已更新')
    } catch (err) {
      ElMessage.error('更新失败')
    }
  }).catch(() => {})
}

const handleManagePort = (port: PortStatus) => {
  selectedPortForManage.value = port
  manageForm.value.is_monitored = port.is_managed
  manageForm.value.recovery_task_id = port.recovery_task_id || null
  showManageDialog.value = true
}

const saveManageSettings = async () => {
  if (!selectedPortForManage.value) return
  try {
    await portStore.updatePortManagement(selectedPortForManage.value.port, {
      is_monitored: manageForm.value.is_monitored,
      recovery_task_id: manageForm.value.recovery_task_id
    })
    ElMessage.success('管理配置已保存')
    showManageDialog.value = false
  } catch (err) {
    ElMessage.error('保存失败')
  }
}

const handleRestart = (port: PortStatus) => {
  const isContainer = port.is_container
  const actionText = isContainer ? '重启容器' : '重启进程'
  const targetText = isContainer ? `Podman 容器 [端口 ${port.port}]` : `原生进程 [端口 ${port.port}]`

  ElMessageBox.confirm(
    `确定要尝试 ${actionText} 吗？\n针对对象: ${targetText}`,
    actionText,
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      confirmButtonClass: 'bg-blue-600 border-none px-6 rounded-lg font-bold text-white',
      cancelButtonClass: 'text-slate-500 dark:text-slate-400 font-bold hover:bg-slate-100 dark:hover:bg-slate-800',
      type: 'warning',
    }
  ).then(async () => {
    try {
      await portStore.restartService(port.port)
      ElMessage({
        message: `${actionText}指令已下发`,
        type: 'success',
        plain: true
      })
    } catch (err: any) {
      const msg = err.response?.data?.detail || '操作失败'
      ElMessage({
        message: msg,
        type: 'error',
        plain: true
      })
    }
  })
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-10 pb-20">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-8">
      <div class="space-y-2">
        <div class="flex items-center gap-3">
          <h2 class="text-4xl font-black text-slate-900 dark:text-white tracking-tight">网络哨兵</h2>
          <div class="flex items-center gap-1.5 px-3 py-1 bg-emerald-100 dark:bg-emerald-500/10 rounded-full">
            <div class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping"></div>
            <span class="text-[10px] font-black text-emerald-600 dark:text-emerald-500 tracking-widest">实时扫描中</span>
          </div>
        </div>
        <p class="text-slate-500 font-medium max-w-lg">深度扫描系统网络堆栈，实时监控 {{ portStore.ports.length }} 个活跃端口及对应进程状态。</p>
      </div>

      <div class="flex flex-col lg:flex-row lg:items-center gap-4 bg-white dark:bg-slate-800/30 p-4 lg:p-2 rounded-3xl lg:rounded-2xl border border-slate-200 dark:border-slate-800/50 backdrop-blur-sm shadow-sm dark:shadow-none w-full lg:w-auto">
        <div class="flex items-center justify-between lg:justify-start gap-4 w-full lg:w-auto">
          <!-- View Mode Toggle -->
          <div class="flex bg-slate-100 dark:bg-slate-900/50 rounded-xl p-1 border border-slate-200 dark:border-slate-700/50">
            <button 
              @click="viewMode = 'grid'" 
              :class="viewMode === 'grid' ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'" 
              class="p-1.5 rounded-lg transition-all"
              title="网格视图"
            >
              <LayoutGrid :size="16" />
            </button>
            <button 
              @click="viewMode = 'list'" 
              :class="viewMode === 'list' ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'" 
              class="p-1.5 rounded-lg transition-all"
              title="列表视图"
            >
              <List :size="16" />
            </button>
          </div>
          
          <button 
            @click="portStore.fetchPortStatus()" 
            :disabled="portStore.isLoading"
            class="lg:hidden flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-black transition-all active:scale-95 shadow-md"
          >
            <RefreshCw :size="14" :class="{'animate-spin': portStore.isLoading}" />
            刷新
          </button>
        </div>

        <div class="flex flex-col sm:flex-row sm:items-center gap-4 w-full lg:w-auto border-t lg:border-t-0 pt-4 lg:pt-0 border-slate-200 dark:border-slate-800">
          <div class="flex items-center justify-between sm:justify-start gap-2 sm:px-4 sm:border-l sm:border-r border-slate-200 dark:border-slate-700/50 w-full sm:w-auto">
            <span class="text-xs font-bold text-slate-600 dark:text-slate-500 tracking-tighter text-nowrap">进程分组</span>
            <el-switch v-model="isGrouped" size="small" />
          </div>

          <div class="flex items-center justify-between sm:justify-start gap-2 sm:pr-4 sm:border-r border-slate-200 dark:border-slate-700/50 w-full sm:w-auto">
            <span class="text-xs font-bold text-slate-600 dark:text-slate-500 tracking-tighter text-nowrap">仅管理端口</span>
            <el-switch v-model="filterManaged" size="small" />
          </div>
        </div>

        <button 
          @click="portStore.fetchPortStatus()" 
          :disabled="portStore.isLoading"
          class="hidden lg:flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-xl text-xs font-black transition-all active:scale-95 shadow-md"
        >
          <RefreshCw :size="14" :class="{'animate-spin': portStore.isLoading}" />
          刷新列表
        </button>
      </div>
    </div>

    <!-- Port Groups Container -->
    <div class="space-y-12">
      <!-- Grouped View -->
      <template v-if="isGrouped">
        <div v-for="(ports, processName) in groupedPorts" :key="processName" 
          class="group/box bg-slate-50/50 dark:bg-slate-900/10 border-2 border-slate-200 dark:border-slate-800 rounded-[2.5rem] p-8 space-y-6 shadow-inner transition-all duration-500 hover:shadow-2xl hover:shadow-sky-500/20 dark:hover:shadow-amber-500/10 hover:border-sky-300 dark:hover:border-amber-500/50 relative overflow-hidden"
        >
          <!-- Background Glow Effect -->
          <div class="absolute inset-0 bg-gradient-to-br from-sky-100/50 to-transparent dark:from-amber-500/10 dark:to-transparent opacity-0 group-hover/box:opacity-100 transition-opacity duration-500 pointer-events-none"></div>

          <!-- Group Header -->
          <div class="flex items-center gap-3 px-2 relative z-10">
            <div class="p-2 bg-slate-200 dark:bg-slate-800 rounded-xl border border-slate-300 dark:border-slate-700 shadow-sm">
              <TerminalIcon class="w-4 h-4 text-slate-600 dark:text-blue-400" />
            </div>
            <h3 class="flex items-center gap-3 text-sm font-black text-slate-500 dark:text-slate-400">
              <span class="tracking-[0.2em] uppercase">所属进程</span>
              <span class="px-3 py-1 rounded-xl bg-sky-100 dark:bg-amber-500/20 text-sky-700 dark:text-amber-400 font-mono text-base border border-sky-200 dark:border-amber-500/30 shadow-sm tracking-[0.35em]">{{ processName }}</span>
            </h3>
            <div class="flex-1 h-[1px] bg-slate-200 dark:bg-slate-800/50 ml-4"></div>
          </div>

          <div :class="viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6' : 'flex flex-col gap-4'">
            <template v-for="port in ports" :key="port.port">
              <!-- Grid View Card -->
              <div 
                v-if="viewMode === 'grid'"
                class="group relative bg-white dark:bg-[#1e293b]/30 backdrop-blur-sm border-2 border-slate-200 dark:border-slate-800 rounded-3xl p-6 transition-all duration-500 hover:translate-y-[-4px] hover:bg-white dark:hover:bg-[#1e293b]/60 hover:shadow-xl dark:hover:shadow-2xl hover:shadow-blue-500/5 dark:hover:shadow-blue-500/10"
                :class="port.status === 'UP' ? 'hover:border-blue-300 dark:hover:border-blue-500/30' : 'border-rose-300 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/[0.02]'"
              >
                <div class="flex justify-between items-start mb-6">
                  <div class="space-y-0.5">
                    <div class="flex items-center gap-2 mb-1">
                      <div :class="[
                        'w-1.5 h-1.5 rounded-full',
                        port.status === 'UP' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]'
                      ]"></div>
                      <span class="text-[10px] font-black uppercase tracking-[0.2em]" :class="port.status === 'UP' ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'">{{ port.status === 'UP' ? '正常' : '异常' }}</span>
                    </div>
                    <div class="flex items-center gap-2 group/edit cursor-pointer" @click="handleEditName(port)">
                      <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200 truncate max-w-[120px]" :title="port.service_name">{{ port.service_name }}</h3>
                      <Edit2 :size="14" class="text-slate-400 opacity-0 group-hover/edit:opacity-100 transition-opacity hover:text-blue-500" />
                    </div>
                  </div>
                  
                  <div class="flex items-center gap-2">
                    <button @click="handleManagePort(port)" class="p-2 rounded-xl bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 hover:bg-blue-600 hover:border-blue-500 hover:text-white transition-all text-slate-400 dark:text-slate-500">
                      <Settings :size="16" />
                    </button>
                    <div class="p-2.5 rounded-2xl bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500">
                      <component :is="port.is_managed ? Lock : Globe" :size="18" />
                    </div>
                  </div>
                </div>

                <div class="flex items-baseline gap-1 mb-6">
                  <span class="text-3xl font-black text-slate-900 dark:text-white tracking-tighter">{{ port.port }}</span>
                  <span class="text-xs font-bold text-slate-400 dark:text-slate-600">端口</span>
                </div>

                <div class="space-y-4">
                  <div class="bg-slate-100/50 dark:bg-slate-900/40 rounded-2xl p-4 border border-slate-200 dark:border-slate-800/50 group-hover:border-blue-400/50 dark:group-hover:border-blue-500/30 transition-colors shadow-inner cursor-pointer group/label" @click="handleEditLabel(port)">
                    <div v-if="port.custom_label" class="mb-2 pb-2 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                      <span class="text-xs font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest">{{ port.custom_label }}</span>
                      <Edit2 :size="10" class="text-blue-400 opacity-0 group-hover/label:opacity-100" />
                    </div>
                    <div class="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                      <TerminalIcon :size="14" class="text-slate-400 dark:text-slate-600" />
                      <span class="text-xs font-mono truncate">{{ port.process_name || '系统进程' }}</span>
                      <Plus v-if="!port.custom_label" :size="10" class="text-slate-400 opacity-0 group-hover/label:opacity-100 ml-auto" />
                    </div>
                  </div>
                  
                  <div class="flex gap-2">
                    <template v-if="port.is_container">
                      <button 
                        @click="handleRestart(port)"
                        class="flex-1 flex items-center justify-center gap-2 py-3 bg-slate-800 hover:bg-slate-900 text-white rounded-2xl text-[10px] font-black tracking-widest transition-all active:scale-95 shadow-md"
                      >
                        <Container :size="14" />
                        重启容器
                      </button>
                    </template>
                    <template v-else-if="port.is_managed">
                      <button 
                        @click="handleRestart(port)"
                        class="flex-1 flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl text-[10px] font-black tracking-widest transition-all active:scale-95 shadow-md"
                      >
                        <RotateCcw :size="14" />
                        重启进程
                      </button>
                    </template>
                  </div>
                </div>
              </div>

              <!-- List View Row -->
              <div 
                v-else-if="viewMode === 'list'"
                class="flex flex-col sm:flex-row sm:items-center justify-between bg-white dark:bg-[#1e293b]/30 backdrop-blur-sm border-2 border-slate-300 dark:border-slate-800 rounded-2xl p-4 transition-all hover:bg-slate-50 dark:hover:bg-[#1e293b]/60 hover:shadow-lg hover:border-blue-400 dark:hover:border-slate-600 shadow-sm"
                :class="port.status === 'UP' ? 'hover:border-blue-500 dark:hover:border-blue-500/30' : 'border-rose-400 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/[0.02]'"
              >
                <div class="flex items-center gap-6 md:w-1/3">
                  <div class="w-16 flex justify-center">
                    <span class="text-3xl font-black text-slate-900 dark:text-white tracking-tighter drop-shadow-sm">{{ port.port }}</span>
                  </div>
                  <div class="space-y-1">
                    <div class="flex items-center gap-2 group/edit cursor-pointer" @click="handleEditName(port)">
                      <h3 class="text-lg font-black text-slate-900 dark:text-slate-200 truncate max-w-[200px]" :title="port.service_name">{{ port.service_name }}</h3>
                      <Edit2 :size="16" class="text-slate-600 dark:text-slate-400 opacity-0 group-hover/edit:opacity-100 transition-opacity hover:text-blue-600 dark:hover:text-blue-500" />
                    </div>
                    <div class="flex items-center gap-2">
                      <div :class="[
                        'w-2 h-2 rounded-full',
                        port.status === 'UP' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-rose-600 shadow-[0_0_8px_rgba(225,29,72,0.8)]'
                      ]"></div>
                      <span class="text-[11px] font-black tracking-widest" :class="port.status === 'UP' ? 'text-emerald-800 dark:text-emerald-500' : 'text-rose-800 dark:text-rose-500'">{{ port.status === 'UP' ? '正常' : '异常' }}</span>
                      <el-tag v-if="port.is_managed" size="small" type="success" effect="dark" class="ml-2 scale-90 origin-left border-emerald-600 bg-emerald-600 dark:bg-emerald-700 dark:border-emerald-700 text-white font-bold shadow-sm">已接管</el-tag>
                      <el-tag v-else size="small" type="info" effect="dark" class="ml-2 scale-90 origin-left border-slate-500 bg-slate-500 dark:bg-slate-700 dark:border-slate-700 text-white font-bold shadow-sm">系统进程</el-tag>
                    </div>
                  </div>
                </div>

                <div class="flex-1 flex items-center my-4 sm:my-0 text-slate-800 dark:text-slate-400 bg-slate-200 dark:bg-slate-900/40 rounded-xl border border-slate-300 dark:border-slate-800/50 w-full sm:w-auto shadow-inner overflow-hidden group/label cursor-pointer" @click="handleEditLabel(port)">
                  <!-- Left Side: Custom Label (if exists) -->
                  <div v-if="port.custom_label" class="flex-1 px-4 py-3 border-r border-slate-300 dark:border-slate-700 bg-blue-500/5 dark:bg-blue-500/10 flex items-center justify-between group-hover/label:bg-blue-500/10 transition-colors">
                    <span class="text-sm font-black text-blue-700 dark:text-blue-400 truncate">{{ port.custom_label }}</span>
                    <Edit2 :size="12" class="text-blue-400 opacity-0 group-hover/label:opacity-100" />
                  </div>
                  <!-- Right Side: Process Name -->
                  <div class="flex-1 px-4 py-3 flex items-center gap-3 min-w-0">
                    <TerminalIcon :size="18" class="text-slate-700 dark:text-slate-500 shrink-0" />
                    <span class="text-sm font-bold font-mono truncate" :title="port.process_name || '系统进程'">{{ port.process_name || '系统进程' }}</span>
                    <Plus v-if="!port.custom_label" :size="12" class="text-slate-500 opacity-0 group-hover/label:opacity-100 ml-auto" />
                  </div>
                </div>

                <div class="flex items-center gap-4 md:w-1/4 justify-end">
                  <button @click="handleManagePort(port)" class="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-blue-600 hover:text-white transition-all text-slate-400">
                    <Settings :size="18" />
                  </button>
                  <component :is="port.is_managed ? Lock : Globe" :size="20" class="text-slate-700 dark:text-slate-500 hidden lg:block drop-shadow-sm" />
                  
                  <template v-if="port.is_container">
                    <button 
                      @click="handleRestart(port)"
                      class="flex items-center gap-2 px-5 py-2.5 bg-slate-800 dark:bg-slate-800 hover:bg-slate-900 dark:hover:bg-slate-700 text-white rounded-xl text-xs font-black transition-colors shrink-0 shadow-md"
                    >
                      <Container :size="16" />
                      <span class="hidden sm:inline">重启容器</span>
                      <span class="sm:hidden">重启</span>
                    </button>
                  </template>
                  
                  <template v-else-if="port.is_managed">
                    <button 
                      @click="handleRestart(port)"
                      class="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black transition-colors shrink-0 shadow-md"
                    >
                      <RotateCcw :size="16" />
                      <span class="hidden sm:inline">重启进程</span>
                      <span class="sm:hidden">重启</span>
                    </button>
                  </template>
                </div>
              </div>
            </template>
          </div>
        </div>
      </template>

      <!-- Non-Grouped View -->
      <template v-else>
        <div :class="viewMode === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6' : 'flex flex-col gap-4'">
          <template v-for="port in flatPorts" :key="port.port">
            <!-- Grid View Card -->
            <div 
              v-if="viewMode === 'grid'"
              class="group relative bg-white dark:bg-[#1e293b]/30 backdrop-blur-sm border-2 border-slate-200 dark:border-slate-800 rounded-3xl p-6 transition-all duration-500 hover:translate-y-[-4px] hover:bg-white dark:hover:bg-[#1e293b]/60 hover:shadow-xl dark:hover:shadow-2xl hover:shadow-blue-500/5 dark:hover:shadow-blue-500/10"
              :class="port.status === 'UP' ? 'hover:border-blue-300 dark:hover:border-blue-500/30' : 'border-rose-300 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/[0.02]'"
            >
              <div class="flex justify-between items-start mb-6">
                <div class="space-y-0.5">
                  <div class="flex items-center gap-2 mb-1">
                    <div :class="[
                      'w-1.5 h-1.5 rounded-full',
                      port.status === 'UP' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]'
                    ]"></div>
                    <span class="text-[10px] font-black uppercase tracking-[0.2em]" :class="port.status === 'UP' ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'">{{ port.status === 'UP' ? '正常' : '异常' }}</span>
                  </div>
                  <div class="flex items-center gap-2 group/edit cursor-pointer" @click="handleEditName(port)">
                    <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200 truncate max-w-[120px]" :title="port.service_name">{{ port.service_name }}</h3>
                    <Edit2 :size="14" class="text-slate-400 opacity-0 group-hover/edit:opacity-100 transition-opacity hover:text-blue-500" />
                  </div>
                </div>
                
                <div class="flex items-center gap-2">
                  <button @click="handleManagePort(port)" class="p-2 rounded-xl bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 hover:bg-blue-600 hover:border-blue-500 hover:text-white transition-all text-slate-400 dark:text-slate-500">
                    <Settings :size="16" />
                  </button>
                  <div class="p-2.5 rounded-2xl bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500">
                    <component :is="port.is_managed ? Lock : Globe" :size="18" />
                  </div>
                </div>
              </div>

              <div class="flex items-baseline gap-1 mb-6">
                <span class="text-3xl font-black text-slate-900 dark:text-white tracking-tighter">{{ port.port }}</span>
                <span class="text-xs font-bold text-slate-400 dark:text-slate-600">端口</span>
              </div>

              <div class="space-y-4">
                <div class="bg-slate-100/50 dark:bg-slate-900/40 rounded-2xl p-4 border border-slate-200 dark:border-slate-800/50 group-hover:border-blue-400/50 dark:group-hover:border-blue-500/30 transition-colors shadow-inner cursor-pointer group/label" @click="handleEditLabel(port)">
                  <div v-if="port.custom_label" class="mb-2 pb-2 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                    <span class="text-xs font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest">{{ port.custom_label }}</span>
                    <Edit2 :size="10" class="text-blue-400 opacity-0 group-hover/label:opacity-100" />
                  </div>
                  <div class="flex items-center gap-3 text-slate-500 dark:text-slate-400">
                    <TerminalIcon :size="14" class="text-slate-400 dark:text-slate-600" />
                    <span class="text-xs font-mono truncate">{{ port.process_name || '系统进程' }}</span>
                    <Plus v-if="!port.custom_label" :size="10" class="text-slate-400 opacity-0 group-hover/label:opacity-100 ml-auto" />
                  </div>
                </div>
                
                <div class="flex gap-2">
                  <template v-if="port.is_container">
                    <button 
                      @click="handleRestart(port)"
                      class="flex-1 flex items-center justify-center gap-2 py-3 bg-slate-800 hover:bg-slate-900 text-white rounded-2xl text-[10px] font-black tracking-widest transition-all active:scale-95 shadow-md"
                    >
                      <Container :size="14" />
                      重启容器
                    </button>
                  </template>
                  <template v-else-if="port.is_managed">
                    <button 
                      @click="handleRestart(port)"
                      class="flex-1 flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl text-[10px] font-black tracking-widest transition-all active:scale-95 shadow-md"
                    >
                      <RotateCcw :size="14" />
                      重启进程
                    </button>
                  </template>
                </div>
              </div>
            </div>

            <!-- List View Row -->
            <div 
              v-else-if="viewMode === 'list'"
              class="flex flex-col sm:flex-row sm:items-center justify-between bg-white dark:bg-[#1e293b]/30 backdrop-blur-sm border-2 border-slate-300 dark:border-slate-800 rounded-2xl p-4 transition-all hover:bg-slate-50 dark:hover:bg-[#1e293b]/60 hover:shadow-lg hover:border-blue-400 dark:hover:border-slate-600 shadow-sm"
              :class="port.status === 'UP' ? 'hover:border-blue-500 dark:hover:border-blue-500/30' : 'border-rose-400 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/[0.02]'"
            >
              <div class="flex items-center gap-6 md:w-1/3">
                <div class="w-16 flex justify-center">
                  <span class="text-3xl font-black text-slate-900 dark:text-white tracking-tighter drop-shadow-sm">{{ port.port }}</span>
                </div>
                <div class="space-y-1">
                  <div class="flex items-center gap-2 group/edit cursor-pointer" @click="handleEditName(port)">
                    <h3 class="text-lg font-black text-slate-900 dark:text-slate-200 truncate max-w-[200px]" :title="port.service_name">{{ port.service_name }}</h3>
                    <Edit2 :size="16" class="text-slate-600 dark:text-slate-400 opacity-0 group-hover/edit:opacity-100 transition-opacity hover:text-blue-600 dark:hover:text-blue-500" />
                  </div>
                  <div class="flex items-center gap-2">
                    <div :class="[
                      'w-2 h-2 rounded-full',
                      port.status === 'UP' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-rose-600 shadow-[0_0_8px_rgba(225,29,72,0.8)]'
                    ]"></div>
                    <span class="text-[11px] font-black tracking-widest" :class="port.status === 'UP' ? 'text-emerald-800 dark:text-emerald-500' : 'text-rose-800 dark:text-rose-500'">{{ port.status === 'UP' ? '正常' : '异常' }}</span>
                    <el-tag v-if="port.is_managed" size="small" type="success" effect="dark" class="ml-2 scale-90 origin-left border-emerald-600 bg-emerald-600 dark:bg-emerald-700 dark:border-emerald-700 text-white font-bold shadow-sm">已接管</el-tag>
                    <el-tag v-else size="small" type="info" effect="dark" class="ml-2 scale-90 origin-left border-slate-500 bg-slate-500 dark:bg-slate-700 dark:border-slate-700 text-white font-bold shadow-sm">系统进程</el-tag>
                  </div>
                </div>
              </div>

              <div class="flex-1 flex items-center my-4 sm:my-0 text-slate-800 dark:text-slate-400 bg-slate-200 dark:bg-slate-900/40 rounded-xl border border-slate-300 dark:border-slate-800/50 w-full sm:w-auto shadow-inner overflow-hidden group/label cursor-pointer" @click="handleEditLabel(port)">
                <!-- Left Side: Custom Label (if exists) -->
                <div v-if="port.custom_label" class="flex-1 px-4 py-3 border-r border-slate-300 dark:border-slate-700 bg-blue-500/5 dark:bg-blue-500/10 flex items-center justify-between group-hover/label:bg-blue-500/10 transition-colors">
                  <span class="text-sm font-black text-blue-700 dark:text-blue-400 truncate">{{ port.custom_label }}</span>
                  <Edit2 :size="12" class="text-blue-400 opacity-0 group-hover/label:opacity-100" />
                </div>
                <!-- Right Side: Process Name -->
                <div class="flex-1 px-4 py-3 flex items-center gap-3 min-w-0">
                  <TerminalIcon :size="18" class="text-slate-700 dark:text-slate-500 shrink-0" />
                  <span class="text-sm font-bold font-mono truncate" :title="port.process_name || '系统进程'">{{ port.process_name || '系统进程' }}</span>
                  <Plus v-if="!port.custom_label" :size="12" class="text-slate-500 opacity-0 group-hover/label:opacity-100 ml-auto" />
                </div>
              </div>

              <div class="flex items-center gap-4 md:w-1/4 justify-end">
                <button @click="handleManagePort(port)" class="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-blue-600 hover:text-white transition-all text-slate-400">
                  <Settings :size="18" />
                </button>
                <component :is="port.is_managed ? Lock : Globe" :size="20" class="text-slate-700 dark:text-slate-500 hidden lg:block drop-shadow-sm" />
                
                <template v-if="port.is_container">
                  <button 
                    @click="handleRestart(port)"
                    class="flex items-center gap-2 px-5 py-2.5 bg-slate-800 dark:bg-slate-800 hover:bg-slate-900 dark:hover:bg-slate-700 text-white rounded-xl text-xs font-black transition-colors shrink-0 shadow-md"
                  >
                    <Container :size="16" />
                    <span class="hidden sm:inline">重启容器</span>
                    <span class="sm:hidden">重启</span>
                  </button>
                </template>
                
                <template v-else-if="port.is_managed">
                  <button 
                    @click="handleRestart(port)"
                    class="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-black transition-colors shrink-0 shadow-md"
                  >
                    <RotateCcw :size="16" />
                    <span class="hidden sm:inline">重启进程</span>
                    <span class="sm:hidden">重启</span>
                  </button>
                </template>
              </div>
            </div>
          </template>
        </div>
      </template>

      <!-- Empty State -->
      <div v-if="portStore.ports.length === 0" class="col-span-full py-40 flex flex-col items-center justify-center space-y-6">
        <div class="p-10 bg-slate-100 dark:bg-slate-900/40 rounded-[2.5rem] border-4 border-dashed border-slate-200 dark:border-slate-800">
          <Activity :size="64" class="opacity-20 dark:opacity-5 text-slate-500" />
        </div>
        <div class="text-center space-y-2">
          <p class="text-xl font-black text-slate-400 dark:text-slate-600 tracking-[0.2em]">监控未生效</p>
          <p class="text-sm text-slate-500 dark:text-slate-700 font-medium">未能捕获到任何系统端口，请检查后端服务权限</p>
        </div>
      </div>
    </div>

    <!-- Manage Port Dialog -->
    <el-dialog v-model="showManageDialog" title="端口管理设置" :width="width < 768 ? '95%' : '500px'" class="custom-dialog" align-center append-to-body>
      <div class="p-2 space-y-6">
        <div class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/50 p-4 rounded-2xl border border-slate-200 dark:border-slate-700/50">
          <div class="space-y-1">
            <p class="text-sm font-black text-slate-900 dark:text-white">开启托管模式</p>
            <p class="text-xs text-slate-500">启用后将允许手动重启该端口的服务</p>
          </div>
          <el-switch v-model="manageForm.is_monitored" inline-prompt active-text="ON" inactive-text="OFF" />
        </div>

        <el-form-item label="关联恢复/重启任务" label-position="top">
          <el-select v-model="manageForm.recovery_task_id" placeholder="选择在调度中心定义的任务" class="custom-select w-full" clearable>
            <el-option
              v-for="task in taskStore.tasks"
              :key="task.id"
              :label="task.name"
              :value="task.id"
            />
            <template #prefix><RotateCcw class="w-4 h-4 text-slate-400" /></template>
          </el-select>
          <p class="text-[10px] text-slate-500 mt-2">点击“重启进程”时，系统将自动触发运行此任务脚本。</p>
        </el-form-item>
      </div>
      <template #footer>
        <div class="flex gap-3 px-2 pb-2">
          <button @click="showManageDialog = false" class="flex-1 px-4 py-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold">取消</button>
          <button @click="saveManageSettings" class="flex-[2] px-4 py-3 rounded-xl bg-blue-600 text-white font-black shadow-lg shadow-blue-600/20">保存配置</button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* Scoped overrides if needed */
</style>
