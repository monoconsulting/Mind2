import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('manual match shows every receipt for the month with diverse merchants', async ({ page }) => {
  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Manuell matchning' }).click();

  const periodCard = page.locator('.card', { has: page.getByRole('heading', { name: 'Välj period' }) });
  await expect(periodCard).toBeVisible();

  const yearSelect = periodCard.locator('select').first();
  const monthSelect = periodCard.locator('select').nth(1);

  await yearSelect.selectOption('2025');
  await monthSelect.selectOption('6');

  const receiptsCard = page.locator('.card', { has: page.getByRole('heading', { name: 'Kvitton' }) });
  const subtitle = receiptsCard.locator('.card-subtitle');
  await expect(subtitle).not.toHaveText('Laddar...', { timeout: 30000 });

  const receiptRows = receiptsCard.locator('tbody tr');
  await expect(receiptRows.first()).toBeVisible({ timeout: 30000 });
  const rowCount = await receiptRows.count();
  expect(rowCount).toBeGreaterThan(0);

  const receiptDateCells = receiptRows.locator('td:nth-child(2)');
  const receiptDates = await receiptDateCells.allTextContents();
  for (const text of receiptDates) {
    expect(text).toContain('2025-06');
  }

  const merchantCells = receiptRows.locator('td:nth-child(3)');
  const merchantTexts = (await merchantCells.allTextContents()).map((text) => {
    const firstLine = text.split('\n')[0].trim();
    return firstLine || '-';
  });
  const uiMerchants = Array.from(new Set(merchantTexts)).sort();
  expect(uiMerchants.length).toBeGreaterThan(1);
  const hasNonBauhaus = uiMerchants.some((name) => name !== 'BAUHAUS' && name !== '-');
  expect(hasNonBauhaus).toBeTruthy();

  const fcCard = page.locator('.card', { has: page.getByRole('heading', { name: 'FirstCard-transaktioner' }) });
  const fcDateCells = fcCard.locator('tbody tr td:nth-child(2)');
  await expect(fcDateCells.first()).toBeVisible({ timeout: 30000 });
  const fcDates = await fcDateCells.allTextContents();
  for (const text of fcDates) {
    expect(text).toContain('2025-06');
  }
});
