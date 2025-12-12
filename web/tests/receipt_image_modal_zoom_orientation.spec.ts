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
  const previewBtn = page.getByRole('button', { name: /Förhandsgranska kvitto/i }).first();
  await expect(previewBtn).toBeVisible();
  await previewBtn.click();

  // Modal should open. The stable wrapper is modal-backdrop with receipt-preview-modal class.
  const previewModalBackdrop = page.locator('.modal-backdrop.receipt-preview-modal');
  await expect(previewModalBackdrop).toBeVisible();

  // Multi-page navigation (only when modal exposes pages).
  const pageIndicator = page.locator('.receipt-modal-page-indicator');
  const indicatorCount = await pageIndicator.count();
  if (indicatorCount > 0) {
    const indicatorText = (await pageIndicator.first().textContent()) || '';
    const match = indicatorText.match(/Sida\s+(\d+)\s+av\s+(\d+)/i);
    const totalPages = match ? Number(match[2]) : 0;

    if (totalPages > 1) {
      const prevPage = page.getByRole('button', { name: 'Föregående sida' });
      const nextPage = page.getByRole('button', { name: 'Nästa sida' });
      const previewImage = page.locator('img.receipt-modal-image');

      await expect(prevPage).toHaveCount(0);
      await expect(nextPage).toBeVisible();

      const srcBefore = await previewImage.getAttribute('src');
      await nextPage.click();
      await expect.poll(async () => await previewImage.getAttribute('src')).not.toBe(srcBefore);
      await expect(prevPage).toBeVisible();
    }
  }

  // If field overlays are present, verify they are not opaque.
  const overlays = page.locator('.receipt-modal-overlay');
  const overlayCount = await overlays.count();
  if (overlayCount > 0) {
    const overlayBackgrounds = await overlays.evaluateAll((elements) =>
      elements.map((element) => {
        const { backgroundColor } = window.getComputedStyle(element);
        return backgroundColor.toLowerCase();
      }),
    );

    const hasOpaqueOverlay = overlayBackgrounds.some((color) => {
      if (color === 'transparent') {
        return false;
      }
      const match = color.match(/rgba?\(([^)]+)\)/);
      if (!match) {
        return true;
      }
      const channels = match[1].split(',').map((channel) => Number.parseFloat(channel.trim()));
      if (channels.length < 4) {
        return true;
      }
      const alpha = channels[3];
      return alpha > 0;
    });

    expect(hasOpaqueOverlay).toBeFalsy();
  }

  // AI3/AI4 - the items section should render extracted line items, not the empty state.
  const itemsHeader = page.locator('.receipt-item-header-main');
  await expect(itemsHeader).toBeVisible({ timeout: 15000 });
  await page.waitForFunction(
    () => document.querySelector('.receipt-item-card-new') !== null,
    undefined,
    { timeout: 15000 },
  );
  const itemCards = page.locator('.receipt-item-card-new');
  await expect(itemCards.first()).toBeVisible();

  // Restart conversion should respond 200 and success=true.
  const restartButton = page.getByRole('button', { name: 'Starta om konvertering' });
  await expect(restartButton).toBeVisible();
  const [restartResponse] = await Promise.all([
    page.waitForResponse((response) => response.url().includes('/ai/api/receipts/') && response.url().endsWith('/restart-ai') && response.request().method() === 'POST'),
    restartButton.click(),
  ]);
  expect(restartResponse.status()).toBe(200);
  const restartJson = await restartResponse.json().catch(() => null);
  expect(restartJson?.success).toBeTruthy();
});
