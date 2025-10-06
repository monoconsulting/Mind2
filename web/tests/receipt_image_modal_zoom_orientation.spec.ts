import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('Receipt preview modal - image zoom and orientation', async ({ page }) => {
  // Enable console logging to debug issues
  page.on('console', msg => console.log(`PAGE LOG: ${msg.text()}`));
  page.on('pageerror', err => console.log(`PAGE ERROR: ${err.message}`));

  // Login
  await page.goto('http://localhost:8008/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  // Wait for login to complete - just wait for the sidebar to appear
  await page.waitForSelector('[role="navigation"], .sidebar, button:has-text("Kvitton")', { timeout: 10000 });

  // Navigate to receipts
  await page.getByRole('button', { name: 'Kvitton' }).click();

  // Wait for receipts to load
  await page.waitForTimeout(5000);

  // Debug: Take screenshot of receipts page
  await page.screenshot({ path: 'web/test-results/receipts-page.png' });

  // Find the first receipt preview thumbnail (the image itself is clickable)
  const firstPreviewThumb = page.locator('.preview-thumb').first();
  await expect(firstPreviewThumb).toBeVisible({ timeout: 10000 });

  // Click the first preview thumbnail
  await firstPreviewThumb.click();

  // Wait a moment for modal to appear
  await page.waitForTimeout(1000);

  // Wait for modal to open - check for modal-backdrop class
  const modal = page.locator('.modal-backdrop.receipt-preview-modal, [role="dialog"]');
  await expect(modal).toBeVisible({ timeout: 10000 });

  // Wait for the receipt image in the center column
  const receiptImage = modal.locator('.receipt-modal-image');
  await expect(receiptImage).toBeVisible({ timeout: 30000 });

  // Verify the modal has the new structure with 3 columns
  const leftColumn = modal.locator('.receipt-modal-left');
  const centerColumn = modal.locator('.receipt-modal-center');
  const rightColumn = modal.locator('.receipt-modal-right');

  await expect(leftColumn).toBeVisible();
  await expect(centerColumn).toBeVisible();
  await expect(rightColumn).toBeVisible();

  // Verify individual scrolling is enabled
  await expect(leftColumn).toHaveCSS('overflow-y', 'auto');
  await expect(centerColumn).toHaveCSS('overflow-y', 'auto');
  await expect(rightColumn).toHaveCSS('overflow-y', 'auto');

  // Verify the new boxes are present
  await expect(modal.getByText('Grunddata (Företagsinformation)')).toBeVisible();
  await expect(modal.getByText('Betalningstyp')).toBeVisible();
  await expect(modal.getByText('Belopp')).toBeVisible();
  await expect(modal.getByText('Övrigt')).toBeVisible();
  await expect(modal.getByText('Varor och kontering')).toBeVisible();

  // Take screenshot for visual verification
  await page.waitForTimeout(2000);
  await expect(page).toHaveScreenshot('001.png', { fullPage: true });
});
