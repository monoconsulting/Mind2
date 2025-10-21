// receipt_image_modal_zoom_orientation.spec.ts
import { test, expect } from '@playwright/test';

/**
 * E2E: Login -> Navigate to "Process" -> Open first "Förhandsgranska kvitto"
 *
 * Notes:
 * - Uses baseURL from playwright.config.ts (so goto('/login') works).
 * - Waits for UI readiness before clicking navigation.
 * - Uses role-aware selectors that match Swedish labels.
 * - Avoids hardcoding a specific UUID in the "Förhandsgranska kvitto" button.
 */

// --------------------------------------------------------------------------------------
// The per-test viewport override below is redundant because viewport is already set
// globally in playwright.config.ts. Keeping it commented to avoid conflicting settings.
// Comment kept intentionally to document why it's not used.
// --------------------------------------------------------------------------------------
// test.use({
//   viewport: {
//     height: 1440,
//     width: 3440,
//   },
// });

// Enable trace for this test
test.use({
  trace: 'on',
});

test.beforeEach(async ({ page }) => {
  page.on('console', (msg) => console.log('[PAGE]', msg.type(), msg.text()));
});

test('Login, open Process, preview first receipt', async ({ page }) => {
  // Navigate to login using baseURL from config.
  await page.goto('/login');

  // Fill password. Prefer label when available as it's more robust in localized UIs.
  // If your login also requires a username, add it here accordingly.
  const password = page.getByLabel('Lösenord', { exact: true }).or(page.getByRole('textbox', { name: 'Lösenord' }));
  await expect(password).toBeVisible();
  await password.fill('adminadmin');

  // Click "Logga in"
  const loginBtn = page.getByRole('button', { name: /^Logga in$/ });
  await expect(loginBtn).toBeVisible();
  await Promise.all([
    // Wait for navigation or stability after clicking login.
    page.waitForLoadState('networkidle'),
    loginBtn.click(),
  ]);

  // After login, wait for the main navigation to be ready.
  // "Process" can be a link or a button depending on your UI.
  const processNav = page.getByRole('button', { name: /^Process$/ }).or(page.getByRole('link', { name: /^Process$/ }));
  await processNav.waitFor({ state: 'visible' });
  await processNav.click();

  // Ensure the Process view loaded (look for some known heading or control on that page).
  // Update the selector below to a reliable marker in your Process page if you have one.
  await page.waitForLoadState('networkidle');

  // Click on a "Förhandsgranska kvitto" button without hardcoding a UUID.
  // Using nth(4) to get the 5th item (0-indexed)
  const previewBtn = page.getByRole('button', { name: /Förhandsgranska kvitto/i }).nth(4);
  await expect(previewBtn).toBeVisible();
  await previewBtn.click();

  const overlayDebugHandle = await page.waitForFunction(() => (window as any).__overlayDebug ?? null, undefined, {
    timeout: 15000,
  });
  const overlayDebug = await overlayDebugHandle.jsonValue();
  console.log('[OVERLAY_DEBUG_DATA]', JSON.stringify(overlayDebug, null, 2));

  // Keep the review modal open for 5 seconds before test ends
  await page.waitForTimeout(5000);
});

