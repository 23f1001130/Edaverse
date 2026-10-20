import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    ssr: 'src/prerender.jsx',
    outDir: '.prerender',
    copyPublicDir: false,
    rollupOptions: { output: { entryFileNames: 'render.js' } },
  },
})
