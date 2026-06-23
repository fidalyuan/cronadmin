import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

// 从 .cronadmin_env 中读取配置 of 后端运行端口 (开发环境代理使用)
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

// CDN plugin that injects the importmap and stylesheets only during build/production when USE_CDN is true
const cdnPlugin = (useCdn: boolean) => {
  return {
    name: 'vite-plugin-cdn-importmap',
    transformIndexHtml(html: string) {
      if (!useCdn) {
        return html
      }
      
      const importMap = `
    <!-- Import map for ESM CDN dependencies -->
    <script type="importmap">
    {
      "imports": {
        "vue": "https://unpkg.com/vue@3.5.34/dist/vue.esm-browser.prod.js",
        "vue-router": "https://unpkg.com/vue-router@5.1.0/dist/vue-router.esm-browser.prod.js",
        "vue-demi": "https://unpkg.com/vue-demi@0.14.6/lib/index.mjs",
        "@vue/devtools-api": "https://unpkg.com/@vue/devtools-api@6.6.1/lib/esm/index.js",
        "pinia": "https://unpkg.com/pinia@3.0.4/dist/pinia.esm-browser.js",
        "axios": "https://unpkg.com/axios@1.17.0/dist/esm/axios.js",
        "element-plus": "https://unpkg.com/element-plus@2.14.1/dist/index.full.min.mjs"
      }
    }
    </script>
    <link rel="stylesheet" href="https://unpkg.com/element-plus@2.14.1/dist/index.css" />
    <link rel="stylesheet" href="https://unpkg.com/element-plus@2.14.1/theme-chalk/dark/css-vars.css" />
      `
      // Insert in the head block
      return html.replace('</head>', `${importMap}\n</head>`)
    }
  }
}

// Virtual CSS plugin to conditionally import Element Plus CSS files locally when USE_CDN is false
const virtualCssPlugin = (useCdn: boolean) => {
  const virtualModuleId = 'virtual:element-plus-theme'
  const resolvedVirtualModuleId = '\0' + virtualModuleId

  return {
    name: 'vite-plugin-virtual-css',
    resolveId(id: string) {
      if (id === virtualModuleId) {
        return resolvedVirtualModuleId
      }
    },
    load(id: string) {
      if (id === resolvedVirtualModuleId) {
        if (useCdn) {
          return ''
        } else {
          return `
            import 'element-plus/dist/index.css';
            import 'element-plus/theme-chalk/dark/css-vars.css';
          `
        }
      }
    }
  }
}

// https://vite.dev/config/
export default defineConfig(() => {
  const useCdn = process.env.USE_CDN === 'true'

  return {
    plugins: [
      vue(),
      cdnPlugin(useCdn),
      virtualCssPlugin(useCdn)
    ],
    server: {
      proxy: {
        '/api': {
          target: `http://127.0.0.1:${backendPort}`,
          changeOrigin: true,
        }
      }
    },
    build: {
      emptyOutDir: true,
      rollupOptions: {
        external: useCdn ? ['vue', 'vue-router', 'pinia', 'axios', 'element-plus'] : [],
        onwarn(warning: any, defaultHandler: any) {
          if (warning.code === 'INVALID_ANNOTATION') {
            return
          }
          defaultHandler(warning)
        }
      }
    }
  }
})
