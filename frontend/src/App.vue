<script setup lang="ts">
import { RouterView, useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Terminal, Settings, ChevronRight, Activity, Sun, Moon, Box, LogOut } from '@lucide/vue'
import { useDark, useToggle } from '@vueuse/core'
import { useAuthStore } from './store/auth'

const isDark = useDark()
const toggleDark = useToggle(isDark)
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const handleLogout = () => {
  authStore.clearAuth()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-screen w-screen bg-slate-50 dark:bg-[#0f172a] text-slate-800 dark:text-slate-200 font-sans overflow-hidden transition-colors duration-300 relative">
    <!-- Demo Mode Dog-eared Ribbon -->
    <div v-if="route.path !== '/login' && authStore.systemMode === 'demo'" class="absolute top-0 left-0 w-16 h-16 pointer-events-none overflow-hidden z-50">
      <div class="absolute top-0 left-0 w-16 h-16 bg-gradient-to-br from-amber-500 via-orange-500 to-amber-600 shadow-md [clip-path:polygon(0_0,_100%_0,_0_100%)]"></div>
      <span class="absolute top-3 left-2.5 text-[9px] font-black text-white uppercase tracking-widest -rotate-45 select-none">Demo</span>
    </div>

    <!-- Sidebar (Hidden on Login Page) -->
    <aside v-if="route.path !== '/login'" class="w-64 bg-white dark:bg-[#1e293b] border-r border-slate-200 dark:border-slate-800 flex flex-col shadow-2xl z-10 transition-colors duration-300">
      <div class="p-8">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-900/20">
            <Activity class="text-white w-6 h-6" />
          </div>
          <div class="flex flex-col">
            <span class="text-xl font-black tracking-tight text-slate-900 dark:text-white">CronAdmin</span>
            <span class="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-500 font-bold">控制台</span>
          </div>
        </div>
      </div>
      
      <nav class="flex-1 px-4 space-y-1">
        <router-link 
          to="/tasks" 
          class="group flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 hover:bg-slate-100 dark:hover:bg-slate-700/50"
          active-class="bg-blue-50 dark:bg-blue-600/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-600/20"
        >
          <div class="flex items-center gap-3 font-medium">
            <LayoutDashboard :size="20" class="group-hover:scale-110 transition-transform" />
            任务调度
          </div>
          <ChevronRight :size="14" class="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
        </router-link>
        
        <router-link 
          to="/ports" 
          class="group flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 hover:bg-slate-100 dark:hover:bg-slate-700/50"
          active-class="bg-blue-50 dark:bg-blue-600/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-600/20"
        >
          <div class="flex items-center gap-3 font-medium">
            <Box :size="20" class="group-hover:scale-110 transition-transform" />
            端口状态
          </div>
          <ChevronRight :size="14" class="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
        </router-link>

        <router-link 
          to="/settings" 
          class="group flex items-center justify-between px-4 py-3 rounded-xl transition-all duration-200 hover:bg-slate-100 dark:hover:bg-slate-700/50"
          active-class="bg-blue-50 dark:bg-blue-600/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-600/20"
        >
          <div class="flex items-center gap-3 font-medium">
            <Settings :size="20" class="group-hover:scale-110 transition-transform" />
            环境配置
          </div>
          <ChevronRight :size="14" class="opacity-0 group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0 transition-all" />
        </router-link>
      </nav>
      
      <div class="p-6 mt-auto space-y-4">
        <button 
          @click="toggleDark()" 
          class="w-full flex items-center justify-center gap-2 p-3 rounded-xl bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors text-sm font-bold text-slate-600 dark:text-slate-400"
        >
          <component :is="isDark ? Sun : Moon" :size="16" />
          {{ isDark ? '切换浅色模式' : '切换深色模式' }}
        </button>

        <div class="flex items-stretch bg-slate-100 dark:bg-slate-800/50 rounded-2xl border border-slate-200 dark:border-slate-700/50 transition-colors duration-300 overflow-hidden">
          <div class="w-2/3 p-4 flex flex-col items-center justify-center border-r border-slate-200 dark:border-slate-700/50">
            <div class="flex items-center gap-2 mb-1">
              <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span class="text-xs font-bold text-slate-700 dark:text-slate-300">系统在线</span>
            </div>
            <p class="text-[10px] text-slate-500 font-medium uppercase tracking-tight truncate" title="Ubuntu 24.04">Ubuntu 24.04</p>
          </div>
          <button 
            @click="handleLogout" 
            class="w-1/3 shrink-0 flex items-center justify-center bg-rose-50 dark:bg-rose-500/10 hover:bg-rose-100 dark:hover:bg-rose-500/20 transition-colors text-rose-600 dark:text-rose-400 group"
            title="安全退出"
          >
            <LogOut :size="16" class="group-hover:scale-110 transition-transform" />
          </button>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-auto relative">
      <!-- Background decoration -->
      <div class="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-400/10 dark:bg-blue-600/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 pointer-events-none transition-colors duration-300"></div>
      <div class="absolute bottom-0 left-0 w-[300px] h-[300px] bg-indigo-400/10 dark:bg-indigo-600/5 blur-[100px] rounded-full translate-y-1/2 -translate-x-1/2 pointer-events-none transition-colors duration-300"></div>
      
      <div class="p-10 relative z-0">
        <RouterView />
      </div>
    </main>
  </div>
</template>
