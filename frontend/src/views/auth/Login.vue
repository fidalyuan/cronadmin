<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Terminal, Lock, User, LogIn, Activity } from '@lucide/vue'
import { ElMessage } from 'element-plus'
import CryptoJS from 'crypto-js'
import apiClient from '../../api/client'
import { useAuthStore } from '../../store/auth'

const router = useRouter()
const authStore = useAuthStore()

const loginForm = reactive({
  username: '',
  password: ''
})
const isLoading = ref(false)

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  isLoading.value = true
  try {
    // 密码 SHA-256 前端加密防明文传输
    const passwordHash = CryptoJS.SHA256(loginForm.password).toString()
    
    // 使用 URLSearchParams 以 application/x-www-form-urlencoded 格式发送，这是 OAuth2PasswordRequestForm 的要求
    const params = new URLSearchParams()
    params.append('username', loginForm.username)
    params.append('password', passwordHash)

    const response = await apiClient.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    })
    
    const token = response.data.access_token
    authStore.setAuth(token, loginForm.username)
    
    ElMessage.success('登录成功')
    router.push('/')
  } catch (err: any) {
    const msg = err.response?.data?.detail || '登录失败，请检查网络或后端服务'
    ElMessage.error(msg)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen w-screen bg-gradient-to-tr from-blue-100 via-indigo-50 to-sky-100 dark:from-[#0b1e36] dark:via-[#070e1b] dark:to-[#020617] flex items-center justify-center p-4 transition-colors duration-300 relative overflow-hidden">
    <!-- Background Decor -->
    <div class="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-400/10 dark:bg-blue-600/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
    <div class="absolute bottom-0 left-0 w-[300px] h-[300px] bg-indigo-400/10 dark:bg-indigo-600/5 blur-[100px] rounded-full translate-y-1/2 -translate-x-1/2 pointer-events-none"></div>

    <div class="w-full max-w-md bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-slate-800 rounded-3xl md:rounded-[2.5rem] shadow-2xl overflow-hidden relative z-10">
      <div class="p-6 md:p-10 space-y-8">
        <div class="text-center space-y-4">
          <div class="inline-flex p-4 bg-blue-600/10 rounded-3xl shadow-lg shadow-blue-500/10 border border-blue-500/20 mb-2">
            <Terminal class="w-10 h-10 text-blue-600 dark:text-blue-500" />
          </div>
          <h2 class="text-3xl font-black text-slate-900 dark:text-white tracking-tight">CronAdmin</h2>
          <p class="text-sm font-bold text-slate-500 uppercase tracking-[0.2em]">系统身份认证</p>
        </div>

        <form @submit.prevent="handleLogin" class="space-y-6 mt-10">
          <div class="space-y-4">
            <div class="relative group">
              <User class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="loginForm.username"
                type="text" 
                placeholder="用户名 (默认: admin)" 
                class="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-2xl py-4 pl-12 pr-4 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-medium placeholder:font-normal"
                autocomplete="username"
              />
            </div>
            
            <div class="relative group">
              <Lock class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5 group-focus-within:text-blue-500 transition-colors" />
              <input 
                v-model="loginForm.password"
                type="password" 
                placeholder="密码 (默认: admin123)" 
                class="w-full bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-2xl py-4 pl-12 pr-4 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-medium placeholder:font-normal"
                autocomplete="current-password"
              />
            </div>
          </div>

          <button 
            type="submit" 
            :disabled="isLoading"
            class="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-70 disabled:hover:bg-blue-600 text-white py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-2 shadow-xl shadow-blue-600/20 transition-all active:scale-[0.98]"
          >
            <LogIn v-if="!isLoading" :size="20" />
            <Activity v-else class="animate-spin" :size="20" />
            {{ isLoading ? '验证中...' : '安全登录' }}
          </button>
        </form>
        
        <div class="text-center text-xs text-slate-500 font-medium">
          &copy; 2026 CronAdmin. All rights reserved.
        </div>
      </div>
    </div>
  </div>
</template>
