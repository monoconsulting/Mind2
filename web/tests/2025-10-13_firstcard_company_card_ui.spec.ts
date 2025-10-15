import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    width: 1900,
    height: 1200,
  },
});

test('Company card dashboard renders summary and detail panels', async ({ page }) => {
  await page.goto('http://localhost:8008/login');

  await page.locator('input[type="text"]').first().fill('admin');
  await page.locator('input[type="password"]').fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  await page.getByRole('button', { name: 'Kortmatchning' }).click();

  await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Utdragsdetaljer' })).toBeVisible();

  await expect(page.getByText('Matchade utdrag')).toBeVisible();
  await expect(page.getByText('P\\u00E5g\\u00E5ende matchningar')).toBeVisible();
  await expect(page.getByText('Kr\\u00E4ver \\u00E5tg\\u00E4rd')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ladda upp utdrag' })).toBeVisible();

  await expect(page.getByText('Inga kontoutdrag hittades.')).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Period' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: '\\u00C5tg\\u00E4rder' })).toBeVisible();
});
