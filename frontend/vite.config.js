import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // In development the app calls /api/... on its own address, and Vite
    // forwards it to the FastAPI backend (dropping the /api prefix). To the
    // browser it's all one site, so there's no CORS to configure, whatever
    // port Vite ends up on.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
