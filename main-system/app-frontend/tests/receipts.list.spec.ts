import { test, expect } from '@playwright/test';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'adminadmin';

const capture = async (page, name) => {
  const filePath = test.info().outputPath(`${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  await test.info().attach(name, { path: filePath, contentType: 'image/png' });
};

test('kvittolistan visar data och förhandsgranskning utan mocks', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'networkidle' });
  await page.fill('#login-username', 'admin');
  await page.fill('#login-password', ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL('**/', { waitUntil: 'networkidle' }),
    page.getByRole('button', { name: 'Logga in' }).click(),
  ]);

  await page.getByRole('button', { name: 'Kvitton', exact: true }).click();
  await page.waitForURL('**/receipts', { waitUntil: 'networkidle' });
  await expect(page.locator('.page-title')).toHaveText('Kvitton');

  const table = page.locator('table.table-dark');
  await expect(table).toBeVisible();

  const rows = table.locator('tbody tr');
  const rowCount = await rows.count();
  expect(rowCount, 'Inga kvitton kunde läsas från backend').toBeGreaterThan(0);

  const firstRow = rows.first();
  const cells = firstRow.locator('td');
  await expect(cells.nth(0).locator('img')).toBeVisible({ timeout: 15000 });
  await expect(cells.nth(1)).not.toHaveText(/^\s*$/);
  await expect(cells.nth(2)).not.toHaveText(/^\s*$/);
  await expect(cells.nth(3)).not.toHaveText(/^\s*$/);
  await expect(cells.nth(4)).not.toHaveText(/^\s*$/);
  await expect(cells.nth(5)).not.toHaveText(/^\s*$/);
  await expect(cells.nth(6)).not.toHaveText(/^\s*$/);
  await expect(cells.nth(7).locator('button', { hasText: 'Visa' })).toBeVisible();

  await capture(page, 'rec-lista');

  await cells.nth(7).locator('button', { hasText: 'Visa' }).click();
  await expect(page.locator('.modal-backdrop .preview-image')).toBeVisible({ timeout: 10000 });
  await capture(page, 'rec-preview');
});
