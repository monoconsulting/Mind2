import { test, expect } from '@playwright/test';

/**
 * Test: Card Matching Error Handling
 * Date: 2025-10-23
 *
 * Tests error handling in the card matching module:
 * - Navigation to card matching page
 * - File upload functionality
 * - Duplicate file handling ("already imported")
 */

test.use({
  viewport: {
    height: 1200,
    width: 1900
  },
  recordVideo: {
    dir: 'web/test-results/media/video',
    size: { width: 1900, height: 1200 },
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

  test('should treat duplicate upload as already imported (non-fatal)', async ({ page }) => {
    // Verify we're on the card matching page
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();

    const uploadOnce = async () => {
      await page.getByRole('button', { name: 'Ladda upp utdrag' }).click();
      const uploadDialog = page.getByRole('dialog', { name: 'Ladda upp kontoutdrag' });
      await expect(uploadDialog).toBeVisible();

      await page.getByRole('button', { name: 'Choose File' }).setInputFiles('web/FC_2505.pdf');
      await page.getByRole('button', { name: 'Ladda upp', exact: true }).click();

      // Duplicate uploads should not be treated as a hard error in the UI.
      // The upload dialog closes automatically on success paths.
      await expect(uploadDialog).toBeHidden({ timeout: 15000 });
    };

    // Upload once (creates or reuses record), then upload again (should be treated as already imported).
    await uploadOnce();
    await uploadOnce();

    // Verify we are still on the card matching page (no crash / no blocking error).
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();
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


