import { defineConfig } from 'vite';

const apiProxy = {
  '/ai/api': {
    target: 'http://localhost:8008',
    changeOrigin: true,
  },
};

export default defineConfig({
  server: {
    port: 5169,
    strictPort: true,
    proxy: apiProxy,
  },
  preview: {
    port: 4173,
    strictPort: true,
    proxy: apiProxy,
  },
});
