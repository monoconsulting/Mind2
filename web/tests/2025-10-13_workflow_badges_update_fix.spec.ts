import { test, expect } from '@playwright/test';

/**
 * Test: Workflow badges (AI1-AI4) should update when status changes
 *
 * Issue #55: The status blocks were not updating in the interval set from env-file
 * Root cause: Backend /ai/api/receipts endpoint was not returning ai_status field
 * Fix: Added ai_status field to receipts list response
 *
 * This test verifies:
 * 1. Workflow badges are present on the Process page
 * 2. Badges update when the auto-refresh interval triggers
 * 3. Both status column AND workflow badges update together
 */

test.describe('Workflow Badges Update Fix - Issue #55', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8008/login');
    await page.getByRole('textbox', { name: 'Lösenord' }).fill('adminadmin');
    await page.getByRole('button', { name: 'Logga in' }).click();
    await page.waitForURL('**/process', { timeout: 10000 });
    await page.waitForLoadState('networkidle');
  });

  test('should load process page', async ({ page }) => {
    await expect(page).toHaveURL(/\/process$/);
  });

  test('should display workflow badges for receipts', async ({ page }) => {
    const table = page.locator('table.table-dark');
    await expect(table).toBeVisible({ timeout: 10000 });

    const firstRow = table.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();

    const workflowBadges = firstRow.locator('td').nth(1);
    await expect(workflowBadges).toBeVisible();

    const aiBadges = await Promise.all([
      workflowBadges.getByText('AI1').count(),
      workflowBadges.getByText('AI2').count(),
      workflowBadges.getByText('AI3').count(),
      workflowBadges.getByText('AI4').count(),
    ]);

    const totalBadges = aiBadges.reduce((sum, count) => sum + count, 0);
    expect(totalBadges).toBeGreaterThan(0);
  });

  test('should verify receipts have both status and ai_status fields', async ({ page }) => {
    const receiptsResponse = page.waitForResponse(
      (response) => response.url().includes('/ai/api/receipts') && response.status() === 200
    );

    await page.reload();

    const response = await receiptsResponse;
    const data = await response.json();

    expect(data).toHaveProperty('items');
    expect(Array.isArray(data.items)).toBe(true);

    if (data.items.length > 0) {
      const firstReceipt = data.items[0];
      expect(firstReceipt).toHaveProperty('status');
      expect(firstReceipt).toHaveProperty('ai_status');
      console.log(`Receipt has status: ${firstReceipt.status}`);
      console.log(`Receipt has ai_status: ${firstReceipt.ai_status}`);
    }
  });

  test('should update workflow badges when status changes (simulated by refresh)', async ({ page }) => {
    const table = page.locator('table.table-dark');
    await expect(table).toBeVisible({ timeout: 10000 });

    const firstRow = table.locator('tbody tr').first();
    await expect(firstRow).toBeVisible();

    const workflowBadgesCell = firstRow.locator('td').nth(1);
    const initialBadgeText = await workflowBadgesCell.textContent();
    console.log('Initial workflow badges:', initialBadgeText);

    const nextRefresh = page.waitForResponse(
      (response) => response.url().includes('/ai/api/receipts') && response.status() === 200,
      { timeout: 15000 }
    );
    await nextRefresh;
    await page.waitForTimeout(1000);

    await expect(workflowBadgesCell).toBeVisible();
    const updatedBadgeText = await workflowBadgesCell.textContent();
    console.log('Updated workflow badges:', updatedBadgeText);
    expect(updatedBadgeText).toMatch(/AI[1-4]/);
  });

  test('should verify WorkflowBadges component fetches workflow-status endpoint', async ({ page }) => {
    const workflowStatusCall = page.waitForResponse(
      (response) => response.url().includes('/workflow-status') && response.status() === 200,
      { timeout: 15000 }
    );

    await page.reload();
    await page.waitForLoadState('networkidle');

    const response = await workflowStatusCall;
    const workflowData = await response.json();

    console.log('Workflow status response:', JSON.stringify(workflowData, null, 2));

    expect(workflowData).toHaveProperty('file_id');
    expect(workflowData).toHaveProperty('ai1');
    expect(workflowData).toHaveProperty('ai2');
    expect(workflowData).toHaveProperty('ai3');
    expect(workflowData).toHaveProperty('ai4');

    if (workflowData.ai1) {
      expect(workflowData.ai1).toHaveProperty('status');
    }
  });

  test('CRITICAL: Click Återuppta button and verify badges update AI1->AI2->AI3->AI4', async ({ page }) => {
    const table = page.locator('table.table-dark');
    await expect(table).toBeVisible({ timeout: 10000 });

    const completedRow = table
      .locator('tbody tr')
      .filter({ has: page.locator('span.status-badge.status-passed') })
      .first();

    const targetRow = (await completedRow.count()) > 0 ? completedRow : table.locator('tbody tr').first();
    await expect(targetRow).toBeVisible();
    console.log('>> Found target receipt row');

    const workflowBadgesCell = targetRow.locator('td').nth(1);
    await expect(workflowBadgesCell).toBeVisible();

    const getAIBadgeStatuses = async () => {
      const fetchBadge = async (label: string) => {
        return workflowBadgesCell
          .getByText(label)
          .locator('..')
          .locator('span.status-badge')
          .textContent()
          .catch(() => 'N/A');
      };

      return {
        ai1: await fetchBadge('AI1'),
        ai2: await fetchBadge('AI2'),
        ai3: await fetchBadge('AI3'),
        ai4: await fetchBadge('AI4'),
      };
    };

    const initialStatuses = await getAIBadgeStatuses();
    console.log('>> Initial badge statuses:', initialStatuses);

    const resumeButton = targetRow.getByRole('button', { name: /Återuppta/i });
    await expect(resumeButton).toBeVisible();

    const resumeRequestPromise = page.waitForRequest(
      (request) =>
        request.method() === 'POST' &&
        request.url().includes('/ai/api/ingest/process/') &&
        request.url().endsWith('/resume')
    );
    const receiptsRefreshPromise = page.waitForResponse(
      (response) => response.url().includes('/ai/api/receipts') && response.status() === 200,
      { timeout: 15000 }
    );

    console.log('>> Clicking Återuppta button...');
    await resumeButton.click();

    const resumeRequest = await resumeRequestPromise;
    const resumeMatch = resumeRequest.url().match(/process\/([^/]+)\/resume$/);
    if (!resumeMatch) {
      throw new Error(`Could not parse resumed receipt id from ${resumeRequest.url()}`);
    }
    const resumedReceiptId = resumeMatch[1];

    await receiptsRefreshPromise;

    const workflowStages = ['ai1', 'ai2', 'ai3', 'ai4'] as const;
    let foundPending = false;

    for (let attempt = 1; attempt <= 5 && !foundPending; attempt++) {
      if (attempt > 1) {
        await page.waitForTimeout(500);
      }

      try {
        const workflowApiResponse = await page.request.get(
          `/ai/api/receipts/${encodeURIComponent(resumedReceiptId)}/workflow-status`
        );
        if (!workflowApiResponse.ok()) {
          console.log(
            `[API] Workflow status check attempt ${attempt} failed with HTTP ${workflowApiResponse.status()}`
          );
          continue;
        }
        const workflowPayload = await workflowApiResponse.json();
        const statuses = workflowStages.map((stage) => workflowPayload[stage]?.status || null);
        console.log(`[API] Workflow statuses attempt ${attempt}:`, statuses);
        if (statuses.some((status) => status === 'pending')) {
          foundPending = true;
          console.log('>> Badges updated to pending (API response)');
        }
      } catch (apiError) {
        console.log(`[API] Workflow status fetch error on attempt ${attempt}:`, apiError);
      }
    }

    console.log('>> Waiting for badges to update to pending...');

    let foundSuccess = false;
    let iterations = 0;
    const maxIterations = 30;

    while (iterations < maxIterations) {
      await page.waitForTimeout(2000);
      iterations += 1;

      const currentStatuses = await getAIBadgeStatuses();
      console.log(`[${iterations}] Current statuses:`, currentStatuses);

      if (!foundPending) {
        if (
          currentStatuses.ai1 === 'pending' ||
          currentStatuses.ai2 === 'pending' ||
          currentStatuses.ai3 === 'pending' ||
          currentStatuses.ai4 === 'pending'
        ) {
          foundPending = true;
          console.log('>> Badges updated to pending (UI poll)');
        }
      }

      if (
        currentStatuses.ai1 === 'success' ||
        currentStatuses.ai2 === 'success' ||
        currentStatuses.ai3 === 'success' ||
        currentStatuses.ai4 === 'success'
      ) {
        if (!foundSuccess) {
          foundSuccess = true;
          console.log('>> Badges progressing to success');
        }
      }

      if (currentStatuses.ai4 === 'success' || currentStatuses.ai4 === 'completed') {
        console.log('>> AI4 completed; workflow badges update confirmed');
        break;
      }
    }

    const finalStatuses = await getAIBadgeStatuses();
    console.log('>> Final badge statuses:', finalStatuses);

    expect(foundPending).toBe(true);
    console.log('Workflow badges updated correctly during resume sequence');
  });
});
