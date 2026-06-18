<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useEnvStore, type RuntimeEnv } from '../../store/env'
import { Plus, Trash2, Terminal, Info, ShieldCheck } from '@lucide/vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const envStore = useEnvStore()
const showAddDialog = ref(false)

const newEnv = reactive({
  name: '',
  interpreter_path: '',
  description: ''
})

onMounted(() => {
  envStore.fetchEnvs()
})

const handleAdd = async () => {
  if (!newEnv.name || !newEnv.interpreter_path) {
    ElMessage.warning('名称和路径不能为空')
    return
  }
  try {
    await envStore.createEnv(newEnv)
    ElMessage.success('环境添加成功')
    showAddDialog.value = false
    newEnv.name = ''
    newEnv.interpreter_path = ''
    newEnv.description = ''
  } catch (err) {
    ElMessage.error('添加失败')
  }
}

const handleDelete = (env: RuntimeEnv) => {
  ElMessageBox.confirm(`确定要删除环境 [${env.name}] 吗？`, '警告', {
    type: 'warning',
    confirmButtonClass: 'bg-red-600 border-none'
  }).then(async () => {
    try {
      await envStore.deleteEnv(env.id)
      ElMessage.success('删除成功')
    } catch (err) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}
</script>

<template>
  <div class="max-w-7xl mx-auto space-y-10 pb-20">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-8">
      <div class="space-y-2">
        <h2 class="text-4xl font-black text-slate-900 dark:text-white tracking-tight">运行环境</h2>
        <p class="text-slate-500 font-medium">配置 Python 解释器别名，简化任务创建流程。</p>
      </div>
      <button 
        @click="showAddDialog = true"
        class="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-2xl font-black flex items-center gap-2 shadow-lg shadow-blue-600/20 transition-all active:scale-95"
      >
        <Plus :size="20" />
        添加运行环境
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      <div v-for="env in envStore.envs" :key="env.id" 
        class="bg-white dark:bg-[#1e293b]/30 backdrop-blur-sm border-2 border-slate-200 dark:border-slate-800 rounded-[2rem] p-8 space-y-6 hover:border-blue-500/30 transition-all shadow-sm"
      >
        <div class="flex justify-between items-start">
          <div class="flex items-center gap-3">
            <div class="p-3 bg-blue-600/10 rounded-2xl">
              <Terminal :size="24" class="text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 class="text-xl font-black text-slate-900 dark:text-white">{{ env.name }}</h3>
              <p class="text-xs font-bold text-slate-400 uppercase tracking-widest">{{ env.id === 1 ? '系统内置' : '自定义环境' }}</p>
            </div>
          </div>
          <button @click="handleDelete(env)" v-if="env.id !== 1" class="p-2 text-slate-400 hover:text-red-500 transition-colors">
            <Trash2 :size="18" />
          </button>
        </div>

        <div class="space-y-4">
          <div class="bg-slate-100 dark:bg-slate-900/40 rounded-2xl p-4 border border-slate-200 dark:border-slate-800/50 shadow-inner">
            <div class="flex items-center gap-3 text-slate-500">
              <Info :size="14" />
              <span class="text-xs font-mono break-all">{{ env.interpreter_path }}</span>
            </div>
          </div>
          <p v-if="env.description" class="text-sm text-slate-500 leading-relaxed">{{ env.description }}</p>
        </div>
      </div>
    </div>

    <el-dialog v-model="showAddDialog" title="添加新 Python 环境" width="500px" class="custom-dialog" align-center append-to-body>
      <el-form label-position="top" class="p-2 space-y-4">
        <el-form-item label="环境别名 (如: pytask, web-env)">
          <el-input v-model="newEnv.name" placeholder="请输入简短的名称" class="custom-input" />
        </el-form-item>
        <el-form-item label="解释器绝对路径">
          <el-input v-model="newEnv.interpreter_path" placeholder="/home/user/anaconda3/envs/myenv/bin/python" class="custom-input" />
        </el-form-item>
        <el-form-item label="描述 (可选)">
          <el-input v-model="newEnv.description" placeholder="简单说明该环境的用途" class="custom-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex gap-3 px-2 pb-2">
          <button @click="showAddDialog = false" class="flex-1 px-4 py-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold">取消</button>
          <button @click="handleAdd" class="flex-[2] px-4 py-3 rounded-xl bg-blue-600 text-white font-black">确认保存</button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
