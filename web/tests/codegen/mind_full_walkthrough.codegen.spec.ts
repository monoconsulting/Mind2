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
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Översikt' }).click();
  await page.getByRole('button', { name: 'Testa API-anslutning' }).click();
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByRole('button', { name: 'Förhandsgranska kvitto de5353e1-23bf-4b7f-8197-236b2efab96d' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('button', { name: 'Stäng förhandsgranskning' }).click();
  await page.getByRole('row', { name: 'Förhandsgranska kvitto d0918000-b9b1-4c01-b6b9-8ddcee4a8e5c - Okänt bolag' }).locator('button').nth(3).click();
  await page.getByRole('cell', { name: 'Bearbetas' }).click();
  await page.getByRole('cell', { name: 'Bearbetas' }).click();
  await page.getByRole('cell', { name: 'Bearbetas' }).click();
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.locator('td:nth-child(9)').first().click();
  await page.locator('tr:nth-child(2) > td:nth-child(9)').click();
  await page.locator('.font-mono').first().click();
  await page.locator('tr:nth-child(2) > .font-mono').click();
  await page.locator('tr:nth-child(3) > .font-mono').click();
  await page.getByRole('button', { name: 'Förhandsgranska kvitto 2c4bf48f-1c8e-4f8c-91aa-5a99db9f7ca9' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('dialog', { name: 'Förhandsgranskning kvitto' }).click();
  await page.getByRole('button', { name: 'Stäng förhandsgranskning' }).click();
  await page.getByRole('row', { name: 'Förhandsgranska kvitto 2c4bf48f-1c8e-4f8c-91aa-5a99db9f7ca9 Smart Psykiatri i' }).getByRole('button').nth(1).click();
  await page.getByRole('dialog', { name: 'Karta för kvitto 2c4bf48f-' }).click();
  await page.getByRole('button', { name: 'Stäng karta' }).click();
  await page.getByRole('row', { name: 'Förhandsgranska kvitto 2c4bf48f-1c8e-4f8c-91aa-5a99db9f7ca9 Smart Psykiatri i' }).getByRole('button').nth(3).click();
  await page.getByRole('button', { name: 'Ladda om' }).click();
  await page.getByRole('button', { name: 'Stäng', exact: true }).click();
  await page.getByRole('button', { name: 'Kortmatchning' }).click();
  await page.getByRole('cell', { name: 'Ej bearbetad' }).first().click();
  await page.getByRole('cell', { name: '83%' }).click();
  await page.getByRole('cell', { name: '-11-08 09:58' }).click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).getByRole('button').first().click();
  await page.getByRole('heading', { name: 'Workflowk rning' }).click();
  await page.getByText('WF3_FIRSTCARD_INVOICE -').first().click();
  await page.getByText('K lla: kortmatchning_restart', { exact: true }).click();
  await page.getByText('P g r').click();
  await page.getByRole('button', { name: 'Stäng logg' }).click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).getByRole('button').nth(2).click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('button', { name: 'Uppdatera' }).click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('row', { name: 'First Card L646 Fakturanummer: 2533590631 Period: 2025-01-02 - 2025-01-22' }).locator('span').click();
  await page.getByRole('cell', { name: 'Under bearbetning' }).locator('span').click();
  await page.getByRole('cell', { name: 'Under bearbetning' }).locator('span').click();
  await page.getByRole('cell', { name: 'Under bearbetning' }).locator('span').click();
  await page.getByRole('button', { name: 'AI', exact: true }).click();
  await page.getByRole('button', { name: 'LLM-konfiguration' }).click();
  await page.getByRole('button', { name: 'Systemprompter' }).click();
  await page.getByRole('button', { name: 'Export' }).click();
  await page.getByRole('button', { name: 'Användare' }).click();
  await page.getByText('Systemansvarig').click();
  await page.getByText('Administratör').click();
  await page.getByRole('button', { name: 'Logga ut' }).click();
});