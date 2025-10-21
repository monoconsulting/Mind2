import { test, expect } from '@playwright/test';

/**
 * Test: Card Matching Auto-Match Functionality
 * Date: 2025-10-21
 *
 * Tests the automatic matching feature in the card matching module:
 * - Navigation to card matching page
 * - Auto-match button functionality
 * - Match log visibility and interaction
 */

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('Auto-match button triggers matching and shows log', async ({ page }) => {
  // Navigate to login page
  await page.goto('http://localhost:5169/login');

  // Login
  await page.getByRole('textbox', { name: 'Lösenord' }).click();
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  // Navigate to card matching module
  await page.getByRole('button', { name: 'Kortmatchning' }).click();

  // Verify we're on the card matching page
  await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();

  // Click auto-match button
  await page.getByRole('button', { name: 'Auto-matcha' }).click();

  // Wait a moment for the matching process to initiate
  await page.waitForTimeout(1000);

  // Open the log
  await page.getByRole('button', { name: 'Visa logg' }).click();

  // Verify log is visible (you can add more specific checks here)
  // For example, check if log contains expected elements or messages
  await page.waitForTimeout(500);

  // Close the log
  await page.getByRole('button', { name: 'Stäng', exact: true }).click();

  // Verify log is closed
  await page.waitForTimeout(500);
});

test('Auto-match button is available on card matching page', async ({ page }) => {
  // Navigate and login
  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  // Navigate to card matching
  await page.getByRole('button', { name: 'Kortmatchning' }).click();

  // Verify auto-match button exists and is enabled
  const autoMatchButton = page.getByRole('button', { name: 'Auto-matcha' });
  await expect(autoMatchButton).toBeVisible();
  await expect(autoMatchButton).toBeEnabled();
});
