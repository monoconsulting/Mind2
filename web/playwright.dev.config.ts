// playwright.dev.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: 'test-results/_artifacts',
  reporter: [['html', { outputFolder: 'test-results/html', open: 'never' }], ['list']],

  use: {
    baseURL: 'http://localhost:5169',
    headless: false,
    viewport: { width: 2560, height: 1440 },
    video: 'on',
    recordVideo: {
      dir: 'test-results/media/video',
      size: { width: 2560, height: 1440 },
    },
    trace: 'on',
    screenshot: 'on',
    launchOptions: {
      args: ['--window-position=0,0', '--window-size=2560,1440'],
    },
  },
});
