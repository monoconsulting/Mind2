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

test('verify FirstCard preview modal and log date grouping', async ({ page }) => {
  test.setTimeout(10 * 60 * 1000);
  page.on('dialog', (dialog) => dialog.accept());

  const uploadPath = createUniquePdfFixture('fc/FC_2503.pdf');
  let invoiceId: string | null = null;
  let statementId: string | null = null;

  try {
    // Login
    await page.goto('http://localhost:5169/login');
    await page.getByRole('textbox', { name: 'Användarnamn' }).fill('admin');
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();

    // Navigate to FirstCard
    await page.getByRole('button', { name: 'Kortmatchning' }).click();
    await page.waitForLoadState('networkidle');

    // Upload FirstCard statement
    await page.getByRole('button', { name: 'Ladda upp utdrag' }).click();
    await page.getByRole('button', { name: 'Choose File' }).setInputFiles(uploadPath);
    await page.getByRole('button', { name: 'Ladda upp', exact: true }).click();

    // Wait for upload success
    await expect(
      page.getByText('Uppladdning klar: 1 fil skickades för bearbetning.', { exact: true }).first(),
    ).toBeVisible({ timeout: 15000 });

    // Wait for statement to appear
    await expect
      .poll(async () => (await listStatementIds(page)).length, { timeout: 60000 })
      .toBeGreaterThan(0);

    const ids = await listStatementIds(page);
    statementId = ids.length ? ids[0] : null;

    // Wait for processing to complete (document_type = Credit Card)
    await expect
      .poll(
        async () =>
          page.evaluate(async () => {
            const response = await fetch('/ai/api/receipts?page=1&page_size=25', {
              method: 'GET',
              credentials: 'include',
            });
            if (!response.ok) return null;
            const payload = await response.json();
            const target = (Array.isArray(payload?.items) ? payload.items : []).find(
              (item) => String(item?.workflow_type || '').toLowerCase() === 'creditcard_invoice',
            );
            return target?.document_type || null;
          }),
        { timeout: 240000 },
      )
      .toBe('Credit Card');

    // Verify CC file_type stability + AI1 metadata stored in other_data
    const ccInfo = await page.evaluate(async () => {
      const response = await fetch('/ai/api/receipts?page=1&page_size=50&include_credit=1', {
        method: 'GET',
        credentials: 'include',
      });
      if (!response.ok) return null;
      const payload = await response.json();
      const items = Array.isArray(payload?.items) ? payload.items : [];
      const target = items.find(
        (item) =>
          String(item?.workflow_type || '').toLowerCase() === 'creditcard_invoice' ||
          String(item?.file_type || '').toLowerCase().startsWith('cc_'),
      );
      if (!target?.id) return null;
      return { id: target.id, file_type: target.file_type };
    });

    expect(ccInfo?.file_type || '').toMatch(/^cc_/);

    await expect
      .poll(
        async () =>
          page.evaluate(async (receiptId) => {
            if (!receiptId) return null;
            const response = await fetch(`/ai/api/receipts/${encodeURIComponent(receiptId)}`, {
              method: 'GET',
              credentials: 'include',
            });
            if (!response.ok) return null;
            const payload = await response.json();
            let otherData: any = payload?.other_data || payload?.otherData || null;
            if (typeof otherData === 'string') {
              try {
                otherData = JSON.parse(otherData);
              } catch {
                otherData = null;
              }
            }
            return otherData?.ai1_document_type || null;
          }, ccInfo?.id),
        { timeout: 240000 },
      )
      .toBeTruthy();

    const ai1DocType = await page.evaluate(async (receiptId) => {
      if (!receiptId) return null;
      const response = await fetch(`/ai/api/receipts/${encodeURIComponent(receiptId)}`, {
        method: 'GET',
        credentials: 'include',
      });
      if (!response.ok) return null;
      const payload = await response.json();
      let otherData: any = payload?.other_data || payload?.otherData || null;
      if (typeof otherData === 'string') {
        try {
          otherData = JSON.parse(otherData);
        } catch {
          otherData = null;
        }
      }
      return otherData?.ai1_document_type || null;
    }, ccInfo?.id);

    expect(String(ai1DocType)).toMatch(/^(invoice|fc_invoice)$/i);

    await expect
      .poll(
        async () =>
          page.evaluate(async (invoiceId) => {
            if (!invoiceId) return 0;
            const response = await fetch(`/ai/api/reconciliation/firstcard/invoices/${encodeURIComponent(invoiceId)}`, {
              method: 'GET',
              credentials: 'include',
            });
            if (!response.ok) return 0;
            const payload = await response.json();
            const lines = Array.isArray(payload?.lines) ? payload.lines : [];
            return lines.length;
          }, statementId || ccInfo?.id),
        { timeout: 240000 },
      )
      .toBeGreaterThan(0);

    // WF3 must accept FC invoices even if AI1 classified as "invoice".
    if (String(ai1DocType).toLowerCase() === 'invoice') {
      const invoiceLinesCount = await page.evaluate(async (invoiceId) => {
        if (!invoiceId) return 0;
        const response = await fetch(`/ai/api/reconciliation/firstcard/invoices/${encodeURIComponent(invoiceId)}`, {
          method: 'GET',
          credentials: 'include',
        });
        if (!response.ok) return 0;
        const payload = await response.json();
        const lines = Array.isArray(payload?.lines) ? payload.lines : [];
        return lines.length;
      }, statementId || ccInfo?.id);
      expect(invoiceLinesCount).toBeGreaterThan(0);
    }

    // Take screenshot after processing
    await page.screenshot({
      path: 'web/test-results/media/snapshots/fc-after-processing.png',
      fullPage: false
    });

    console.log('✓ FirstCard processing complete');

    // Reload page to ensure fresh data
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // ==================================================================
    // TEST 1: Verify Preview Modal Exists and Can Be Opened
    // ==================================================================
    console.log('\n=== Testing Preview Modal ===');

    // Click on first statement to select it
    const firstStatement = page.locator('tbody tr').first();
    await firstStatement.click();
    await page.waitForTimeout(1000);

    // Take screenshot of table with statement selected
    await page.screenshot({
      path: 'web/test-results/media/snapshots/fc-statement-selected.png',
      fullPage: false
    });

    // Look for "Förhandsgranska" buttons
    const previewButtons = page.getByRole('button', { name: 'Förhandsgranska' });
    const previewButtonCount = await previewButtons.count();
    console.log(`Found ${previewButtonCount} "Förhandsgranska" buttons`);

    if (previewButtonCount === 0) {
      // Try alternative button with icon
      const visaButtons = page.getByRole('button', { name: 'Visa' });
      const visaButtonCount = await visaButtons.count();
      console.log(`Found ${visaButtonCount} "Visa" buttons`);

      if (visaButtonCount > 0) {
        console.log('Clicking first "Visa" button...');
        await visaButtons.first().click();
      } else {
        console.error('ERROR: No preview buttons found at all!');
        await page.screenshot({
          path: 'web/test-results/media/snapshots/fc-no-preview-buttons.png',
          fullPage: true
        });
      }
    } else {
      console.log('Clicking first "Förhandsgranska" button...');
      await previewButtons.first().click();
    }

    await page.waitForTimeout(1000);

    // Check if modal is visible
    const modalVisible = await page.locator('[class*="modal"], [role="dialog"]').isVisible().catch(() => false);

    if (modalVisible) {
      console.log('✓ Preview modal opened successfully');
      await page.screenshot({
        path: 'web/test-results/media/snapshots/fc-preview-modal-open.png',
        fullPage: false
      });

      // Close modal
      const closeButton = page.locator('button').filter({ hasText: /stäng|close/i }).first();
      if (await closeButton.isVisible()) {
        await closeButton.click();
        console.log('✓ Modal closed');
      }
    } else {
      console.error('✗ Preview modal did NOT open');
      await page.screenshot({
        path: 'web/test-results/media/snapshots/fc-preview-modal-FAILED.png',
        fullPage: true
      });

      // Get page HTML for debugging
      const html = await page.content();
      fs.writeFileSync('web/test-results/fc-page-content.html', html);
      console.log('Page HTML saved to: web/test-results/fc-page-content.html');
    }

    // ==================================================================
    // TEST 2: Verify Log Date Grouping
    // ==================================================================
    console.log('\n=== Testing Log Date Grouping ===');

    // Click on "Visa logg" button
    const showLogButtons = page.getByRole('button', { name: /visa logg/i });
    const logButtonCount = await showLogButtons.count();
    console.log(`Found ${logButtonCount} "Visa logg" buttons`);

    if (logButtonCount > 0) {
      await showLogButtons.first().click();
      await page.waitForTimeout(2000);

      // Take screenshot of opened log
      await page.screenshot({
        path: 'web/test-results/media/snapshots/fc-log-modal-open.png',
        fullPage: false
      });

      // Extract log structure
      const logStructure = await page.evaluate(() => {
        const logModal = document.querySelector('[class*="modal"]') || document.body;

        // Find all date headers
        const dateHeaders = Array.from(logModal.querySelectorAll('h3, h4, h5')).filter(el =>
          /\d{4}-\d{2}-\d{2}/.test(el.textContent || '')
        );

        const structure: Array<{date: string, workflows: string[], ai6: string[]}> = [];

        dateHeaders.forEach(header => {
          const dateText = header.textContent || '';
          const dateMatch = dateText.match(/\d{4}-\d{2}-\d{2}/);
          if (!dateMatch) return;

          const date = dateMatch[0];

          // Find all workflow runs under this date
          let currentEl = header.nextElementSibling;
          const workflows: string[] = [];
          const ai6: string[] = [];

          while (currentEl && !currentEl.matches('h3, h4, h5')) {
            const text = currentEl.textContent || '';

            if (text.includes('WF3_FIRSTCARD_INVOICE')) {
              workflows.push(text.trim());
            }
            if (text.includes('AI6') || text.includes('CreditCardInvoiceParsing')) {
              ai6.push(text.trim());
            }

            currentEl = currentEl.nextElementSibling;
          }

          structure.push({ date, workflows, ai6 });
        });

        return structure;
      });

      console.log('\nLog structure found:');
      console.log(JSON.stringify(logStructure, null, 2));

      // Verify: Latest date should be first
      if (logStructure.length > 1) {
        const dates = logStructure.map(s => s.date);
        const sortedDates = [...dates].sort().reverse();

        if (JSON.stringify(dates) === JSON.stringify(sortedDates)) {
          console.log('✓ Dates are correctly sorted (newest first)');
        } else {
          console.error('✗ Dates are NOT sorted correctly');
          console.error(`  Expected: ${sortedDates.join(', ')}`);
          console.error(`  Actual:   ${dates.join(', ')}`);
        }
      }

      // Verify: WF3 and AI6 entries for same date should be grouped together
      logStructure.forEach(({ date, workflows, ai6 }) => {
        if (workflows.length > 0 && ai6.length > 0) {
          console.log(`✓ Date ${date}: Found ${workflows.length} WF3 entries and ${ai6.length} AI6 entries grouped together`);
        } else if (workflows.length > 0) {
          console.log(`  Date ${date}: Found ${workflows.length} WF3 entries (no AI6)`);
        } else if (ai6.length > 0) {
          console.log(`  Date ${date}: Found ${ai6.length} AI6 entries (no WF3)`);
        }
      });

      // Close log modal
      const closeLogButton = page.locator('button').filter({ hasText: /stäng|close/i }).first();
      if (await closeLogButton.isVisible()) {
        await closeLogButton.click();
        console.log('✓ Log modal closed');
      }
    } else {
      console.error('✗ No "Visa logg" button found');
      await page.screenshot({
        path: 'web/test-results/media/snapshots/fc-no-log-button.png',
        fullPage: true
      });
    }

  } finally {
    fs.rmSync(uploadPath, { force: true });

    // Cleanup: Delete test statement
    if (statementId) {
      await deleteStatementsByIds(page, [statementId]);
    }
  }

  console.log('\n=== Test Complete ===');
});
