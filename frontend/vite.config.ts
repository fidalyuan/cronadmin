import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

// 从 .cronadmin_env 中读取配置的后端运行端口 (开发环境代理使用)
let backendPort = '8342'
try {
  const envPath = path.resolve(__dirname, '../.cronadmin_env')
  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8')
    const match = content.match(/export\s+CRONADMIN_PORT=["']?(\d+)["']?/)
    if (match) {
      backendPort = match[1]
    }
  }
} catch (e) {
  // 忽略读取错误
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      }
    }
  }
})
