// playwright.dev.config.ts
// Development mode config - points tests to Vite dev server with hot-reload
import { defineConfig } from '@playwright/test';
import baseConfig from './playwright.config';

/**
 * Development mode configuration for Playwright tests
 *
 * Usage:
 *   npx playwright test --config=playwright.dev.config.ts
 *   npx playwright test web/tests/[file].spec.ts --config=playwright.dev.config.ts --headed
 *
 * Prerequisites:
 *   1. Backend services running (mind_docker_compose_up.bat)
 *   2. Frontend dev server running (mind_frontend_dev.bat)
 *
 * This config:
 *   - Points baseURL to Vite dev server (localhost:5169)
 *   - Inherits all other settings from playwright.config.ts
 *   - Enables testing with hot-reload (no Docker rebuilds needed)
 */

export default defineConfig({
  ...baseConfig,

  use: {
    ...baseConfig.use,
    // Override baseURL to point to Vite dev server
    baseURL: 'http://localhost:5169',
  },
});
