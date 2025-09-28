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
  await page.getByRole('button', { name: 'AI' }).click();
  await expect(page).toHaveScreenshot('AI001.png');
  await page.getByRole('button', { name: 'LLM-konfiguration' }).click();
  await expect(page).toHaveScreenshot('AI002.png');
  await page.getByRole('button', { name: 'Lägg till leverantör' }).click();
  await expect(page).toHaveScreenshot('AI003.png');
  await page.getByRole('textbox', { name: 'Min OpenAI-konfiguration...' }).click();
  await expect(page).toHaveScreenshot('AI004.png');
  await page.getByRole('textbox', { name: 'Min OpenAI-konfiguration...' }).fill('test');
  await page.getByRole('textbox', { name: 'sk-' }).click();
  await page.getByRole('textbox', { name: 'sk-' }).fill('skasdfjowiejfsldkjfoweifjslkdjf');
  await page.getByRole('checkbox', { name: 'Aktiverad' }).check();
  await page.getByRole('button', { name: 'Spara' }).click();
  await expect(page).toHaveScreenshot('AI005.png');
});