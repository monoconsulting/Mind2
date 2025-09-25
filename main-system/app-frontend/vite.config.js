import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5169,
    strictPort: true,
    proxy: {
      '/ai/api': {
        target: 'http://localhost:8008',
        changeOrigin: true,
      },
    },
  },
});
