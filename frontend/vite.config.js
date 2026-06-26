import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    open: true,
    // Allow ngrok and any other tunnel/host to reach this dev server
    allowedHosts: true,
    // Proxy all /api/* requests to the FastAPI backend.
    // This means only ONE ngrok tunnel (port 3000) is needed —
    // teammates' browsers call /api/chat and Vite forwards it
    // server-side to localhost:8000.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

