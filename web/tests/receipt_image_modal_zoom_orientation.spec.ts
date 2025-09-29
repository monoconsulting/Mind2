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
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.waitForTimeout(12000);
  await page.getByRole('button', { name: 'Förhandsgranska kvitto 0ac43f53-6dd9-4e92-b3dd-538716b31108' }).click();

  // Vänta på att bilden laddas
  await page.waitForSelector('.preview-image', { state: 'visible', timeout: 30000 });

  await page.getByRole('dialog', { name: 'Förhandsgranska kvitto' }).locator('img').click();
  await page.getByRole('dialog', { name: 'Förhandsgranska kvitto' }).locator('img').click();
  await page.getByRole('dialog', { name: 'Förhandsgranska kvitto' }).locator('img').click();
  await page.waitForTimeout(2000);
  await expect(page).toHaveScreenshot('001.png');
});
