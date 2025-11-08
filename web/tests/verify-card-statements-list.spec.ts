import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test.describe('Card Statements List', () => {
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

  test('should display a list of card statements', async ({ page }) => {
    // Check for the main heading
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();

    // Wait for the table to be populated
    await page.waitForSelector('table.min-w-full');

    // Check that the "no statements found" message is not visible
    await expect(page.getByText('Inga kontoutdrag hittades.')).not.toBeVisible();

    // Check that there is at least one row in the table body
    const tableBody = page.locator('table.min-w-full > tbody');
    const rows = tableBody.locator('tr');
    await expect(rows).toHaveCountGreaterThan(0);

    // Check for a known column header
    await expect(page.getByRole('cell', { name: 'Kort' })).toBeVisible();
  });

  test('should update Senast uppdaterad after Återuppta fakturaimport', async ({ page }) => {
    await page.waitForSelector('table.min-w-full');

    const rows = page.locator('table.min-w-full > tbody > tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    const firstRow = rows.first();
    const fakturaLine = await firstRow
      .locator('div')
      .filter({ hasText: /Fakturanummer:/ })
      .first()
      .innerText();
    const invoiceRef = fakturaLine.split(':').pop()?.trim() ?? '';
    expect(invoiceRef.length).toBeGreaterThan(0);

    const findRowByInvoice = () =>
      page.locator('table.min-w-full > tbody > tr').filter({ hasText: invoiceRef }).first();

    const initialTimestamp = (await findRowByInvoice().locator('td').nth(9).innerText()).trim();

    await findRowByInvoice().getByRole('button', { name: /Återuppta fakturaimport/i }).click();
    await page.waitForTimeout(1500);

    await page.getByRole('button', { name: 'Uppdatera' }).click();
    await page.waitForLoadState('networkidle');
    await expect(findRowByInvoice()).toBeVisible();

    const refreshedTimestamp = (await findRowByInvoice().locator('td').nth(9).innerText()).trim();
    expect(refreshedTimestamp).not.toBe('');
    expect(refreshedTimestamp).not.toBe(initialTimestamp);
  });
});
