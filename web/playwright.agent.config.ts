import { defineConfig } from '@playwright/test';

const authFile = 'test-reports/.auth/admin.json';

export default defineConfig({
  testDir: './tests',
  outputDir: 'test-reports/_artifacts',
  reporter: [['html', { outputFolder: 'test-reports/html', open: 'never' }], ['list']],
  snapshotPathTemplate: 'test-reports/media/snapshots/{testName}{-arg}{ext}',
  expect: {
    toHaveScreenshot: {
      pathTemplate: 'test-reports/media/snapshots/{testName}{-arg}{ext}',
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    },
  },
  use: {
    baseURL: 'http://localhost:8008',
    headless: true,
    viewport: { width: 1900, height: 1200 },
    video: 'on',
    recordVideo: {
      dir: 'test-reports/media/video',
      size: { width: 1900, height: 120 },
    },
    trace: 'on',
    screenshot: 'on',
  },
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },
    {
      name: 'chromium-headless',
      dependencies: ['setup'],
      use: {
        storageState: authFile,
      },
    },
  ],
});
