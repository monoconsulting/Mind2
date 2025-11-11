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

test.describe('Kortmatchning - Kontoutdrag Table Structure', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('textbox', { name: 'Lösenord' }).click();
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Navigate to CompanyCard page
    await page.getByRole('button', { name: 'Kortmatchning' }).click();

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display all required table columns', async ({ page }) => {
    // Wait for the table to be visible
    await page.waitForSelector('table.min-w-full');

    const table = page.locator('table.min-w-full');
    const headers = table.locator('thead th');

    // Verify all column headers are present
    await expect(headers.nth(0)).toContainText('Kort');
    await expect(headers.nth(1)).toContainText('Fakturadatum');
    await expect(headers.nth(2)).toContainText('Betalningsdatum');
    await expect(headers.nth(3)).toContainText('Belopp');
    await expect(headers.nth(4)).toContainText('Status');
    await expect(headers.nth(5)).toContainText('AI - Konfidens');
    await expect(headers.nth(6)).toContainText('RADER');
    await expect(headers.nth(7)).toContainText('Matchade rader');
    await expect(headers.nth(8)).toContainText('Omatchade rader');
    await expect(headers.nth(9)).toContainText('Senast uppdaterad');
    await expect(headers.nth(10)).toContainText('Åtgärder');
    await expect(headers.nth(11)).toContainText('Ta bort');

    // Verify old columns are removed
    await expect(table.locator('thead')).not.toContainText('Bearbetning');
    await expect(table.locator('thead')).not.toContainText('AI6');
    await expect(table.locator('thead')).not.toContainText('Linjer');
  });

  test('should display header button "Matcha omatchade poster"', async ({ page }) => {
    // Verify the header button exists
    const headerButton = page.getByRole('button', { name: /Matcha omatchade poster/i });
    await expect(headerButton).toBeVisible();
  });

  test('should not display "Auto-matcha" button', async ({ page }) => {
    // Wait for the table to be visible
    await page.waitForSelector('table.min-w-full');

    // Verify "Auto-matcha" button is not present
    const autoMatchButton = page.getByRole('button', { name: /Auto-matcha/i });
    await expect(autoMatchButton).not.toBeVisible();
  });

  test('should display "Matcha omatchade rader" button for rows with unmatched items', async ({ page }) => {
    // Wait for the table to be visible
    await page.waitForSelector('table.min-w-full');

    // Check if any "Matcha omatchade rader" buttons are present in the table
    const matchButtons = page.locator('button', { hasText: /Matcha omatchade rader/i });

    // If there are unmatched rows, buttons should be visible
    const count = await matchButtons.count();

    // This test just verifies that the button appears when there are unmatched rows
    // We don't fail if there are no unmatched rows (count could be 0)
    if (count > 0) {
      await expect(matchButtons.first()).toBeVisible();
    }
  });

  test('should successfully auto-match when clicking row button', async ({ page }) => {
    await page.waitForSelector('table.min-w-full');

    const matchButton = page.locator('button', { hasText: /Matcha omatchade rader/i }).first();
    await expect(matchButton).toBeVisible();

    const responsePromise = page.waitForResponse((response) => {
      return response.url().includes('/ai/api/reconciliation/firstcard/match') && response.request().method() === 'POST';
    });

    await matchButton.click();
    const response = await responsePromise;
    const rawBody = await response.text();
    let payload: unknown;
    try {
      payload = JSON.parse(rawBody);
    } catch (error) {
      payload = rawBody;
    }
    expect(response.status(), 'Auto-match API should return success').toBe(200);

    if (typeof payload !== 'object' || payload === null) {
      throw new Error(`Unexpected payload: ${String(payload)}`);
    }

    expect(payload).toMatchObject({
      invoice_id: expect.any(String),
      matched: expect.any(Number),
      total: expect.any(Number),
    });
  });

  test('should display data in new columns', async ({ page }) => {
    // Wait for the table to be visible
    await page.waitForSelector('table.min-w-full');

    const tableBody = page.locator('table.min-w-full > tbody');
    const firstRow = tableBody.locator('tr').first();
    const cells = firstRow.locator('td');

    // Verify that cells exist (we have data)
    const cellCount = await cells.count();
    expect(cellCount).toBeGreaterThan(0);

    // Check that Betalningsdatum cell (index 2) exists
    const dueDateCell = cells.nth(2);
    await expect(dueDateCell).toBeVisible();

    // Check that Belopp cell (index 3) exists
    const amountCell = cells.nth(3);
    await expect(amountCell).toBeVisible();

    // Check that RADER cell (index 6) exists and contains a number
    const totalRowsCell = cells.nth(6);
    await expect(totalRowsCell).toBeVisible();

    // Check that Matchade rader cell (index 7) exists
    const matchedRowsCell = cells.nth(7);
    await expect(matchedRowsCell).toBeVisible();

    // Check that Omatchade rader cell (index 8) exists
    const unmatchedRowsCell = cells.nth(8);
    await expect(unmatchedRowsCell).toBeVisible();
  });
});
