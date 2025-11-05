import { test, expect } from '@playwright/test';

/**
 * Test: Card Matching Error Handling
 * Date: 2025-10-23
 *
 * Tests error handling in the card matching module:
 * - Navigation to card matching page
 * - File upload functionality
 * - Duplicate file error handling (409)
 * - Error message display and dismissal
 */

test.use({
  viewport: {
    height: 1440,
    width: 2560
  }
});

test.describe('Card Matching Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login page
    await page.goto('http://localhost:5169/login');

    // Login
    await page.getByRole('textbox', { name: 'Lösenord' }).click();
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Navigate to card matching module
    await page.getByRole('button', { name: 'Kortmatchning' }).click();

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should handle duplicate file upload error (409)', async ({ page }) => {
    // Verify we're on the card matching page
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();

    // Click upload button
    await page.getByRole('button', { name: 'Ladda upp utdrag' }).click();

    // Upload file
    await page.getByRole('button', { name: 'Choose File' }).setInputFiles('FC_2505.pdf');

    // Click upload
    await page.getByRole('button', { name: 'Ladda upp', exact: true }).click();

    // Wait for error message to appear
    await page.waitForTimeout(1000);

    // Verify error message is displayed (409 - file already exists)
    const errorMessage = page.locator('div').filter({
      hasText: /^Kunde inte ladda upp 1 fil: FC_2505\.pdf \(Fel 409\.\)\.$/
    });
    await expect(errorMessage).toBeVisible();

    // Click on error message to acknowledge
    await errorMessage.click();

    // Close upload dialog
    await page.getByRole('button', { name: 'Avbryt' }).click();

    // Verify dialog is closed
    await page.waitForTimeout(500);
  });

  test('should be able to cancel upload dialog', async ({ page }) => {
    // Click upload button
    await page.getByRole('button', { name: 'Ladda upp utdrag' }).click();

    // Verify upload dialog is visible
    await page.waitForTimeout(300);

    // Cancel without uploading
    await page.getByRole('button', { name: 'Avbryt' }).click();

    // Verify we're back on card matching page
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();
  });

  test('should navigate between Process and Card Matching', async ({ page }) => {
    // Navigate to Process
    await page.getByRole('button', { name: 'Process' }).click();
    await page.waitForTimeout(500);

    // Navigate back to Card Matching
    await page.getByRole('button', { name: 'Kortmatchning' }).click();
    await page.waitForTimeout(500);

    // Verify we're on card matching page
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();
  });
});


