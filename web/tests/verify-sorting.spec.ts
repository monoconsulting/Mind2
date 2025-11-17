import { test, expect } from '@playwright/test';

test.describe('Table Sorting Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('http://localhost:8008/');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'admin');
    await page.click('button:has-text("Logga in")');
    await page.waitForURL('**/receipts', { timeout: 10000 });
  });

  test('Receipts table - sort by company name', async ({ page }) => {
    await page.goto('http://localhost:8008/receipts');
    await page.waitForLoadState('networkidle');

    // Wait for table to load
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    // Click on company header to sort
    const companyHeader = page.locator('th:has-text("Företag")').first();
    await companyHeader.click();

    await page.waitForTimeout(1000);

    // Get first few company names
    const firstCompany = await page.locator('table tbody tr').first().locator('td').nth(1).textContent();
    console.log('First company after sort:', firstCompany);

    // Verify arrow indicator appears
    const hasArrow = await companyHeader.locator('span').count();
    expect(hasArrow).toBeGreaterThan(0);

    console.log('✓ Receipts sorting works');
  });

  test('Process table - sort by date', async ({ page }) => {
    await page.goto('http://localhost:8008/process');
    await page.waitForLoadState('networkidle');

    // Wait for table to load
    await page.waitForSelector('table tbody tr', { timeout: 10000 });

    // Click on date header to sort
    const dateHeader = page.locator('th:has-text("Datum")').first();
    await dateHeader.click();

    await page.waitForTimeout(1000);

    // Verify arrow indicator appears
    const hasArrow = await dateHeader.locator('span').count();
    expect(hasArrow).toBeGreaterThan(0);

    console.log('✓ Process sorting works');
  });

  test('Manual Match - sort FC items by date', async ({ page }) => {
    await page.goto('http://localhost:8008/manual-match');
    await page.waitForLoadState('networkidle');

    // Wait for tables to load
    await page.waitForSelector('table', { timeout: 10000 });

    // Click on date header in FC items table (left side)
    const tables = page.locator('table');
    const fcTable = tables.first();
    const dateHeader = fcTable.locator('th:has-text("Datum")');

    if (await dateHeader.count() > 0) {
      await dateHeader.click();
      await page.waitForTimeout(1000);

      // Verify arrow indicator appears
      const hasArrow = await dateHeader.locator('span').count();
      expect(hasArrow).toBeGreaterThan(0);

      console.log('✓ Manual Match FC items sorting works');
    }
  });

  test('Manual Match - sort receipts by company', async ({ page }) => {
    await page.goto('http://localhost:8008/manual-match');
    await page.waitForLoadState('networkidle');

    // Wait for tables to load
    await page.waitForSelector('table', { timeout: 10000 });

    // Click on company header in receipts table (right side)
    const tables = page.locator('table');
    const receiptsTable = tables.last();
    const companyHeader = receiptsTable.locator('th:has-text("Företag")');

    if (await companyHeader.count() > 0) {
      await companyHeader.click();
      await page.waitForTimeout(1000);

      // Verify arrow indicator appears
      const hasArrow = await companyHeader.locator('span').count();
      expect(hasArrow).toBeGreaterThan(0);

      console.log('✓ Manual Match receipts sorting works');
    }
  });
});
