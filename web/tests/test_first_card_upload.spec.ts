import { test, expect } from '@playwright/test';

test('test first card upload - basic check', async ({ page }) => {
  // Go to login page
  await page.goto('http://localhost:5169/login');

  // Take screenshot to see current state
  await page.screenshot({ path: 'test-results/login-page.png', fullPage: true });

  // Try to login
  await page.getByRole('textbox', { name: 'Lösenord' }).click();
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  // Wait for navigation
  await page.waitForURL('**/dashboard');

  // Take screenshot after login
  await page.screenshot({ path: 'test-results/dashboard.png', fullPage: true });

  // Try to find Kortmatchning button
  const kortmatchningButton = page.getByRole('button', { name: 'Kortmatchning' });
  if (await kortmatchningButton.isVisible()) {
    await kortmatchningButton.click();

    // Take screenshot of kortmatchning page
    await page.screenshot({ path: 'test-results/kortmatchning.png', fullPage: true });

    // Try to find Ladda upp utdrag button
    const uploadButton = page.getByRole('button', { name: 'Ladda upp utdrag' });
    if (await uploadButton.isVisible()) {
      await uploadButton.click();

      // Take screenshot of upload dialog
      await page.screenshot({ path: 'test-results/upload-dialog.png', fullPage: true });

      console.log('Upload dialog opened successfully');
    } else {
      console.log('Ladda upp utdrag button not found');
    }
  } else {
    console.log('Kortmatchning button not found');
  }
});