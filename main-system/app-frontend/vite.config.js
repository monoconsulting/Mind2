import { defineConfig } from 'vite';
// Touch to restart server
import path from 'path';

// Proxy target: use env var for Docker, default to localhost for local dev
// - Local dev (mind_frontend_dev.bat): http://localhost:8008 (nginx proxy)
// - Docker dev: http://ai-api:5000 (direct to backend service)
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8008';

const apiProxy = {
  '/ai/api': {
    target: apiProxyTarget,
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/ai\/api/, ''), // Strip /ai/api prefix like nginx does
  },
};

const workspaceRoot = path.resolve(__dirname, '..', '..');

export default defineConfig({
  server: {
    host: '0.0.0.0', // Accept connections from outside (required for Docker)
    port: 5169,
    strictPort: true,
    fs: {
      strict: false,
      allow: [workspaceRoot],
    },
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    strictPort: true,
    fs: {
      strict: false,
      allow: [workspaceRoot],
    },
    proxy: apiProxy,
  },
});
