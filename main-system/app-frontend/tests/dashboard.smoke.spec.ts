import { test, expect } from '@playwright/test';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'DEGER43179fors!';

test('shows dashboard after login', async ({ page }) => {
  // Inject a token to bypass backend login in smoke
  await page.addInitScript(() => {
    window.localStorage.setItem('mind.jwt', 'smoke-token')
  })
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Testa API' })).toBeVisible();
});

