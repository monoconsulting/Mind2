import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('test', async ({ page }) => {
  await page.goto('http://localhost:8008/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).click();
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByRole('button', { name: 'Kvitton' }).press('ArrowRight');
  await page.getByText('MMind AdminÖ').click();
  await page.locator('tr:nth-child(17) > .font-mono').click({
    button: 'middle'
  });
  await page.locator('div').filter({ hasText: /^Visar 25 av 28 kvitton$/ }).first().click({
    button: 'middle'
  });
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('cell', { name: 'Title ID: 9530521e-2a3d-40d7-' }).click();
  await page.locator('tr:nth-child(13) > td:nth-child(5)').click();
});