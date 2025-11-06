import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('test', async ({ page }) => {
  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Användarnamn' }).click();
  await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
  await page.getByRole('textbox', { name: 'Användarnamn' }).press('Tab');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('textbox', { name: 'Lösenord' }).press('Enter');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('textbox', { name: 'Lösenord' }).press('Enter');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.getByRole('button', { name: 'Kortmatchning' }).click();
  await page.getByRole('button', { name: 'AI' }).click();
  await page.getByRole('button', { name: 'LLM-konfiguration' }).click();
  await page.getByRole('button', { name: 'Export' }).click();
  await page.getByRole('button', { name: 'Användare' }).click();
  await page.getByText('Administratör').click();
  await page.getByText('A', { exact: true }).click();
  await page.getByRole('main').click();
});