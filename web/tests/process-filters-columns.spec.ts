import { test, expect } from '@playwright/test';

test.describe('Process Page - New Filters and Columns @process', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to Process page
    await page.goto('/process');
    // Wait for page to load
    await page.waitForSelector('h1:has-text("Process")', { timeout: 10000 });
  });

  test('should display 4 new columns in table header', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table.table-dark');

    // Verify new column headers exist
    await expect(page.locator('th:has-text("Utgiftstyp")')).toBeVisible();
    await expect(page.locator('th:has-text("Betalningstyp")')).toBeVisible();
    await expect(page.locator('th:has-text("Uppladdningsdatum")')).toBeVisible();
    await expect(page.locator('th:has-text("Sista 4")')).toBeVisible();
  });

  test('should display new columns as sortable', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table.table-dark');

    // Verify columns are clickable (sortable)
    const utgiftstypHeader = page.locator('th:has-text("Utgiftstyp")');
    const betalningsTypHeader = page.locator('th:has-text("Betalningstyp")');
    const uppladdningsdatumHeader = page.locator('th:has-text("Uppladdningsdatum")');

    await expect(utgiftstypHeader).toHaveClass(/cursor-pointer/);
    await expect(betalningsTypHeader).toHaveClass(/cursor-pointer/);
    await expect(uppladdningsdatumHeader).toHaveClass(/cursor-pointer/);
  });

  test('should display filter section above table', async ({ page }) => {
    // Verify filter card exists
    await expect(page.locator('.card').filter({ hasText: 'Filter' }).first()).toBeVisible();

    // Verify filter card is positioned before the receipts table
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const receiptsCard = page.locator('.card').filter({ hasText: 'Alla kvitton' });

    const filterBox = await filterCard.boundingBox();
    const receiptsBox = await receiptsCard.boundingBox();

    // Filter card should be above receipts card
    expect(filterBox!.y).toBeLessThan(receiptsBox!.y);
  });

  test('should display all 5 filter dropdowns in first row', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();

    // Verify all 5 filters in first row
    await expect(filterCard.locator('label:has-text("Status")')).toBeVisible();
    await expect(filterCard.locator('label:has-text("Upload")')).toBeVisible();
    await expect(filterCard.locator('label:has-text("Dokumenttyp")')).toBeVisible();
    await expect(filterCard.locator('label:has-text("Utgiftstyp")')).toBeVisible();
    await expect(filterCard.locator('label:has-text("Betalningstyp")')).toBeVisible();
  });

  test('should display year and month filters in second row', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();

    // Verify year and month filters
    await expect(filterCard.locator('label:has-text("År")')).toBeVisible();
    await expect(filterCard.locator('label:has-text("Månad")')).toBeVisible();
  });

  test('should have current year as default in year filter', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const yearSelect = filterCard.locator('label:has-text("År")').locator('select');

    const currentYear = new Date().getFullYear().toString();
    await expect(yearSelect).toHaveValue(currentYear);
  });

  test('should have "Alla månader" as default in month filter', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const monthSelect = filterCard.locator('label:has-text("Månad")').locator('select');

    await expect(monthSelect).toHaveValue('');

    // Verify first option is "Alla månader"
    const firstOption = monthSelect.locator('option').first();
    await expect(firstOption).toHaveText('Alla månader');
  });

  test('should filter by status', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const statusSelect = filterCard.locator('label:has-text("Status")').locator('select');

    // Select a status
    await statusSelect.selectOption('passed');

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify URL contains status parameter
    expect(page.url()).toContain('status=passed');
  });

  test('should filter by upload source', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const uploadSelect = filterCard.locator('label:has-text("Upload")').locator('select');

    // Select FTP
    await uploadSelect.selectOption('ftp');

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify data in table shows FTP uploads
    const firstUploadCell = page.locator('tbody tr').first().locator('td').nth(3);
    await expect(firstUploadCell).toContainText('FTP');
  });

  test('should filter by document type', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const docTypeSelect = filterCard.locator('label:has-text("Dokumenttyp")').locator('select');

    // Select receipt
    await docTypeSelect.selectOption('receipt');

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify URL contains file_type parameter
    expect(page.url()).toContain('file_type=receipt');
  });

  test('should filter by expense type', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const expenseTypeSelect = filterCard.locator('label:has-text("Utgiftstyp")').locator('select');

    // Select mat
    await expenseTypeSelect.selectOption('mat');

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify URL contains expense_type parameter
    expect(page.url()).toContain('expense_type=mat');
  });

  test('should filter by payment type', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const paymentTypeSelect = filterCard.locator('label:has-text("Betalningstyp")').locator('select');

    // Select card
    await paymentTypeSelect.selectOption('card');

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify URL contains payment_type parameter
    expect(page.url()).toContain('payment_type=card');
  });

  test('should filter by year', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const yearSelect = filterCard.locator('label:has-text("År")').locator('select');

    const lastYear = (new Date().getFullYear() - 1).toString();
    await yearSelect.selectOption(lastYear);

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify URL contains upload_from and upload_to parameters
    expect(page.url()).toContain('upload_from=');
    expect(page.url()).toContain('upload_to=');
  });

  test('should filter by year and month combined', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();
    const yearSelect = filterCard.locator('label:has-text("År")').locator('select');
    const monthSelect = filterCard.locator('label:has-text("Månad")').locator('select');

    // Select year and month
    await yearSelect.selectOption('2024');
    await monthSelect.selectOption('05'); // Maj

    // Wait for table to reload
    await page.waitForTimeout(1000);

    // Verify URL contains correct date range
    expect(page.url()).toContain('upload_from=2024-05-01');
    expect(page.url()).toContain('upload_to=2024-05-31');
  });

  test('should reset all filters when clicking "Rensa filter"', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();

    // Set multiple filters
    await filterCard.locator('label:has-text("Status")').locator('select').selectOption('passed');
    await filterCard.locator('label:has-text("Utgiftstyp")').locator('select').selectOption('mat');

    // Wait for filters to apply
    await page.waitForTimeout(500);

    // Click reset button
    await filterCard.locator('button:has-text("Rensa filter")').click();

    // Wait for reset
    await page.waitForTimeout(500);

    // Verify filters are reset
    const statusSelect = filterCard.locator('label:has-text("Status")').locator('select');
    const expenseTypeSelect = filterCard.locator('label:has-text("Utgiftstyp")').locator('select');

    await expect(statusSelect).toHaveValue('');
    await expect(expenseTypeSelect).toHaveValue('');
  });

  test('should display data in new columns when receipts exist', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('tbody tr');

    // Check if receipts exist
    const rowCount = await page.locator('tbody tr').count();

    if (rowCount > 0) {
      const firstRow = page.locator('tbody tr').first();

      // Get cells by index (after Upload which is index 3)
      // Index 4: Utgiftstyp
      // Index 5: Betalningstyp
      // Index 6: Uppladdningsdatum
      // Index 7: Sista 4

      const utgiftstypCell = firstRow.locator('td').nth(4);
      const betalningTypCell = firstRow.locator('td').nth(5);
      const uppladdningsdatumCell = firstRow.locator('td').nth(6);
      const sista4Cell = firstRow.locator('td').nth(7);

      // Verify cells exist and have content (or '-' for empty)
      await expect(utgiftstypCell).toBeVisible();
      await expect(betalningTypCell).toBeVisible();
      await expect(uppladdningsdatumCell).toBeVisible();
      await expect(sista4Cell).toBeVisible();
    }
  });

  test('should sort by expense type when clicking column header', async ({ page }) => {
    const expenseTypeHeader = page.locator('th:has-text("Utgiftstyp")');

    // Click to sort
    await expenseTypeHeader.click();
    await page.waitForTimeout(500);

    // Verify sort indicator appears
    await expect(expenseTypeHeader).toContainText(/▲|▼/);

    // Verify URL contains sort parameters
    expect(page.url()).toContain('sort_by=expense_type');
  });

  test('should sort by payment type when clicking column header', async ({ page }) => {
    const paymentTypeHeader = page.locator('th:has-text("Betalningstyp")');

    // Click to sort
    await paymentTypeHeader.click();
    await page.waitForTimeout(500);

    // Verify sort indicator appears
    await expect(paymentTypeHeader).toContainText(/▲|▼/);

    // Verify URL contains sort parameters
    expect(page.url()).toContain('sort_by=payment_type');
  });

  test('should sort by upload date when clicking column header', async ({ page }) => {
    const uploadDateHeader = page.locator('th:has-text("Uppladdningsdatum")');

    // Click to sort
    await uploadDateHeader.click();
    await page.waitForTimeout(500);

    // Verify sort indicator appears
    await expect(uploadDateHeader).toContainText(/▲|▼/);

    // Verify URL contains sort parameters
    expect(page.url()).toContain('sort_by=uploaded_at');
  });

  test('should combine multiple filters', async ({ page }) => {
    const filterCard = page.locator('.card').filter({ hasText: 'Filter' }).first();

    // Set multiple filters
    await filterCard.locator('label:has-text("Status")').locator('select').selectOption('passed');
    await filterCard.locator('label:has-text("Dokumenttyp")').locator('select').selectOption('receipt');
    await filterCard.locator('label:has-text("Utgiftstyp")').locator('select').selectOption('mat');

    // Wait for filters to apply
    await page.waitForTimeout(1000);

    // Verify URL contains all filter parameters
    expect(page.url()).toContain('status=passed');
    expect(page.url()).toContain('file_type=receipt');
    expect(page.url()).toContain('expense_type=mat');
  });

  test('should have correct column count (17 total)', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table.table-dark');

    // Count header columns
    const headerCount = await page.locator('thead th').count();

    // Should be 17 columns total (13 original + 4 new)
    expect(headerCount).toBe(17);
  });
});
