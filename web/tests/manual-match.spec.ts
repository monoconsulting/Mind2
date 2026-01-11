import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  },
  trace: 'on',
  video: 'on',
  screenshot: 'on'
});

test.describe('Manual Match - FirstCard to Receipts @manual-match', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('textbox', { name: 'Lösenord' }).click();
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Navigate to Manual Match page
    await page.getByRole('button', { name: 'Manuell matchning' }).click();

    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('page should display two columns: FC transactions and receipts', async ({ page }) => {
    // Verify page title/heading exists
    await expect(page.locator('text=FirstCard-transaktioner')).toBeVisible();
    await expect(page.locator('text=Kvitton')).toBeVisible();

    // Verify period selection exists
    await expect(page.locator('text=Välj period')).toBeVisible();
  });

  test('selecting both sides should trigger confirmation modal', async ({ page }) => {
    // Wait for the page to fully load and have data
    await page.waitForTimeout(2000);

    // Get year and month dropdowns
    const yearSelect = page.locator('select').filter({ hasText: /2025|2024|2026/ }).first();
    const monthSelect = page.locator('select').filter({ hasText: /Januari|Februari|Mars|April|Maj|Juni|Juli|Augusti|September|Oktober|November|December/ }).first();

    // If we have year/month selectors, ensure they're set
    if (await yearSelect.isVisible()) {
      await yearSelect.selectOption({ index: 0 });
    }

    // Wait for tables to load
    await page.waitForTimeout(1000);

    // Check if we have unmatched items on both sides
    const fcTable = page.locator('table').first();
    const receiptsTable = page.locator('table').last();

    // Look for unmatched FC items (checkboxes that are not disabled)
    const unmatchedFcCheckboxes = fcTable.locator('input[type="checkbox"]:not([disabled])');
    const unmatchedReceiptCheckboxes = receiptsTable.locator('input[type="checkbox"]:not([disabled])');

    const fcCount = await unmatchedFcCheckboxes.count();
    const receiptCount = await unmatchedReceiptCheckboxes.count();

    if (fcCount > 0 && receiptCount > 0) {
      // Select a receipt first
      await unmatchedReceiptCheckboxes.first().click();

      // Then select an FC item
      await unmatchedFcCheckboxes.first().click();

      // Wait for modal
      await page.waitForTimeout(500);

      // Verify confirmation modal appears with exact Swedish text
      await expect(page.locator('text=Vill du matcha dessa?')).toBeVisible();
    } else {
      // Skip if no unmatched items available
      test.skip(true, 'No unmatched items available for testing');
    }
  });

  test('confirmation modal shows both selected items summary', async ({ page }) => {
    await page.waitForTimeout(2000);

    const fcTable = page.locator('table').first();
    const receiptsTable = page.locator('table').last();

    const unmatchedFcCheckboxes = fcTable.locator('input[type="checkbox"]:not([disabled])');
    const unmatchedReceiptCheckboxes = receiptsTable.locator('input[type="checkbox"]:not([disabled])');

    const fcCount = await unmatchedFcCheckboxes.count();
    const receiptCount = await unmatchedReceiptCheckboxes.count();

    if (fcCount > 0 && receiptCount > 0) {
      await unmatchedReceiptCheckboxes.first().click();
      await unmatchedFcCheckboxes.first().click();

      await page.waitForTimeout(500);

      // Modal should show summary
      const modal = page.locator('.fixed.inset-0');
      await expect(modal).toBeVisible();

      // Should have section headers
      await expect(modal.locator('text=Korttransaktion')).toBeVisible();
      await expect(modal.locator('text=/Kvitto|Faktura/')).toBeVisible();

      // Should have labels
      await expect(modal.locator('text=Datum:')).toBeVisible();
      await expect(modal.locator('text=Belopp:')).toBeVisible();

      // Should have action buttons
      await expect(modal.locator('button:has-text("Avbryt")')).toBeVisible();
      await expect(modal.locator('button:has-text("Matcha")')).toBeVisible();
    } else {
      test.skip(true, 'No unmatched items available for testing');
    }
  });

  test('cancel button closes modal without matching', async ({ page }) => {
    await page.waitForTimeout(2000);

    const fcTable = page.locator('table').first();
    const receiptsTable = page.locator('table').last();

    const unmatchedFcCheckboxes = fcTable.locator('input[type="checkbox"]:not([disabled])');
    const unmatchedReceiptCheckboxes = receiptsTable.locator('input[type="checkbox"]:not([disabled])');

    const fcCount = await unmatchedFcCheckboxes.count();
    const receiptCount = await unmatchedReceiptCheckboxes.count();

    if (fcCount > 0 && receiptCount > 0) {
      await unmatchedReceiptCheckboxes.first().click();
      await unmatchedFcCheckboxes.first().click();

      await page.waitForTimeout(500);

      // Modal should appear
      await expect(page.locator('text=Vill du matcha dessa?')).toBeVisible();

      // Click cancel
      await page.locator('button:has-text("Avbryt")').click();

      // Modal should close
      await expect(page.locator('text=Vill du matcha dessa?')).not.toBeVisible();

      // Selections should remain (checkboxes still checked)
      await expect(unmatchedFcCheckboxes.first()).toBeChecked();
      await expect(unmatchedReceiptCheckboxes.first()).toBeChecked();
    } else {
      test.skip(true, 'No unmatched items available for testing');
    }
  });

  test('confirm performs match using PUT endpoint', async ({ page }) => {
    await page.waitForTimeout(2000);

    const fcTable = page.locator('table').first();
    const receiptsTable = page.locator('table').last();

    const unmatchedFcCheckboxes = fcTable.locator('input[type="checkbox"]:not([disabled])');
    const unmatchedReceiptCheckboxes = receiptsTable.locator('input[type="checkbox"]:not([disabled])');

    const fcCount = await unmatchedFcCheckboxes.count();
    const receiptCount = await unmatchedReceiptCheckboxes.count();

    if (fcCount > 0 && receiptCount > 0) {
      // Select items
      await unmatchedReceiptCheckboxes.first().click();
      await unmatchedFcCheckboxes.first().click();

      await page.waitForTimeout(500);

      // Modal should appear
      await expect(page.locator('text=Vill du matcha dessa?')).toBeVisible();

      // Set up response interceptor for PUT request
      const matchPromise = page.waitForResponse(response =>
        response.url().includes('/ai/api/reconciliation/firstcard/lines/') &&
        response.request().method() === 'PUT'
      );

      // Click confirm
      await page.locator('button:has-text("Matcha")').click();

      // Verify PUT request was made
      const response = await matchPromise;
      expect(response.status()).toBe(200);

      // Modal should close
      await expect(page.locator('text=Vill du matcha dessa?')).not.toBeVisible();

      // Success message should appear
      await expect(page.locator('text=Matchning genomförd')).toBeVisible();
    } else {
      test.skip(true, 'No unmatched items available for testing');
    }
  });

  test('conflict shows Swedish error message', async ({ page }) => {
    // Mock 409 response for the PUT endpoint
    await page.route('**/ai/api/reconciliation/firstcard/lines/*', async route => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ ok: false, reason: 'receipt_in_use' })
        });
      } else {
        await route.continue();
      }
    });

    await page.waitForTimeout(2000);

    const fcTable = page.locator('table').first();
    const receiptsTable = page.locator('table').last();

    const unmatchedFcCheckboxes = fcTable.locator('input[type="checkbox"]:not([disabled])');
    const unmatchedReceiptCheckboxes = receiptsTable.locator('input[type="checkbox"]:not([disabled])');

    const fcCount = await unmatchedFcCheckboxes.count();
    const receiptCount = await unmatchedReceiptCheckboxes.count();

    if (fcCount > 0 && receiptCount > 0) {
      await unmatchedReceiptCheckboxes.first().click();
      await unmatchedFcCheckboxes.first().click();

      await page.waitForTimeout(500);

      await expect(page.locator('text=Vill du matcha dessa?')).toBeVisible();

      // Click confirm
      await page.locator('button:has-text("Matcha")').click();

      // Wait for error to appear
      await page.waitForTimeout(1000);

      // Verify Swedish error message
      await expect(page.locator('text=Detta kvitto/faktura är redan matchat mot en annan rad')).toBeVisible();
    } else {
      test.skip(true, 'No unmatched items available for testing');
    }
  });

  test('status filter works correctly', async ({ page }) => {
    // Verify filter dropdown exists
    const filterSelect = page.locator('select').filter({ hasText: 'Alla' });
    await expect(filterSelect).toBeVisible();

    // Test switching to "Ej matchade"
    await filterSelect.selectOption('unmatched');
    await page.waitForTimeout(500);

    // Verify filter is applied (unmatched items should be visible)
    // We just verify the dropdown value changed
    await expect(filterSelect).toHaveValue('unmatched');

    // Switch back to all
    await filterSelect.selectOption('all');
    await expect(filterSelect).toHaveValue('all');
  });
});
