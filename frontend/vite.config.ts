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

// CDN plugin that injects the importmap and stylesheets only during build/production
const cdnPlugin = () => {
  let isBuild = false
  return {
    name: 'vite-plugin-cdn-importmap',
    configResolved(config: any) {
      isBuild = config.command === 'build'
    },
    transformIndexHtml(html: string) {
      if (!isBuild) {
        return html
      }
      
      const importMap = `
    <!-- Import map for ESM CDN dependencies -->
    <script type="importmap">
    {
      "imports": {
        "vue": "https://cdn.jsdelivr.net/npm/vue@3.5.34/dist/vue.esm-browser.prod.js",
        "vue-router": "https://cdn.jsdelivr.net/npm/vue-router@5.1.0/dist/vue-router.esm-browser.prod.js",
        "vue-demi": "https://cdn.jsdelivr.net/npm/vue-demi@0.14.6/lib/index.mjs",
        "@vue/devtools-api": "https://cdn.jsdelivr.net/npm/@vue/devtools-api@6.6.1/lib/esm/index.js",
        "pinia": "https://cdn.jsdelivr.net/npm/pinia@3.0.4/dist/pinia.esm-browser.js",
        "axios": "https://cdn.jsdelivr.net/npm/axios@1.17.0/dist/esm/axios.js",
        "element-plus": "https://cdn.jsdelivr.net/npm/element-plus@2.14.1/dist/index.full.min.mjs"
      }
    }
    </script>
      `
      // Insert in the head block
      return html.replace('</head>', `${importMap}\n</head>`)
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), cdnPlugin()],
  server: {
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${backendPort}`,
        changeOrigin: true,
      }
    }
  },
  build: {
    rollupOptions: {
      external: ['vue', 'vue-router', 'pinia', 'axios', 'element-plus']
    }
  }
})
