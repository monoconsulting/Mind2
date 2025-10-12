import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test('Verify PDF files are filtered out from Kvitton and Process views', async ({ page }) => {
  // Login
  await page.goto('http://localhost:8008/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  // Test Kvitton view
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.waitForTimeout(1000);

  // Check that the count shows 28 total (not 41)
  const kvittonText = await page.locator('div').filter({ hasText: /Visar.*av.*kvitton/ }).first().textContent();
  console.log('Kvitton text:', kvittonText);
  expect(kvittonText).toMatch(/28 kvitton/);

  // Verify no pure .pdf files are visible in the table
  // Note: Files like "file.pdf-page-0001.png" are OK (converted PDF pages)
  // We only want to exclude files that end with ".pdf" (no "-page-" suffix)
  const kvittonRows = await page.locator('table tbody tr').all();
  console.log(`Kvitton: Found ${kvittonRows.length} rows`);

  for (const row of kvittonRows) {
    const text = await row.textContent();
    if (text) {
      const lowerText = text.toLowerCase();
      // Check that no row contains a filename ending with .pdf (without -page- suffix)
      const hasPurePdf = lowerText.match(/\w+\.pdf[^-]/);
      expect(hasPurePdf).toBeNull();
    }
  }

  // Test Process view
  await page.getByRole('button', { name: 'Process' }).click();
  await page.waitForTimeout(2000);

  // Check that the count shows 28 total (not 41)
  const processText = await page.locator('div').filter({ hasText: /Visar.*av.*kvitton/ }).first().textContent();
  console.log('Process text:', processText);
  expect(processText).toMatch(/28 kvitton/);

  // Verify no pure .pdf files are visible in the table
  // Note: Files like "file.pdf-page-0001.png" are OK (converted PDF pages)
  // We only want to exclude files that end with ".pdf" (no "-page-" suffix)
  const processRows = await page.locator('table tbody tr').all();
  console.log(`Process: Found ${processRows.length} rows`);

  for (const row of processRows) {
    const text = await row.textContent();
    if (text) {
      const lowerText = text.toLowerCase();
      // Check that no row contains a filename ending with .pdf (without -page- suffix)
      const hasPurePdf = lowerText.match(/\w+\.pdf[^-]/);
      expect(hasPurePdf).toBeNull();
    }
  }

  console.log('✓ PDF filtering verified successfully in both views');
});
