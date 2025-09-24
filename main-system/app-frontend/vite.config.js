import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/ai/api': {
        target: 'http://localhost:8008',
        changeOrigin: true,
      },
    },
  },
});
