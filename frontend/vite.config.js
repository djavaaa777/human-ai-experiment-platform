import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Same-origin requests in the browser; FastAPI remains unchanged.
const proxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
    rewrite: path => path.replace(/^\/api/, ''),
  },
  '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy },
  preview: { proxy },
});
