import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    target: 'es2020',
    minify: 'oxc',
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/recharts')) return 'recharts'
          if (id.includes('node_modules/@clerk')) return 'clerk'
          if (id.includes('node_modules/@sentry')) return 'sentry'
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) return 'vendor'
        },
      },
    },
  },
})
