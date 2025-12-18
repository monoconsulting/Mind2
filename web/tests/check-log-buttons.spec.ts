import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1200,
    width: 1900
  },
  permissions: ['clipboard-read', 'clipboard-write'],
  recordVideo: {
    dir: 'web/test-results/media/video',
    size: { width: 1900, height: 1200 },
  },
});

test('Check log buttons exist in Process and Receipts', async ({ page }) => {
  // Login
  await page.goto('http://localhost:5169/login');
  await page.locator('#login-username').fill('admin');
  await page.locator('#login-password').fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  // Wait for navigation
  await page.waitForURL('http://localhost:5169/', { timeout: 10000 });

  // Go to Process page
  await page.getByRole('button', { name: 'Process' }).click();
  await page.waitForTimeout(2000);

  // Take screenshot of Process page
  await page.screenshot({ path: 'test-results/process-page.png', fullPage: true });

  // Check if there's a log button (FiFileText icon) in Process page
  const processLogButtons = page.locator('button[title="Visa logg"]');
  const processLogCount = await processLogButtons.count();
  console.log(`Found ${processLogCount} log buttons in Process page`);

  // Go to Receipts page
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.waitForTimeout(2000);

  // Take screenshot of Receipts page
  await page.screenshot({ path: 'test-results/receipts-page.png', fullPage: true });

  // Check if there's a log button in Receipts page
  const receiptsLogButtons = page.locator('button[title="Visa logg"]');
  const receiptsLogCount = await receiptsLogButtons.count();
  console.log(`Found ${receiptsLogCount} log buttons in Receipts page`);

  // Assert that we found at least one log button in each page
  expect(processLogCount).toBeGreaterThan(0);
  expect(receiptsLogCount).toBeGreaterThan(0);
});

test('Process log modal shows ai_stage_name and copy gives feedback @process-log-copy', async ({ page }, testInfo) => {
  test.setTimeout(2 * 60_000);

  // Login
  await page.goto('http://localhost:5169/login');
  await page.locator('#login-username').fill('admin');
  await page.locator('#login-password').fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.waitForURL('http://localhost:5169/', { timeout: 10000 });

  // Go to Process page
  await page.getByRole('button', { name: 'Process' }).click();
  await page.waitForLoadState('networkidle');

  const processLogButtons = page.locator('button[title="Visa logg"]');
  await expect(processLogButtons.first()).toBeVisible();
  await processLogButtons.first().click();

  const dialog = page.getByRole('dialog', { name: 'Bearbetningslogg' });
  await expect(dialog).toBeVisible();

  // The modal should show ai_stage_name headings (not AI-entry 1..N).
  await expect(dialog).not.toContainText('AI-entry');

  const copyButton = dialog.getByRole('button', { name: /Kopiera allt|Kopierar\.\.\.|Copied!|Copy failed/i });
  await expect(copyButton).toBeVisible();

  await copyButton.click();
  await expect(copyButton).toContainText(/Copied!|Copy failed/i);

  const copied = await page.evaluate(async () => {
    try {
      return await navigator.clipboard.readText();
    } catch {
      return null;
    }
  });

  expect(copied).toBeTruthy();
  expect(String(copied)).not.toContain('AI-entry');
  expect(String(copied)).not.toContain('\n');

  await testInfo.attach('process-log-modal', {
    body: await page.screenshot({ fullPage: true }),
    contentType: 'image/png',
  });
});
