import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  await page.goto('http://localhost:8008/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).click();
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.getByRole('button', { name: 'Förhandsgranska kvitto cc0ef1c8-a92f-4f9a-b6a8-6f5368cb34c9' }).click();
  await page.getByRole('button', { name: 'Stäng', exact: true }).click();
  await page.getByRole('button', { name: 'Förhandsgranska kvitto 4b396afc-0e9b-4021-ad41-8119651bed92' }).click();
  await page.screenshot({ path: 'web/tests/screenshots/receipt_preview.png' });
});