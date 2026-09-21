import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  // The backend is the only source of data. There is no second implementation
  // of the pipeline in the browser this time: v1 had one and the two drifted.
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
