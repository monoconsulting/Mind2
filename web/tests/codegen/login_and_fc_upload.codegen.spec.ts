import { test, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { randomUUID } from 'crypto';

test.use({
  viewport: {
    height: 1440,
    width: 3440,
  },
});

function createUniquePdfFixture(relativePath: string): string {
  const sourcePath = path.resolve(relativePath);
  const pdfBytes = fs.readFileSync(sourcePath);
  const marker = Buffer.from(`\n% Mind FC upload ${randomUUID()}\n`);
  const eofMarker = Buffer.from('%%EOF');
  const eofIndex = pdfBytes.lastIndexOf(eofMarker);

  const augmented =
    eofIndex >= 0
      ? Buffer.concat([pdfBytes.subarray(0, eofIndex), marker, pdfBytes.subarray(eofIndex)])
      : Buffer.concat([pdfBytes, marker, eofMarker]);

  const tempFilePath = path.join(os.tmpdir(), `mind_fc_${randomUUID()}.pdf`);
  fs.writeFileSync(tempFilePath, augmented);
  return tempFilePath;
}

async function deleteStatementsByIds(page: Page, ids: string[]): Promise<void> {
  if (!ids.length) return;
  for (const id of ids) {
    await page.evaluate(
      async (statementId) => {
        await fetch(`/ai/api/reconciliation/firstcard/statements/${statementId}`, {
          method: 'DELETE',
          credentials: 'include',
        });
      },
      id,
    );
  }
  await page.reload({ waitUntil: 'networkidle' });
}

async function deleteExistingStatements(page: Page): Promise<void> {
  const ids = await listStatementIds(page);
  if (!ids.length) {
    return;
  }
  await deleteStatementsByIds(page, ids);
  await expect
    .poll(async () => (await listStatementIds(page)).length, { timeout: 30000 })
    .toBe(0);
}

async function listStatementIds(page: Page): Promise<string[]> {
  return page.evaluate(async () => {
    const response = await fetch('/ai/api/reconciliation/firstcard/statements', {
      method: 'GET',
      credentials: 'include',
    });
    if (!response.ok) {
      return [];
    }
    const data = await response.json();
    const statements = Array.isArray(data?.statements) ? data.statements : [];
    return statements
      .map((item: Record<string, unknown>) => {
        const id = item?.id;
        return typeof id === 'string' ? id : null;
      })
      .filter((id: string | null): id is string => Boolean(id));
  });
}

test('test', async ({ page }) => {
  test.setTimeout(10 * 60 * 1000);
  page.on('dialog', (dialog) => dialog.accept());

  const uploadPath = createUniquePdfFixture('fc/FC_2503.pdf');
  const uploadFileName = path.basename(uploadPath);

  await page.goto('http://localhost:5169/login');
  await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
  await page.getByRole('textbox', { name: 'Användarnamn' }).press('Tab');
  await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.getByRole('button', { name: 'Kortmatchning' }).click();
  await page.waitForLoadState('networkidle');

  await deleteExistingStatements(page);

  await page.getByRole('button', { name: 'Ladda upp utdrag' }).click();
  await page.getByRole('button', { name: 'Choose File' }).setInputFiles(uploadPath);
  await page.getByRole('button', { name: 'Ladda upp', exact: true }).click();

  let invoiceId: string | null = null;
  try {
    await expect(
      page.getByText('Uppladdning klar: 1 fil skickades för bearbetning.', { exact: true }).first(),
    ).toBeVisible({ timeout: 15000 });

    await expect
      .poll(async () => (await listStatementIds(page)).length, { timeout: 60000 })
      .toBeGreaterThan(0);

    const ids = await listStatementIds(page);
    invoiceId = ids.length ? ids[0] : null;

    await expect
      .poll(
        async () =>
          page.evaluate(async () => {
            const response = await fetch('/ai/api/receipts?page=1&page_size=25', {
              method: 'GET',
              credentials: 'include',
            });
            if (!response.ok) {
              return null;
            }
            const payload = await response.json();
            const target = (Array.isArray(payload?.items) ? payload.items : []).find(
              (item) => String(item?.workflow_type || '').toLowerCase() === 'creditcard_invoice',
            );
            return target?.document_type || null;
          }),
        { timeout: 240000, message: 'Förväntade att dokumenttyp sattes till Credit Card.' },
      )
      .toBe('Credit Card');

    // Confirm credit card invoice appears in Process view with correct document classification.
    await page.getByRole('button', { name: 'Process' }).click();
    await expect(page.getByRole('heading', { name: 'Process' })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Laddar kvitton...')).toBeHidden({ timeout: 60000 });
    const creditCardLabels = page.getByText('Credit Card');
    await expect(creditCardLabels.first()).toBeVisible({ timeout: 120000 });

    // Ensure the credit card invoice does not surface in the Receipts queue.
    await page.getByRole('button', { name: 'Kvitton' }).click();
    await expect(page.getByRole('heading', { level: 1, name: 'Kvitton' })).toBeVisible({ timeout: 15000 });
    const receiptsSearch = page.getByPlaceholder('Sök efter företag, filnamn eller belopp');
    await receiptsSearch.fill(uploadFileName);
    await page.getByRole('button', { name: 'Sök' }).click();
    await expect(page.getByText('Inga kvitton hittades')).toBeVisible({ timeout: 15000 });

  } finally {
    fs.rmSync(uploadPath, { force: true });
  }

  if (invoiceId) {
    await deleteStatementsByIds(page, [invoiceId]);
    await expect
      .poll(async () => (await listStatementIds(page)).length, { timeout: 30000 })
      .toBe(0);
  }
});
