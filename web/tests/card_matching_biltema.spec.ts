import { test, expect, Page } from '@playwright/test';

test.describe('FirstCard Biltema matching', () => {
  test.use({
    viewport: { width: 3440, height: 1440 },
  });

  const login = async (page: Page) => {
    await page.goto('http://localhost:5169/login');
    await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();
    await expect(page.getByRole('button', { name: 'Kortmatchning' })).toBeVisible();
  };

  test('Biltema receipt is matched to statement line 856', async ({ page }) => {
    await login(page);

    await page.getByRole('button', { name: 'Kortmatchning' }).click();
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();

    const statementRow = page.getByRole('row', {
      name: /Fakturanummer:\s*2534253760/i,
    });
    await expect(statementRow).toBeVisible();
    await statementRow.click();

    const biltemaRow = page.locator('tr', { hasText: /Rad-ID:\s*856/ });
    await expect(biltemaRow).toBeVisible();
    await expect(biltemaRow).toContainText('2025-07-03');
    await expect(biltemaRow).toContainText(/BILTEMA SWEDEN/i);

    const statusCell = biltemaRow.locator('td').nth(3);
    await expect(statusCell).toContainText(/Auto/i);

    const matchCell = biltemaRow.locator('td').nth(4);
    await expect(matchCell).not.toContainText(/Ingen/i);
    await expect(matchCell).toContainText(/BILTEMA/i);
    await expect(matchCell.getByRole('button', { name: 'Förhandsgranska' })).toBeVisible();
  });
});
