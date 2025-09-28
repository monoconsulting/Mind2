// playwright.config.ts
import { defineConfig } from '@playwright/test';

/**
 * Output layout:
 *   web/test-results/
 *   ├─ html/                 ← HTML report (reporter.outputFolder)  [MÅSTE vara skild från outputDir]
 *   ├─ media/
 *   │  ├─ snapshots/         ← Visual snapshots (toHaveScreenshot / toMatchSnapshot)
 *   │  └─ video/             ← Recordings (recordVideo.dir)
 *   └─ _artifacts/           ← Per-test artefakter (outputDir): traces, fail-screenshots, etc.
 */

export default defineConfig({
  testDir: './web/tests',

  // Traces m.m. hamnar här (måste inte krocka med html-rapportens mapp)
  outputDir: 'web/test-results/_artifacts',

  reporter: [['html', { outputFolder: 'web/test-results/html', open: 'never' }], ['list']],

  // Visuella snapshots (namn och placering)
  snapshotPathTemplate: 'web/test-results/media/snapshots/{testName}{-arg}{ext}',
  expect: {
    toHaveScreenshot: {
      pathTemplate: 'web/test-results/media/snapshots/{testName}{-arg}{ext}',
      animations: 'disabled',
      caret: 'hide',
      scale: 'css',
    },
    toMatchAriaSnapshot: {
      pathTemplate: 'web/test-results/media/snapshots/{testName}{-arg}{ext}',
    },
  },

  use: {
    baseURL: 'http://localhost:8008',
    headless: false,

    // Ultrabred skärm – undvik scroll
    viewport: { width: 3440, height: 1440 },

    // Video: lagras där du vill ha dem
    video: 'on',
    recordVideo: {
      dir: 'web/test-results/media/video',
      size: { width: 3440, height: 1440 },
    },

    // Trace sparas per test i outputDir (ovan) – aktiverat för alla körningar
    trace: 'on',

    // Vanliga fel-screenshots går också till outputDir
    screenshot: 'on',

    // Se till att fönstret matchar viewport
    launchOptions: {
      args: ['--window-position=0,0', '--window-size=3440,1440'],
    },
  },

  projects: [
    {
      name: 'chromium-ultrawide',
      use: {
        viewport: { width: 3440, height: 1440 },
        launchOptions: {
          args: ['--window-position=0,0', '--window-size=3440,1440'],
        },
      },
    },
  ],
});
