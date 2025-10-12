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
  await page.getByRole('textbox', { name: 'Lösenord' }).click();
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('button', { name: 'AI', exact: true }).click();
  await page.getByRole('button', { name: 'Öppna i modal' }).first().click();
  await page.goto('http://localhost:8008/');
  await page.getByRole('button', { name: 'AI' }).click();
  await page.getByRole('button', { name: 'Öppna i modal' }).nth(2).click();

});