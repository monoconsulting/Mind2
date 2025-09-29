import { test, expect } from '@playwright/test';

const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'adminadmin';

const capture = async (page, name) => {
  const filePath = test.info().outputPath(`${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  await test.info().attach(name, { path: filePath, contentType: 'image/png' });
};

test('svenska menyer och sidor utan mockad data', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'networkidle' });
  await expect(page.getByRole('heading', { name: 'Logga in' })).toBeVisible();
  await capture(page, 'login');

  await page.fill('#login-username', 'admin');
  await page.fill('#login-password', ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL('**/', { waitUntil: 'networkidle' }),
    page.getByRole('button', { name: 'Logga in' }).click(),
  ]);

  const title = page.locator('.page-title');
  await expect(title).toHaveText('Översikt');
  await capture(page, 'oversikt');

  const sections = [
    { button: 'Kvitton', title: 'Kvitton', screenshot: 'kvitton' },
    { button: 'Kortmatchning', title: 'Kortmatchning', screenshot: 'kortmatchning' },
    { button: 'Analys', title: 'Analys', screenshot: 'analys' },
    { button: 'Export', title: 'Export', screenshot: 'export' },
    { button: 'Användare', title: 'Användare', screenshot: 'anvandare' },
  ];

  for (const section of sections) {
    await page.getByRole('button', { name: section.button, exact: true }).click();
    await expect(title).toHaveText(section.title);
    await capture(page, section.screenshot);
  }
});
