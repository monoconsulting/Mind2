import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 1200,
    width: 1900
  }
});

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function formatCurrencySvSe(value: number, currency: string): string {
  const code = currency?.trim()?.toUpperCase?.() ? currency.trim().toUpperCase() : 'SEK';
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: code,
      minimumFractionDigits: 2
    }).format(value);
  } catch {
    return `${value.toFixed(2)} ${code}`;
  }
}

test('receipts/process use original-currency display amounts', async ({ page }) => {
  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();

  await expect(page.getByRole('button', { name: 'Kvitton' })).toBeVisible();

  // API contract: list endpoint must include original-currency display fields (required for UI tables)
  const apiRes = await page.request.get(
    'http://localhost:5169/ai/api/receipts?page=1&page_size=1000&include_credit=0&file_type=receipt'
  );
  expect(apiRes.ok()).toBeTruthy();
  const payload = await apiRes.json();
  const items = Array.isArray(payload?.items) ? payload.items : [];
  expect(items.length).toBeGreaterThan(0);
  expect(items[0]).toHaveProperty('currency');
  expect(items[0]).toHaveProperty('gross_amount_display');
  expect(items[0]).toHaveProperty('net_amount_display');

  const foreign = items.find(
    (r: any) =>
      r?.currency &&
      r.currency !== 'SEK' &&
      typeof r.gross_amount_display === 'number' &&
      typeof r.merchant === 'string' &&
      r.merchant.trim()
  );
  expect(foreign, 'No foreign-currency receipt with gross_amount_display + merchant found in API list').toBeTruthy();

  const receiptId = foreign.id as string;
  const merchant = foreign.merchant as string;
  const currency = foreign.currency as string;
  const expectedGross = formatCurrencySvSe(foreign.gross_amount_display as number, currency);
  const expectedNet =
    typeof foreign.net_amount_display === 'number'
      ? formatCurrencySvSe(foreign.net_amount_display as number, currency)
      : null;

  const expectedGrossRe = new RegExp(escapeRegExp(expectedGross).replace(/\\s+/g, '\\\\s+'));
  const expectedNetRe = expectedNet ? new RegExp(escapeRegExp(expectedNet).replace(/\\s+/g, '\\\\s+')) : null;

  // Receipts table: display must use *_display + currency (not SEK conversion fields)
  await page.getByRole('button', { name: 'Kvitton' }).click();
  await page.getByPlaceholder('Sök efter företag, filnamn eller belopp').fill(merchant);
  await page.getByRole('button', { name: 'Sök' }).click();

  const receiptsTable = page.locator('table.table-dark').first();
  await expect(receiptsTable).toContainText(merchant);
  await expect(receiptsTable).toContainText(expectedGrossRe);
  if (expectedNetRe) {
    await expect(receiptsTable).toContainText(expectedNetRe);
  }

  // Process table: same rule (search by id to ensure the row is in view)
  await page.getByRole('button', { name: 'Process' }).click();
  await page.getByPlaceholder('Sök efter företag, filnamn eller belopp').fill(merchant);
  await page.getByRole('button', { name: 'Sök' }).click();

  const processTable = page.locator('table.table-dark').first();
  await expect(processTable).toContainText(merchant);
  await expect(processTable).toContainText(expectedGrossRe);
  if (expectedNetRe) {
    await expect(processTable).toContainText(expectedNetRe);
  }
});
