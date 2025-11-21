import { test, expect } from '@playwright/test';

const png1x1 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+pN9kAAAAASUVORK5CYII=',
  'base64'
);

test.describe('Process status & upload filters', () => {
  test('dropdowns follow workflow definitions and filters use stage data', async ({ page }) => {
    const receipts = [
      {
        id: 'portal-2024',
        merchant: 'Portal Traders',
        original_filename: 'portal-2024.pdf',
        purchase_datetime: '2024-05-05T10:00:00Z',
        file_creation_timestamp: '2024-05-05T09:00:00Z',
        net_amount: 500,
        gross_amount: 625,
        status: 'completed',
        ai_status: 'completed',
        workflow_stage_key: 'r_ai4',
        workflow_stage_state: 'succeeded',
        workflow_stage_status: 'r_ai4 succeeded',
        file_type: 'receipt',
        workflow_type: 'receipt',
        submitted_by: 'web_upload',
        line_item_count: 2,
        expense_type: 'corporate',
        payment_type: 'card',
        tags: ['portal'],
        upload_stage: {
          stage_key: 'src_portal',
          status: 'succeeded',
          label: 'Portal'
        },
        workflow_stages: {
          src_portal: { stage_key: 'src_portal', status: 'succeeded', label: 'Portal' },
          r_ai4: { stage_key: 'r_ai4', status: 'succeeded', label: 'Normalisering' }
        }
      },
      {
        id: 'ftp-2025',
        merchant: 'FTP Corp',
        original_filename: 'ftp-2025.pdf',
        purchase_datetime: '2025-01-12T09:00:00Z',
        file_creation_timestamp: '2025-01-12T08:45:00Z',
        net_amount: 300,
        gross_amount: 375,
        status: 'processing',
        ai_status: 'processing',
        workflow_stage_key: 'r_ai3',
        workflow_stage_state: 'running',
        workflow_stage_status: 'r_ai3 running',
        file_type: 'receipt',
        workflow_type: 'receipt',
        submitted_by: 'ftp_bot',
        line_item_count: 1,
        expense_type: 'corporate',
        payment_type: 'card',
        tags: ['ftp'],
        upload_stage: {
          stage_key: 'src_ftp',
          status: 'succeeded',
          label: 'FTP'
        },
        workflow_stages: {
          src_ftp: { stage_key: 'src_ftp', status: 'succeeded', label: 'FTP' },
          r_ai3: { stage_key: 'r_ai3', status: 'running', label: 'Dataextraktion' }
        }
      }
    ];

    await page.route('**/ai/api/receipts**', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }
      const url = new URL(route.request().url());
      const workflowStage = url.searchParams.get('workflow_stage');
      const uploadStage = url.searchParams.get('upload_stage');
      const search = url.searchParams.get('search');

      let filtered = receipts.slice();
      if (workflowStage) {
        filtered = filtered.filter((item) => item.workflow_stage_key === workflowStage);
      }
      if (uploadStage) {
        filtered = filtered.filter((item) => item.upload_stage?.stage_key === uploadStage);
      }
      if (search) {
        if (/^\d{4}$/.test(search)) {
          filtered = filtered.filter((item) => item.purchase_datetime.startsWith(search));
        } else {
          const lower = search.toLowerCase();
          filtered = filtered.filter((item) => item.merchant.toLowerCase().includes(lower));
        }
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: filtered,
          meta: {
            page: 1,
            page_size: filtered.length,
            total: filtered.length
          }
        })
      });
    });

    await page.route('**/ai/api/receipts/*/workflow-status**', async (route) => {
      const match = route.request().url().match(/receipts\/([^/]+)/);
      const id = match?.[1];
      const receipt = receipts.find((item) => item.id === id);
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          file_id: id,
          title: receipt?.merchant || id,
          datetime: '2025-01-01 10:00',
          upload: 'Upload',
          filename: receipt?.original_filename,
          pdf_convert: 'success',
          ocr: { status: 'succeeded', data: null },
          ocr_merge: { status: 'pending', data: null },
          ocr_raw_updated: { status: 'pending', data: null },
          ai1: { status: 'succeeded', data: null },
          ai2: { status: 'succeeded', data: null },
          ai3: { status: 'running', data: null },
          ai4: { status: 'pending', data: null },
          ai5: { status: 'pending', data: null },
          ai6: { status: 'pending', data: null },
          match: { status: 'pending', data: null },
          upload_stage: receipt?.upload_stage || null
        })
      });
    });

    await page.route('**/ai/api/receipts/*/image**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'image/png',
        body: png1x1
      });
    });

    await page.goto('/process');

    await expect(page.getByRole('row', { name: /Portal Traders/ })).toBeVisible();
    await expect(page.getByRole('row', { name: /FTP Corp/ })).toBeVisible();

    const statusSelect = page.getByLabel('Status').first();
    await expect(statusSelect).toContainText('Uploads · Portal');
    await expect(page.getByRole('row', { name: /Portal Traders/ }).getByText('Portal - klar')).toBeVisible();

    const uploadSelect = page.getByLabel('Upload').first();
    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/ai/api/receipts') && response.request().url().includes('upload_stage=src_ftp')),
      uploadSelect.selectOption('src_ftp')
    ]);
    await expect(page.getByRole('row', { name: /FTP Corp/ })).toBeVisible();
    await expect(page.getByRole('row', { name: /Portal Traders/ })).toHaveCount(0);

    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/ai/api/receipts') && !response.request().url().includes('upload_stage=')),
      uploadSelect.selectOption('')
    ]);

    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/ai/api/receipts') && response.request().url().includes('workflow_stage=r_ai3')),
      statusSelect.selectOption('stage:r_ai3')
    ]);
    await expect(page.getByRole('row', { name: /FTP Corp/ })).toBeVisible();
    await expect(page.getByRole('row', { name: /Portal Traders/ })).toHaveCount(0);

    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/ai/api/receipts') && !response.request().url().includes('workflow_stage=')),
      statusSelect.selectOption('')
    ]);

    const searchInput = page.getByPlaceholder('Sök efter företag, filnamn eller belopp');
    await searchInput.fill('2024');
    await Promise.all([
      page.waitForResponse((response) => response.url().includes('/ai/api/receipts') && response.request().url().includes('search=2024')),
      page.getByRole('button', { name: /^Sök$/ }).click()
    ]);
    await expect(page.getByRole('row', { name: /Portal Traders/ })).toBeVisible();
    await expect(page.getByRole('row', { name: /FTP Corp/ })).toHaveCount(0);
  });
});
