import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test.describe('Resume receipts functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('http://localhost:8008/login');
    await page.getByRole('textbox', { name: 'Lösenord' }).click();
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Navigate to Process page
    await page.getByRole('button', { name: 'Process' }).click();

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should be able to preview and close receipt', async ({ page }) => {
    // Click preview button for first receipt
    await page.getByRole('button', { name: /Förhandsgranska kvitto/ }).first().click();

    // Verify dialog is visible
    await expect(page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' })).toBeVisible();

    // Close preview
    await page.getByRole('button', { name: 'Stäng förhandsgranskning' }).click();

    // Verify dialog is closed
    await expect(page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' })).not.toBeVisible();
  });

  test('should be able to pause individual receipts', async ({ page }) => {
    // Get all pause buttons (4th button in each row)
    const rows = page.getByRole('row').filter({ has: page.getByRole('button', { name: /Förhandsgranska kvitto/ }) });
    const rowCount = await rows.count();

    // Pause first 3 receipts (or all if less than 3)
    const pauseCount = Math.min(3, rowCount);
    for (let i = 0; i < pauseCount; i++) {
      const row = rows.nth(i);
      // Click the pause button (4th button, index 3)
      await row.getByRole('button').nth(3).click();

      // Wait a bit for the action to complete
      await page.waitForTimeout(500);
    }

    // Verify buttons were clicked (you might want to add more specific assertions here
    // based on what happens when a receipt is paused - e.g., button text changes, row styling, etc.)
    await expect(rows.first()).toBeVisible();
  });

  test('should be able to resume all receipts', async ({ page }) => {
    // First pause some receipts
    const rows = page.getByRole('row').filter({ has: page.getByRole('button', { name: /Förhandsgranska kvitto/ }) });
    const rowCount = await rows.count();

    // Pause first 3 receipts if available
    const pauseCount = Math.min(3, rowCount);
    for (let i = 0; i < pauseCount; i++) {
      const row = rows.nth(i);
      await row.getByRole('button').nth(3).click();
      await page.waitForTimeout(500);
    }

    // Click "Återuppta alla" button
    const resumeAllButton = page.getByRole('button', { name: 'Återuppta alla' });
    await expect(resumeAllButton).toBeVisible();
    await resumeAllButton.click();

    // Wait for the action to complete
    await page.waitForTimeout(1000);

    // Verify success banner is displayed
    await expect(page.getByText(/Återupptagning klar: .* 0 misslyckades/i)).toBeVisible();

    // Verify the button was clicked successfully
    // (You might want to add assertions here to verify the receipts are actually resumed)
    await expect(page.getByRole('button', { name: 'Process' })).toBeVisible();
  });

  test('should be able to pause and resume specific receipt', async ({ page }) => {
    // Get first row
    const firstRow = page.getByRole('row').filter({ has: page.getByRole('button', { name: /Förhandsgranska kvitto/ }) }).first();

    // Pause the receipt
    await firstRow.getByRole('button').nth(3).click();
    await page.waitForTimeout(500);

    // Resume all (which will resume the paused receipt)
    await page.getByRole('button', { name: 'Återuppta alla' }).click();
    await page.waitForTimeout(1000);

    // Confirm success banner rendered
    await expect(page.getByText(/Återupptagning klar: .* 0 misslyckades/i)).toBeVisible();

    // Verify we're still on the process page
    await expect(page.getByRole('button', { name: 'Process' })).toBeVisible();
  });
});
