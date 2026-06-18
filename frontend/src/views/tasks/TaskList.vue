<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
import { useTaskStore, type Task } from '../../store/task'
import { useEnvStore } from '../../store/env'
import { Play, ToggleLeft, ToggleRight, Terminal as TerminalIcon, Plus, Clock, FileCode, Search, Edit2, FileText } from '@lucide/vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

const taskStore = useTaskStore()
const envStore = useEnvStore()
const showLogs = ref(false)
const showCreateDialog = ref(false)
const editingTaskId = ref<number | null>(null)
const selectedTaskLogs = ref<any[]>([])
const selectedTaskIdForLogs = ref<number | null>(null)
const logContainerRef = ref<HTMLElement>()
let logRefreshTimer: number | null = null

const taskFormRef = ref<FormInstance>()
const searchQuery = ref('')

const newTask = reactive({
  name: '',
  script_path: '',
  python_interpreter: '',
  cron_expression: '*/5 * * * *',
  is_active: true,
  environment_params_str: ''
})

const rules = reactive<FormRules>({
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  script_path: [{ required: true, message: '请输入脚本绝对路径', trigger: 'blur' }],
  cron_expression: [{ required: true, message: '请输入 Cron 表达式', trigger: 'blur' }]
})

onMounted(() => {
  taskStore.fetchTasks()
  envStore.fetchEnvs()
})

const openCreateDialog = () => {
  editingTaskId.value = null
  newTask.name = ''
  newTask.script_path = ''
  newTask.python_interpreter = ''
  newTask.cron_expression = '*/5 * * * *'
  newTask.is_active = true
  newTask.environment_params_str = ''
  showCreateDialog.value = true
}

const openEditDialog = (task: Task) => {
  editingTaskId.value = task.id
  newTask.name = task.name
  newTask.script_path = task.script_path
  // 如果路径匹配某个预设环境，则选中该环境名称，否则置空
  const matchedEnv = envStore.envs.find(e => e.interpreter_path === task.python_interpreter)
  newTask.python_interpreter = matchedEnv ? matchedEnv.name : ''
  newTask.cron_expression = task.cron_expression
  newTask.is_active = task.is_active
  newTask.environment_params_str = task.environment_params ? JSON.stringify(task.environment_params, null, 2) : ''
  showCreateDialog.value = true
}

const handleRun = async (task: Task) => {
  try {
    await taskStore.runTaskNow(task.id)
    ElMessage({
      message: `任务 [${task.name}] 已手动触发`,
      type: 'success',
      plain: true,
    })
  } catch (err) {
    ElMessage.error('触发失败')
  }
}

const handleToggle = async (task: Task) => {
  try {
    await taskStore.toggleTask(task.id)
    ElMessage({
      message: `任务状态已切换`,
      type: 'info',
      plain: true,
    })
  } catch (err) {
    ElMessage.error('切换失败')
  }
}

const viewLogs = async (task: Task) => {
  selectedTaskIdForLogs.value = task.id
  showLogs.value = true
  await fetchLogsData()
}

const fetchLogsData = async () => {
  if (!selectedTaskIdForLogs.value) return
  try {
    selectedTaskLogs.value = await taskStore.fetchLogs(selectedTaskIdForLogs.value)
  } catch (err) {
    console.error('获取日志失败', err)
  }
}

const closeLogs = () => {
  showLogs.value = false
  selectedTaskIdForLogs.value = null
}

const showFullLogDialog = ref(false)
const fullLogContent = ref('')
const currentLogFilename = ref('')
const currentLogTime = ref('')

const getFileName = (path: string | undefined) => {
  if (!path) return '未知文件'
  return path.split('/').pop() || '未知文件'
}

const viewFullLog = async (log: any) => {
  try {
    currentLogFilename.value = getFileName(log.log_file_path)
    currentLogTime.value = new Date(log.start_time).toLocaleString()
    fullLogContent.value = await taskStore.fetchLogContent(log.id)
    showFullLogDialog.value = true
  } catch (err) {
    ElMessage.error('无法读取日志文件')
  }
}

const submitTask = async () => {
  if (!taskFormRef.value) return
  await taskFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        let parsedParams = null
        if (newTask.environment_params_str.trim()) {
          try {
            parsedParams = JSON.parse(newTask.environment_params_str)
          } catch (e) {
            ElMessage.error('环境变量 JSON 格式错误')
            return
          }
        }

        // 将环境别名映射回真实的解释器路径
        const selectedEnv = envStore.envs.find(e => e.name === newTask.python_interpreter)
        const finalPath = selectedEnv ? selectedEnv.interpreter_path : null

        const payload = {
          name: newTask.name,
          script_path: newTask.script_path,
          python_interpreter: finalPath,
          cron_expression: newTask.cron_expression,
          is_active: newTask.is_active,
          environment_params: parsedParams
        }

        if (editingTaskId.value) {
          await taskStore.updateTask(editingTaskId.value, payload)
          ElMessage.success('任务配置已保存')
        } else {
          await taskStore.createTask(payload)
          ElMessage.success('任务创建成功')
        }
        showCreateDialog.value = false
      } catch (err: any) {
        console.error('Submission Error:', err)
        const errorDetail = err.response?.data?.detail
        const msg = Array.isArray(errorDetail) ? errorDetail[0].msg : (errorDetail || '网络请求失败')
        ElMessage.error(`${editingTaskId.value ? '保存' : '创建'}失败: ${msg}`)
      }
    }
  })
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-8">
    <!-- Header Area -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div class="space-y-1">
        <h2 class="text-4xl font-black text-slate-900 dark:text-white tracking-tight">调度中心</h2>
        <p class="text-slate-500 font-medium">管理您的定时任务与自动化脚本</p>
      </div>
      
      <div class="flex items-center gap-4">
        <div class="relative group">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-slate-500 w-4 h-4 group-focus-within:text-blue-500 transition-colors" />
          <input 
            v-model="searchQuery"
            type="text" 
            placeholder="搜索任务..." 
            class="bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 rounded-xl py-2.5 pl-10 pr-4 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all w-64 shadow-sm dark:shadow-none"
          />
        </div>
        <button 
          @click="showCreateDialog = true"
          class="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-blue-600/20 transition-all active:scale-95"
        >
          <Plus :size="18" />
          新建任务
        </button>
      </div>
    </div>

    <!-- Task Cards Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div v-for="task in taskStore.tasks" :key="task.id" 
        class="bg-white/80 dark:bg-[#1e293b]/40 backdrop-blur-sm border border-slate-200 dark:border-slate-800 rounded-3xl p-8 hover:border-slate-300 dark:hover:border-slate-600 hover:bg-white dark:hover:bg-[#1e293b]/60 transition-all duration-300 group shadow-sm dark:shadow-none"
      >
        <div class="flex justify-between items-start mb-6">
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <h3 class="text-xl font-bold text-slate-900 dark:text-white tracking-tight">{{ task.name }}</h3>
              <div :class="[
                'px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider',
                task.is_active ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-500 border border-emerald-200 dark:border-emerald-500/20' : 'bg-rose-100 dark:bg-rose-500/10 text-rose-600 dark:text-rose-500 border border-rose-200 dark:border-rose-500/20'
              ]">
                {{ task.is_active ? '运行中' : '已暂停' }}
              </div>
            </div>
            
            <div class="flex flex-wrap gap-4 text-xs font-medium text-slate-500">
              <div class="flex items-center gap-1.5">
                <FileCode :size="14" class="text-blue-500" />
                <span class="font-mono text-slate-600 dark:text-slate-400">{{ task.script_path }}</span>
              </div>
              <div class="flex items-center gap-1.5">
                <Clock :size="14" class="text-purple-500" />
                <span class="font-mono text-purple-600 dark:text-purple-400">{{ task.cron_expression }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center bg-slate-50 dark:bg-slate-900/50 p-1.5 rounded-2xl border border-slate-200 dark:border-slate-800 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <button @click="handleRun(task)" class="p-2.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl text-emerald-500 dark:text-emerald-400 transition-colors" title="立即运行">
              <Play :size="18" fill="currentColor" />
            </button>
            <button @click="openEditDialog(task)" class="p-2.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl text-amber-500 dark:text-amber-400 transition-colors" title="编辑任务">
              <Edit2 :size="18" />
            </button>
            <button @click="handleToggle(task)" class="p-2.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl text-blue-500 dark:text-blue-400 transition-colors" :title="task.is_active ? '暂停' : '启动'">
              <component :is="task.is_active ? ToggleRight : ToggleLeft" :size="20" />
            </button>
            <button @click="viewLogs(task)" class="p-2.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl text-slate-500 dark:text-slate-400 transition-colors" title="查看日志">
              <TerminalIcon :size="18" />
            </button>
          </div>
        </div>

        <div class="flex items-center justify-between text-[11px] font-bold tracking-wider text-slate-500 dark:text-slate-600 mt-2">
          <span>上次成功: 2分钟前</span>
          <span v-if="task.config_hash" class="font-mono lowercase text-[9px] opacity-40 dark:opacity-30">哈希校验: {{ task.config_hash.substring(0,8) }}</span>
        </div>
      </div>
      
      <div v-if="taskStore.tasks.length === 0" class="col-span-full py-32 bg-slate-50 dark:bg-slate-900/20 rounded-[2rem] border-2 border-dashed border-slate-300 dark:border-slate-800 flex flex-col items-center justify-center text-slate-500 dark:text-slate-600 space-y-4">
        <div class="p-4 bg-slate-100 dark:bg-slate-800/50 rounded-full">
          <TerminalIcon :size="48" class="opacity-20" />
        </div>
        <p class="font-bold tracking-tight">暂无任何调度任务</p>
        <button @click="showCreateDialog = true" class="text-blue-500 hover:text-blue-400 font-bold text-sm">立即创建第一个任务</button>
      </div>
    </div>

    <!-- Create Task Dialog -->
    <el-dialog 
      v-model="showCreateDialog" 
      :title="editingTaskId ? '编辑任务配置' : '配置新任务'" 
      width="800px" 
      class="custom-dialog"
      :show-close="false"
      align-center
    >
      <div class="p-2">
        <el-form :model="newTask" :rules="rules" ref="taskFormRef" label-position="top">
          <div class="grid grid-cols-1 gap-4">
            <el-form-item label="任务标识" prop="name">
              <el-input v-model="newTask.name" placeholder="例如：每日备份脚本" class="custom-input" />
            </el-form-item>
            
            <el-form-item label="脚本资源" prop="script_path">
              <el-input v-model="newTask.script_path" placeholder="/绝对路径/至/脚本.py" class="custom-input">
                <template #prefix><FileCode class="w-4 h-4 text-slate-400 dark:text-slate-500" /></template>
              </el-input>
            </el-form-item>

            <el-form-item label="运行环境 (Python)">
              <el-select v-model="newTask.python_interpreter" placeholder="请选择预设环境" class="custom-select w-full">
                <el-option
                  v-for="env in envStore.envs"
                  :key="env.id"
                  :label="env.name"
                  :value="env.name"
                >
                  <div class="flex justify-between items-center w-full">
                    <span class="font-bold">{{ env.name }}</span>
                    <span class="text-[10px] text-slate-400 font-mono">{{ env.interpreter_path }}</span>
                  </div>
                </el-option>
                <template #prefix><TerminalIcon class="w-4 h-4 text-slate-400 dark:text-slate-500" /></template>
              </el-select>
              <p class="text-[10px] text-slate-500 mt-1">下拉框展示“环境配置”页面定义的别名</p>
            </el-form-item>

            <div class="grid grid-cols-2 gap-4">
              <el-form-item label="执行周期 (Cron)" prop="cron_expression">
                <el-input v-model="newTask.cron_expression" placeholder="*/5 * * * *" class="custom-input" />
              </el-form-item>
              <el-form-item label="初始化状态">
                <div class="flex items-center gap-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl px-4 py-1.5 border border-slate-200 dark:border-slate-700/50">
                  <span class="text-xs font-bold text-slate-500 dark:text-slate-400">立即启用</span>
                  <el-switch v-model="newTask.is_active" inline-prompt active-text="开" inactive-text="关" />
                </div>
              </el-form-item>
            </div>

            <el-form-item label="环境变量 (JSON格式，可选)">
              <el-input 
                v-model="newTask.environment_params_str" 
                type="textarea" 
                :rows="3" 
                placeholder='{"ENV_VAR_1": "value", "DEBUG": "true"}'
                class="custom-input font-mono" 
              />
            </el-form-item>
          </div>
        </el-form>
      </div>
      
      <template #footer>
        <div class="flex gap-3 px-2 pb-2">
          <button 
            @click="showCreateDialog = false" 
            class="flex-1 px-4 py-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 font-bold transition-colors"
          >
            取消
          </button>
          <button 
            @click="submitTask" 
            :disabled="taskStore.isLoading"
            class="flex-[2] px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-black shadow-lg shadow-blue-600/20 transition-all active:scale-[0.98]"
          >
            {{ taskStore.isLoading ? '正在提交...' : '确认部署任务' }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- Logs Drawer -->
    <el-drawer 
      v-model="showLogs" 
      size="50%" 
      class="log-drawer"
      :with-header="false"
      @close="closeLogs"
    >
      <div class="h-full flex flex-col bg-slate-50 dark:bg-[#020617]">
        <div class="p-8 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center bg-white/80 dark:bg-[#0f172a]/80 backdrop-blur-md sticky top-0 z-10">
          <div class="flex items-center gap-3">
            <div class="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg">
              <TerminalIcon class="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 class="text-xl font-black text-slate-900 dark:text-white">执行历史</h3>
          </div>
          <button @click="closeLogs" class="text-slate-500 hover:text-slate-900 dark:hover:text-white font-black text-sm uppercase tracking-widest">关闭</button>
        </div>

        <div class="flex-1 overflow-auto p-8 space-y-6 scroll-smooth" ref="logContainerRef">
          <div v-for="log in selectedTaskLogs" :key="log.id" class="group space-y-3">
            <div class="flex justify-between items-end">
              <div class="flex items-center gap-3">
                <div :class="[
                  'w-2 h-2 rounded-full',
                  log.status === 'success' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 
                  log.status === 'running' ? 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)] animate-pulse' :
                  'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.4)]'
                ]"></div>
                <span class="text-sm font-bold text-slate-700 dark:text-slate-300">{{ new Date(log.start_time).toLocaleString() }}</span>
              </div>
              <span class="text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300 transition-colors">
                <template v-if="log.status === 'running'">
                  <span class="text-blue-500 dark:text-blue-400">执行中...</span>
                </template>
                <template v-else>
                  退出码 {{ log.exit_code !== null ? log.exit_code : 'N/A' }} • 
                  <span :class="log.status === 'success' ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600 dark:text-rose-500'">
                    {{ log.status === 'success' ? '成功' : '失败' }}
                  </span>
                </template>
              </span>
            </div>
            
            <div class="relative group/log flex flex-col gap-3 bg-slate-100 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-800 rounded-2xl p-6">
              <div v-if="log.stdout || log.stderr" class="space-y-2">
                <p class="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">日志预览 (前三行)</p>
                <pre class="text-xs font-mono text-slate-600 dark:text-slate-400 opacity-80">{{ log.stdout }}</pre>
                <pre v-if="log.stderr" class="text-xs font-mono text-rose-500 opacity-80">{{ log.stderr }}</pre>
              </div>
              <div class="flex items-center justify-end pt-2 border-t border-slate-200 dark:border-slate-800/50">
                <button @click="viewFullLog(log)" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all active:scale-95 shadow-lg shadow-blue-600/20">
                  查看完整日志
                </button>
              </div>
            </div>
          </div>
          
          <div v-if="selectedTaskLogs.length === 0" class="h-full flex flex-col items-center justify-center py-40 text-slate-400 dark:text-slate-600 space-y-4">
            <TerminalIcon :size="64" class="opacity-20 dark:opacity-10" />
            <p class="font-bold uppercase tracking-widest text-xs opacity-50 dark:opacity-30">暂无执行记录</p>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- Full Log Dialog -->
    <el-dialog 
      v-model="showFullLogDialog" 
      width="85%" 
      class="custom-dialog full-log-dialog"
      align-center
      append-to-body
    >
      <template #header>
        <div class="flex items-center gap-4">
          <div class="p-3 bg-blue-600/10 rounded-2xl border border-blue-500/20">
            <FileText class="w-6 h-6 text-blue-500" />
          </div>
          <div class="flex flex-col">
            <h3 class="text-xl font-black text-slate-900 dark:text-white tracking-tight">完整运行日志</h3>
            <div class="flex items-center gap-3 mt-1">
              <span class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-700">文件名: {{ currentLogFilename }}</span>
              <span class="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-700">执行时间: {{ currentLogTime }}</span>
            </div>
          </div>
        </div>
      </template>
      <div class="px-6 pb-6 pt-2">
        <pre class="bg-slate-950 text-slate-300 p-6 rounded-2xl overflow-auto max-h-[70vh] font-mono text-sm leading-relaxed custom-scroll border border-slate-800 shadow-2xl">{{ fullLogContent || '日志文件为空或不存在' }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<style>
@reference "../../style.css";

/* Scoped overrides */
.custom-dialog {
  @apply rounded-[2rem] bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800;
}
.custom-dialog .el-dialog__header {
  @apply border-b border-slate-100 dark:border-slate-800 p-8 m-0;
}
.custom-dialog .el-dialog__title {
  @apply text-xl font-black text-slate-900 dark:text-white tracking-tight;
}
.custom-dialog .el-dialog__body {
  @apply p-8;
}
.full-log-dialog .el-dialog__body {
  @apply p-0 px-8 pb-8;
}
.custom-dialog .el-dialog__footer {
  @apply p-6 border-t border-slate-100 dark:border-slate-800;
}

.custom-input .el-input__wrapper, .custom-select .el-select__wrapper {
  @apply bg-slate-50 dark:bg-slate-800/50 shadow-none border-slate-200 dark:border-slate-700/50 rounded-xl px-4 py-2 transition-all;
}
.custom-input .el-input__wrapper.is-focus, .custom-select .el-select__wrapper.is-focus {
  @apply ring-2 ring-blue-500/20 border-blue-500;
}

.log-drawer {
  @apply bg-white dark:bg-slate-950;
}

.custom-scroll::-webkit-scrollbar {
  width: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  @apply bg-slate-300 dark:bg-slate-800 rounded-full;
}
</style>
