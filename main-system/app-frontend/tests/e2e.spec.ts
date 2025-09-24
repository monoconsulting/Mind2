import { test, expect } from '@playwright/test';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'adminadmin';

async function login(page) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Logga in' })).toBeVisible();
  await page.fill('#u', 'admin');
  await page.fill('#p', ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL('**/'),
    page.getByRole('button', { name: 'Logga in' }).click(),
  ]);
  await expect(page.getByRole('button', { name: 'Testa API' })).toBeVisible();
}

async function ensureApiHealthy(page) {
  const res = await page.request.get('http://localhost:8008/ai/api/health');
  expect(res.ok()).toBeTruthy();
}

test.beforeAll(async ({ request }) => {
  const res = await request.get('http://localhost:8008/ai/api/health');
  expect(res.ok()).toBeTruthy();
});

test('login and navigate menu', async ({ page }) => {
  await ensureApiHealthy(page);
  await login(page);

  await page.getByRole('button', { name: 'Testa API' }).click();
  await expect(page.locator('#out')).toContainText('200');

  await page.getByRole('button', { name: 'Kvitton' }).click();
  await expect(page.getByRole('heading', { name: 'Kvitton' })).toBeVisible();
  await expect(page.locator('#status')).toContainText('Hämtade');

  const rows = page.locator('#tbl tr');
  const rowCount = await rows.count();
  expect(rowCount).toBeGreaterThan(0);

  await page.selectOption('#page-size', '10');
  await expect(page.locator('#status')).toContainText('Hämtade');

  await page.getByRole('button', { name: 'Översikt' }).click();
  await expect(page.getByRole('button', { name: 'Testa API' })).toBeVisible();

  await page.getByRole('button', { name: 'Logga ut' }).click();
  await expect(page.getByRole('heading', { name: 'Logga in' })).toBeVisible();
});


