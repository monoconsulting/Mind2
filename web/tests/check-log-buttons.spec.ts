import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1200,
    width: 1900
  }
});

test('Check log buttons exist in Process and Receipts', async ({ page }) => {
  // Login
  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
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
