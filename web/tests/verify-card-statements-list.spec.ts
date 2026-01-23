import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1440,
    width: 3440
  }
});

test.describe('Card Statements List', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByRole('textbox', { name: 'Lösenord' }).click();
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Navigate to CompanyCard page
    await page.getByRole('button', { name: 'Kortmatchning' }).click();

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
  });

  test('should display a list of card statements', async ({ page }) => {
    // Check for the main heading
    await expect(page.getByRole('heading', { name: 'Kontoutdrag' })).toBeVisible();

    // Wait for the table to be populated
    await page.waitForSelector('table.min-w-full');

    // Check that the "no statements found" message is not visible
    await expect(page.getByText('Inga kontoutdrag hittades.')).not.toBeVisible();

    // Check that there is at least one row in the table body
    const tableBody = page.locator('table.min-w-full > tbody');
    const rows = tableBody.locator('tr');
    await expect(rows).toHaveCountGreaterThan(0);

    // Check for a known column header
    await expect(page.getByRole('cell', { name: 'Kort' })).toBeVisible();
  });

  test('should update Senast uppdaterad after Återuppta fakturaimport', async ({ page }) => {
    await page.waitForSelector('table.min-w-full');

    const rows = page.locator('table.min-w-full > tbody > tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    const firstRow = rows.first();
    const fakturaLine = await firstRow
      .locator('div')
      .filter({ hasText: /Fakturanummer:/ })
      .first()
      .innerText();
    const invoiceRef = fakturaLine.split(':').pop()?.trim() ?? '';
    expect(invoiceRef.length).toBeGreaterThan(0);

    const findRowByInvoice = () =>
      page.locator('table.min-w-full > tbody > tr').filter({ hasText: invoiceRef }).first();

    const initialTimestamp = (await findRowByInvoice().locator('td').nth(9).innerText()).trim();

    await findRowByInvoice().getByRole('button', { name: /Återuppta fakturaimport/i }).click();
    await page.waitForTimeout(1500);

    await page.getByRole('button', { name: 'Uppdatera' }).click();
    await page.waitForLoadState('networkidle');
    await expect(findRowByInvoice()).toBeVisible();

    const refreshedTimestamp = (await findRowByInvoice().locator('td').nth(9).innerText()).trim();
    expect(refreshedTimestamp).not.toBe('');
    expect(refreshedTimestamp).not.toBe(initialTimestamp);
  });

  test('invoice lines persist currency fields after restart @fc-currency', async ({ page }) => {
    test.setTimeout(180000);
    await page.waitForSelector('table.min-w-full');

    const statementId = await page.evaluate(async () => {
      const res = await fetch('/ai/api/reconciliation/firstcard/statements', {
        method: 'GET',
        credentials: 'include',
      });
      if (!res.ok) return null;
      const data = await res.json();
      const statements = Array.isArray(data?.statements) ? data.statements : [];
      const first = statements[0];
      return typeof first?.id === 'string' ? first.id : null;
    });
    expect(statementId).toBeTruthy();

    const restartOk = await page.evaluate(async (invoiceId) => {
      const res = await fetch(`/ai/api/reconciliation/firstcard/statements/${invoiceId}/restart`, {
        method: 'POST',
        credentials: 'include',
      });
      return res.ok;
    }, statementId);
    expect(restartOk).toBeTruthy();

    // Refresh view so that backend state is consistent for follow-up reads.
    await page.getByRole('button', { name: 'Uppdatera' }).click();
    await page.waitForLoadState('networkidle');

    const pollStart = Date.now();
    const pollTimeoutMs = 120000;
    const pollIntervalMs = 2000;

    let pollResult: {
      lineCount: number;
      hasAmountSek: boolean;
      hasCurrencyOriginal: boolean;
      hasFxLine: boolean;
      fxHasFields: boolean;
    } | null = null;

    while (Date.now() - pollStart < pollTimeoutMs) {
      pollResult = await page.evaluate(async (invoiceId) => {
        const res = await fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}`, {
          method: 'GET',
          credentials: 'include',
        });
        if (!res.ok) return null;
        const data = await res.json();
        const lines = Array.isArray(data?.lines) ? data.lines : [];
        return {
          lineCount: lines.length,
          hasAmountSek: lines.some((l) => typeof l?.amount_sek === 'number'),
          hasCurrencyOriginal: lines.some(
            (l) => typeof l?.currency_original === 'string' && l.currency_original.trim(),
          ),
          hasFxLine: lines.some(
            (l) =>
              typeof l?.currency_original === 'string' &&
              l.currency_original.trim().toUpperCase() !== 'SEK',
          ),
          fxHasFields: lines.some(
            (l) =>
              typeof l?.currency_original === 'string' &&
              l.currency_original.trim().toUpperCase() !== 'SEK' &&
              typeof l?.amount_original === 'number' &&
              typeof l?.exchange_rate === 'number' &&
              typeof l?.amount_sek === 'number',
          ),
        };
      }, statementId);

      if (
        pollResult &&
        pollResult.lineCount > 0 &&
        pollResult.hasAmountSek &&
        pollResult.hasCurrencyOriginal &&
        (!pollResult.hasFxLine || pollResult.fxHasFields)
      ) {
        break;
      }

      await page.waitForTimeout(pollIntervalMs);
    }

    expect(pollResult).not.toBeNull();
    if (!pollResult) return;

    expect(pollResult.lineCount).toBeGreaterThan(0);
    expect(pollResult.hasAmountSek).toBeTruthy();
    expect(pollResult.hasCurrencyOriginal).toBeTruthy();

    // Foreign currency rows may not exist on every statement, but when they do, all FX fields must be present.
    if (pollResult.hasFxLine) {
      expect(pollResult.fxHasFields).toBeTruthy();
    }
  });
});
