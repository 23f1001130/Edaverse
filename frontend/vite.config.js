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
    minify: 'esbuild',
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          recharts: ['recharts'],
          clerk: ['@clerk/clerk-react'],
          sentry: ['@sentry/react'],
          vendor: ['react', 'react-dom'],
        },
      },
    },
  },
})
