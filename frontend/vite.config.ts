import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')

  // Validate required variables
  const requiredVars = ['VITE_MODE', 'VITE_APP_COUCHBASE_URL', 'VITE_APP_MAIN_LAKEHOUSE_API_URL']
  requiredVars.forEach((varName) => {
    if (!env[varName]) {
      console.warn(`⚠️ Missing required environment variable: ${varName}`)
    }
  })

  return {
    base: '/',
    plugins: [vue(), vueDevTools()],

    server: {
      host: true,
      port: 3000,
      // Proxy API requests in development
      proxy: {
        '/api/couchbase': {
          target: env.VITE_APP_COUCHBASE_URL,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/couchbase/, ''),
        },
        '/api/lakehouse': {
          target: env.VITE_APP_MAIN_LAKEHOUSE_API_URL,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/lakehouse/, ''),
        },
      },
    },

    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      emptyOutDir: true,
      rollupOptions: {
        output: {
          assetFileNames: 'assets/[name]-[hash][extname]',
          chunkFileNames: 'assets/[name]-[hash].js',
          entryFileNames: 'assets/[name]-[hash].js',
        },
      },
    },

    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },

    optimizeDeps: {
      include: [
        'primevue',
        'primevue/config',
        'primevue/toastservice',
        'primevue/dialogservice',
        'primevue/tooltip',
        '@primeuix/themes/aura',
      ],
    },
  }
})
