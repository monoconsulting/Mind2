// web/tests/workflow_status.spec.ts
import { test, expect, Page, Locator } from '@playwright/test';

test.use({
  viewport: { width: 2560, height: 1440 },
});

/**
 * -----------------------------------------------------------------------------
 * Helpers
 * -----------------------------------------------------------------------------
 */

/**
 * Returns a friendly record of stage labels used in the UI.
 *
 * @returns {{AI1:string; AI2:string; AI3:string; AI4:string}}
 *   Well-known UI labels for the four AI stages.
 */
function stageLabels() {
  return {
    AI1: 'AI1 - Dokumentklassificering',
    AI2: 'AI2 - Utgiftsklassificering',
    AI3: 'AI3',
    AI4: 'AI4',
  };
}

/**
 * Create a locator for a stage "row" (a container that includes the stage label and its badge).
 *
 * The selector strategy is text-anchored: we find an element containing the stage label
 * and then search upward (closest row/container) to scope badge queries robustly.
 *
 * @param {Page} page - Playwright Page.
 * @param {string} label - Visible text of the stage label (e.g., "AI1 - Dokumentklassificering").
 * @returns {Locator} A locator representing the stage row/container.
 */
function stageRow(page: Page, label: string): Locator {
  // Find the element that has the stage label text, then narrow to its nearest row-like container.
  // Adjust the container selector if your DOM groups stages differently.
  const labelEl = page.getByText(label, { exact: false });
  return labelEl.locator('xpath=ancestor-or-self::*[self::tr or self::*[@role="row"] or self::div][1]');
}

/**
 * Returns the status badge locator within a stage row.
 *
 * Expected badge classes observed in the app:
 *   - .status-badge.status-manual_review
 *   - .status-badge.status-pending
 *   - .status-badge.status-success
 *   - .status-badge.status-error
 *
 * @param {Page} page - Playwright Page.
 * @param {string} label - Stage label.
 * @returns {Locator} The badge locator inside the stage row.
 */
function stageBadge(page: Page, label: string): Locator {
  return stageRow(page, label).locator('.status-badge');
}

/**
 * Read the current status of a stage badge by inspecting its class list.
 *
 * @param {Locator} badge - Badge locator.
 * @returns {Promise<'manual_review'|'pending'|'success'|'error'|'unknown'>}
 *   Parsed status string from class names.
 */
async function getBadgeStatus(badge: Locator): Promise<'manual_review'|'pending'|'success'|'error'|'unknown'> {
  const className = await badge.getAttribute('class');
  if (!className) return 'unknown';
  if (className.includes('status-manual_review')) return 'manual_review';
  if (className.includes('status-pending')) return 'pending';
  if (className.includes('status-success')) return 'success';
  if (className.includes('status-error')) return 'error';
  return 'unknown';
}

/**
 * Wait until a stage badge reaches a specific state, with polling and timeout.
 *
 * @param {Page} page - Playwright Page.
 * @param {string} label - Stage label (visible text).
 * @param {'manual_review'|'pending'|'success'|'error'} state - Target state.
 * @param {number} timeoutMs - Max time to wait in ms.
 */
async function waitForStageState(
  page: Page,
  label: string,
  state: 'manual_review'|'pending'|'success'|'error',
  timeoutMs = 90_000
): Promise<void> {
  const badge = stageBadge(page, label);
  const start = Date.now();
  await expect(badge).toBeVisible();
  while (true) {
    const current = await getBadgeStatus(badge);
    if (current === state) return;
    if (Date.now() - start > timeoutMs) {
      throw new Error(`Timed out waiting for stage "${label}" to become "${state}". Last seen: "${current}".`);
    }
    await page.waitForTimeout(500);
  }
}

/**
 * Ensure all four stages show "pending" badges (after pressing Process).
 * This guarantees a clean starting point before asserting ordered success.
 *
 * @param {Page} page - Playwright Page.
 */
async function waitAllStagesPending(page: Page): Promise<void> {
  const labels = stageLabels();
  await Promise.all([
    waitForStageState(page, labels.AI1, 'pending', 30_000),
    waitForStageState(page, labels.AI2, 'pending', 30_000),
    waitForStageState(page, labels.AI3, 'pending', 30_000),
    waitForStageState(page, labels.AI4, 'pending', 30_000),
  ]);
}

/**
 * If a stage falls back to manual review or error, this attempts a recovery:
 *  - Click the badge (common pattern to open details/manual dialog).
 *  - Close any dialog if present.
 *  - Click the global "Process" button again to re-queue the workflow.
 *
 * NOTE: This mirrors the user’s recorded steps (click badge, open/close dialogs, re-process).
 * If your app uses specific confirm buttons, add them here with explicit locators.
 *
 * @param {Page} page - Playwright Page.
 * @param {string} label - Stage label.
 */
async function attemptRecoveryToPending(page: Page, label: string): Promise<void> {
  const badge = stageBadge(page, label);
  await badge.click({ trial: false });
  // Try to close detail dialog if it appears (optional; ignore if not present).
  const detailsDialog = page.getByRole('dialog', { name: /AI Stage Details/i });
  if (await detailsDialog.isVisible().catch(() => false)) {
    // Prefer close button label "Stäng" if available; else Esc as fallback
    const closeBtn = page.getByLabel('Stäng', { exact: true });
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
  }
  // Re-process the workflow
  await page.getByRole('button', { name: 'Process' }).click();
  await waitAllStagesPending(page);
}

/**
 * Drive ordered success: wait for AI1→AI2→AI3→AI4 to become success in strict sequence.
 * If any stage flips to "manual_review" or "error", attempt recovery and continue.
 *
 * @param {Page} page - Playwright Page.
 */
async function waitForOrderedSuccess(page: Page): Promise<void> {
  const labels = stageLabels();
  const ordered = [labels.AI1, labels.AI2, labels.AI3, labels.AI4];
  for (const label of ordered) {
    // Loop until the current stage reaches success (handling manual/error detours).
    // Give generous time per stage; internal retries handle short-lived detours.
    const hardTimeoutPerStage = 5 * 60_000; // 5 minutes per stage
    const started = Date.now();
    while (true) {
      const status = await getBadgeStatus(stageBadge(page, label));
      if (status === 'success') break;
      if (status === 'manual_review' || status === 'error') {
        await attemptRecoveryToPending(page, label);
      } else {
        // Let it run if pending; avoid hammering
        await page.waitForTimeout(1000);
      }
      if (Date.now() - started > hardTimeoutPerStage) {
        throw new Error(`Stage "${label}" did not reach success within ${hardTimeoutPerStage / 1000}s. Last status: ${status}`);
      }
    }
  }
}

/**
 * Verifies the final business goal text appears for AI4:
 * "Bokföringsförslag klart" must be visible near/within AI4 context.
 *
 * @param {Page} page - Playwright Page.
 */
async function expectAI4FinalText(page: Page): Promise<void> {
  const labels = stageLabels();
  const row = stageRow(page, labels.AI4);
  await expect(row.getByText(/Bokföringsförslag klart/i)).toBeVisible({
    timeout: 30_000,
  });
}

/**
 * Open the first receipt row into details, matching the user's original steps but in a robust way.
 * The earlier snippet clicked nth(2) button in a specific row ID; here we avoid hard-coded IDs.
 *
 * @param {Page} page - Playwright Page.
 */
async function openFirstReceiptDetails(page: Page): Promise<void> {
  // The UI shows a row with a preview button label like "Förhandsgranska kvitto <uuid>".
  // Click the third action button (index 2) on the first matching row – mirroring the user’s flow.
  const firstPreviewRow = page.getByRole('row', { name: /Förhandsgranska kvitto/i }).first();
  await expect(firstPreviewRow).toBeVisible();
  await firstPreviewRow.locator('button').nth(2).click();
}

/**
 * Login helper for the app (keeps the user-provided password/value intact, unchanged).
 *
 * @param {Page} page - Playwright Page.
 */
async function login(page: Page): Promise<void> {
  await page.goto('http://localhost:8008/login');
  const pwd = page.getByRole('textbox', { name: 'Lösenord' });
  await pwd.click();
  await pwd.fill('adminadmin'); // kept as in the user’s original snippet
  await pwd.press('Enter');
  await page.getByRole('button', { name: 'Logga in' }).click();
  await page.waitForLoadState('networkidle');
}

/**
 * Press the global "Process" button and ensure all workflow badges go to "pending".
 *
 * @param {Page} page - Playwright Page.
 */
async function startProcessingAndWaitPending(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Process' }).click();
  await waitAllStagesPending(page);
}

/**
 * -----------------------------------------------------------------------------
 * Test
 * -----------------------------------------------------------------------------
 */

test('AI workflow reaches AI4 success with ordered stage completion and recovers from manual/error', async ({ page }) => {
  // 1) Login and open a receipt details view (mirrors user’s navigation).
  await login(page);
  await startProcessingAndWaitPending(page);

  // Open the first receipt details (stable alternative to hard-coded UUID).
  await openFirstReceiptDetails(page);

  // 2) Now drive ordered success: AI1 -> AI2 -> AI3 -> AI4
  await waitForOrderedSuccess(page);

  // 3) Verify business goal text for AI4 is present
  await expectAI4FinalText(page);
});