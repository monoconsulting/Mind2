import { test as setup, expect } from '@playwright/test';

const authFile = 'test-reports/.auth/admin.json';

setup('authenticate as admin', async ({ page }) => {
  await page.goto('/login');
  const usernameInput = page.getByLabel('Användarnamn');
  const passwordInput = page.getByLabel('Lösenord');

  if (await usernameInput.isVisible().catch(() => false)) {
    await usernameInput.fill('admin');
  }
  if (await passwordInput.isVisible().catch(() => false)) {
    await passwordInput.fill('adminadmin');
  }

  const loginBtn = page.getByRole('button', { name: /^Logga in$/ });
  await expect(loginBtn).toBeVisible();
  await Promise.all([
    page.waitForURL((url: URL) => !url.pathname.endsWith('/login'), { timeout: 15000 }),
    loginBtn.click(),
  ]);

  await page.context().storageState({ path: authFile });
});
