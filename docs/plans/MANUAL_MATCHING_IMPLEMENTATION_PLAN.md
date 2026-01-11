# Implementation Plan: Manual Matching (FirstCard ↔ Receipts/Invoices)

**Date:** 2026-01-08
**Status:** Ready for implementation
**Author:** Claude Opus 4.5
**Reference:** docs/bugs/MANUAL_MATCHING_ISSUES_2026-12-08.md

---

## Executive Summary

This plan implements manual matching functionality for the FirstCard reconciliation flow. The implementation consists of fixing a backend filter bug and rewriting the frontend to use the correct API endpoint.

### Current State Analysis

| Component | Status | Issue |
|-----------|--------|-------|
| Backend `match_status=unmatched` filter | BROKEN | Uses obsolete column `il.receipt_id` instead of `il.matched_file_id` |
| Backend PUT `/lines/<line_id>` endpoint | WORKING | Fully implemented, conflict detection works |
| Frontend ManualMatch.jsx | BROKEN | Uses wrong endpoint (POST) and wrong payload fields |
| Frontend CompanyCard.jsx | WORKING | Correct reference implementation exists |
| Backend tests | INCOMPLETE | Missing tests for unmatched filter and manual match conflict |
| Frontend E2E tests | MISSING | No Playwright tests for manual matching workflow |

---

## Step-by-Step Implementation Plan

### Step A — Backend: Fix receipts `match_status=unmatched` filter

**File:** `backend/src/api/receipts.py`

**Location:** Lines 1066-1074

**Current (broken) code:**
```python
if q_match_status == "unmatched":
    where.append(
        """u.id NOT IN (
            SELECT DISTINCT il.receipt_id
            FROM invoice_lines il
            WHERE il.receipt_id IS NOT NULL
        )"""
    )
```

**Required fix:**
```python
if q_match_status == "unmatched":
    # Receipts that are not matched to any credit card invoice line
    # Uses matched_file_id which is the correct column for matching
    where.append(
        """u.id NOT IN (
            SELECT DISTINCT il.matched_file_id
            FROM invoice_lines il
            WHERE il.matched_file_id IS NOT NULL
        )"""
    )
```

**Rationale:** The `invoice_lines` table uses `matched_file_id` (VARCHAR(36)) to store the linked unified file ID. The column `receipt_id` is obsolete and may not exist or be populated.

**Acceptance Criteria:**
- `GET /ai/api/receipts?match_status=unmatched` excludes files where `u.id` appears in any `invoice_lines.matched_file_id`
- Files with no match in invoice_lines appear in the result
- Existing pagination and sorting continue to work

---

### Step B — Frontend: Rewrite ManualMatch.jsx handleMatch function

**File:** `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`

**Location:** Lines 533-572 (handleMatch function)

**Current (broken) code:**
```javascript
const handleMatch = useCallback(async () => {
  // ...
  const payload = {
    line_id: item.id,           // ✗ Wrong field
    receipt_id: selectedReceiptId,  // ✗ Wrong field
  }
  if (item.invoice_id) {
    payload.invoice_id = item.invoice_id
  }

  const res = await api.fetch('/ai/api/reconciliation/firstcard/match', {
    method: 'POST',  // ✗ Wrong method
    // ...
  })
  // ...
})
```

**Required fix:**
```javascript
const handleMatch = useCallback(async () => {
  if (!canMatch) return
  setMatching(true)
  try {
    const item = fcItems.find((i) => i.id === selectedItemId)
    if (!item) {
      showError('Kunde inte hitta vald transaktion.')
      return
    }

    // Correct endpoint: PUT /lines/<line_id>
    // Correct payload: { matched_file_id, invoice_id }
    const res = await api.fetch(`/ai/api/reconciliation/firstcard/lines/${item.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        matched_file_id: selectedReceiptId,
        invoice_id: item.invoice_id || null,
      }),
    })

    if (res.ok) {
      showSuccess('Matchning genomförd!')
      await Promise.all([loadFcItems({ force: true }), loadReceipts()])
      setSelectedItemId(null)
      setSelectedReceiptId(null)
    } else {
      const errorData = await res.json().catch(() => ({}))
      // Handle specific error codes
      if (errorData.reason === 'receipt_in_use') {
        showError('Detta kvitto/faktura är redan matchat mot en annan rad.')
      } else if (errorData.reason === 'line_state_conflict') {
        showError('Raden kan inte matchas i nuvarande status.')
      } else {
        showError(errorData.error || errorData.reason || 'Matchning misslyckades.')
      }
    }
  } catch (err) {
    console.error('Match error', err)
    showError('Matchning misslyckades.')
  } finally {
    setMatching(false)
  }
}, [canMatch, fcItems, selectedItemId, selectedReceiptId, loadFcItems, loadReceipts])
```

**Acceptance Criteria:**
- Uses PUT method to `/ai/api/reconciliation/firstcard/lines/<line_id>`
- Sends `matched_file_id` (not `receipt_id`)
- Sends `invoice_id` when available
- Shows Swedish error message for 409 `receipt_in_use` conflict
- Clears selections and refreshes both lists on success

---

### Step C — Frontend: Add Confirmation Modal

**File:** `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`

**New Component Required:** Confirmation modal that appears when both selections are made.

**Requirements:**
1. Trigger: When both `selectedItemId != null` AND `selectedFileId != null`
2. Modal text: **"Vill du matcha dessa?"**
3. Modal content: Summary of both selected items
   - Left (line): date, amount, merchant/description
   - Right (file): type badge, date, amount, vendor/filename
4. Buttons: "Avbryt" (Cancel) and "Matcha" (Confirm)
5. Cancel: Close modal, keep selections
6. Confirm: Call handleMatch, close modal on success

**Implementation approach:**
```javascript
// New state
const [confirmModalOpen, setConfirmModalOpen] = useState(false)

// Effect to open modal when both selections made
useEffect(() => {
  if (selectedItemId && selectedReceiptId) {
    setConfirmModalOpen(true)
  }
}, [selectedItemId, selectedReceiptId])

// Modal JSX
{confirmModalOpen && (
  <div className="modal-overlay">
    <div className="modal-content">
      <h3>Vill du matcha dessa?</h3>
      <div className="match-summary">
        <div className="left-summary">
          <strong>Korttransaktion:</strong>
          <p>Datum: {formatDate(selectedItem?.purchase_date) || '–'}</p>
          <p>Belopp: {formatAmount(selectedItem?.amount)}</p>
          <p>Beskrivning: {selectedItem?.merchant_name || selectedItem?.description || '–'}</p>
        </div>
        <div className="right-summary">
          <strong>Kvitto/Faktura:</strong>
          <span className="badge">{selectedReceipt?.file_type}</span>
          <p>Datum: {formatDate(selectedReceipt?.purchase_datetime) || '–'}</p>
          <p>Belopp: {formatAmount(selectedReceipt?.gross_amount)}</p>
          <p>Leverantör: {selectedReceipt?.merchant || selectedReceipt?.filename || '–'}</p>
        </div>
      </div>
      <div className="modal-actions">
        <button onClick={() => setConfirmModalOpen(false)}>Avbryt</button>
        <button onClick={handleConfirmMatch} className="btn-primary">Matcha</button>
      </div>
    </div>
  </div>
)}
```

---

### Step D — Backend Tests

**File:** `backend/tests/integration/test_manual_match_api.py` (extend existing)

#### Test 1: Unmatched filter excludes matched files

```python
def test_receipts_unmatched_filter_uses_matched_file_id(client):
    """Verify match_status=unmatched uses invoice_lines.matched_file_id correctly."""
    # Setup: Two unified_files (u1, u2), one invoice_line matching u1
    # u1 should NOT appear in unmatched results
    # u2 SHOULD appear in unmatched results

    count_cursor = FakeCursor(fetchone_sequence=[(1,)])  # 1 result
    data_cursor = FakeCursor(fetchall_sequence=[[
        # Only u2 should be returned (u1 is matched)
        ("u2", "receipt2.pdf", "VENDOR2", "2025-10-06", 200.0, 250.0,
         "ocr_done", "receipt", "receipt", "user1", "2025-10-06",
         None, None, None, "office", None, None, None, "", None)
    ]])

    with patch("api.receipts.db_cursor", make_db_cursor([count_cursor, data_cursor])):
        resp = client.get("/receipts?match_status=unmatched")
        assert resp.status_code == 200
        payload = resp.get_json()

        # Verify only unmatched receipt appears
        ids = [item["id"] for item in payload["items"]]
        assert "u2" in ids
        assert "u1" not in ids  # u1 is matched
```

#### Test 2: Manual match endpoint success

```python
def test_manual_match_line_success(client):
    """Verify PUT /lines/<id> updates matched_file_id correctly."""
    # Setup: Line exists with matched_file_id=NULL
    line_cursor = FakeCursor(fetchone_sequence=[
        ("inv-1", "2025-10-05", 125.0),  # Line data
        None,  # No conflict
        (None,),  # Old match is NULL
    ])

    with patch("api.reconciliation_firstcard.routes.matching.db_cursor",
               make_db_cursor([line_cursor])), \
         patch("api.reconciliation_firstcard.routes.matching.transition_line_status_and_link",
               return_value=True), \
         patch("api.reconciliation_firstcard.routes.matching.log_line_history"), \
         patch("api.reconciliation_firstcard.routes.matching.refresh_invoice_match_state",
               return_value=(2, 1)), \
         patch("api.reconciliation_firstcard.routes.matching._backfill_receipt_card_from_fc"):

        resp = client.put("/reconciliation/firstcard/lines/101", json={
            "matched_file_id": "rec-1",
            "invoice_id": "inv-1"
        })

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["ok"] is True
```

#### Test 3: Manual match conflict (receipt_in_use)

```python
def test_manual_match_line_conflict(client):
    """Verify PUT /lines/<id> returns 409 when receipt already matched."""
    # Setup: Line exists, but rec-1 is already matched to another line
    line_cursor = FakeCursor(fetchone_sequence=[
        ("inv-1", "2025-10-05", 125.0),  # Line data
        (999,),  # Conflict: another line (999) has this receipt
    ])

    with patch("api.reconciliation_firstcard.routes.matching.db_cursor",
               make_db_cursor([line_cursor])):

        resp = client.put("/reconciliation/firstcard/lines/101", json={
            "matched_file_id": "rec-1",
            "invoice_id": "inv-1"
        })

        assert resp.status_code == 409
        payload = resp.get_json()
        assert payload["ok"] is False
        assert payload["reason"] == "receipt_in_use"
```

---

### Step E — Frontend E2E Tests (Playwright)

**File:** `web/tests/manual-match.spec.ts` (new file)

#### Test 1: Selection triggers confirmation modal

```typescript
import { test, expect } from '@playwright/test'

test.describe('Manual Match @manual-match', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to manual match page
    await page.goto('/manual-match')
    await page.waitForLoadState('networkidle')
  })

  test('selecting both sides triggers confirmation modal', async ({ page }) => {
    // Select a statement first
    const statementDropdown = page.locator('select').first()
    await statementDropdown.selectOption({ index: 1 })

    // Wait for left lines to load
    await page.waitForSelector('[data-testid="fc-lines-table"] tbody tr')

    // Wait for right receipts to load
    await page.waitForSelector('[data-testid="receipts-table"] tbody tr')

    // Select a receipt on the right
    const firstReceiptCheckbox = page.locator('[data-testid="receipts-table"] tbody tr:first-child input[type="checkbox"]')
    await firstReceiptCheckbox.click()

    // Select a line on the left
    const firstLineCheckbox = page.locator('[data-testid="fc-lines-table"] tbody tr:first-child input[type="checkbox"]')
    await firstLineCheckbox.click()

    // Verify confirmation modal appears
    await expect(page.locator('text=Vill du matcha dessa?')).toBeVisible()
  })
})
```

#### Test 2: Confirm performs match and refreshes UI

```typescript
test('confirm button performs match and refreshes UI', async ({ page }) => {
  // Setup: Select statement, then both items
  const statementDropdown = page.locator('select').first()
  await statementDropdown.selectOption({ index: 1 })
  await page.waitForSelector('[data-testid="fc-lines-table"] tbody tr')
  await page.waitForSelector('[data-testid="receipts-table"] tbody tr')

  // Select both sides
  await page.locator('[data-testid="receipts-table"] tbody tr:first-child input[type="checkbox"]').click()
  await page.locator('[data-testid="fc-lines-table"] tbody tr:first-child input[type="checkbox"]').click()

  // Wait for modal
  await page.waitForSelector('text=Vill du matcha dessa?')

  // Intercept the PUT request
  const matchPromise = page.waitForResponse(response =>
    response.url().includes('/ai/api/reconciliation/firstcard/lines/') &&
    response.request().method() === 'PUT'
  )

  // Click confirm
  await page.locator('button:has-text("Matcha")').click()

  // Verify PUT request was made
  const response = await matchPromise
  expect(response.status()).toBe(200)

  // Verify modal closes
  await expect(page.locator('text=Vill du matcha dessa?')).not.toBeVisible()

  // Verify success message
  await expect(page.locator('text=Matchning genomförd')).toBeVisible()
})
```

#### Test 3: Conflict shows Swedish error message

```typescript
test('conflict shows Swedish error message', async ({ page }) => {
  // Mock 409 response for the PUT endpoint
  await page.route('**/ai/api/reconciliation/firstcard/lines/*', async route => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ ok: false, reason: 'receipt_in_use' })
      })
    } else {
      await route.continue()
    }
  })

  // Select statement and both items
  const statementDropdown = page.locator('select').first()
  await statementDropdown.selectOption({ index: 1 })
  await page.waitForSelector('[data-testid="fc-lines-table"] tbody tr')
  await page.waitForSelector('[data-testid="receipts-table"] tbody tr')

  await page.locator('[data-testid="receipts-table"] tbody tr:first-child input[type="checkbox"]').click()
  await page.locator('[data-testid="fc-lines-table"] tbody tr:first-child input[type="checkbox"]').click()

  await page.waitForSelector('text=Vill du matcha dessa?')
  await page.locator('button:has-text("Matcha")').click()

  // Verify Swedish error message
  await expect(page.locator('text=Detta kvitto/faktura är redan matchat mot en annan rad')).toBeVisible()
})
```

---

### Step F — Non-Regression Verification

**File:** `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

**Action:** NO CHANGES REQUIRED

**Verification:**
- Run existing tests: `npx playwright test kortmatchning-kontoutdrag-table-structure.spec.ts --headed`
- Verify CompanyCard still uses:
  - `assignCandidate` function with PUT to `/lines/${lineId}`
  - Correct payload: `{ matched_file_id: receiptId }`
- Ensure no shared code was accidentally modified

---

## File Change Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/src/api/receipts.py` | FIX | Change `il.receipt_id` to `il.matched_file_id` in unmatched filter |
| `main-system/app-frontend/src/ui/pages/ManualMatch.jsx` | REWRITE | Fix handleMatch endpoint, add confirmation modal |
| `backend/tests/integration/test_manual_match_api.py` | EXTEND | Add 3 new test cases |
| `web/tests/manual-match.spec.ts` | NEW | Create E2E tests for manual matching |

---

## Verification Commands

### Backend Tests
```bash
docker compose exec -e PYTHONPATH=/app ai-api pytest -q backend/tests/integration/test_manual_match_api.py -v
```

### Frontend E2E Tests
```bash
# Development (port 5169)
npx playwright test web/tests/manual-match.spec.ts --config=playwright.dev.config.ts --headed

# Production (port 8008)
npx playwright test web/tests/manual-match.spec.ts --headed
```

### Manual Smoke Test
1. Upload a FirstCard PDF → verify statements exist
2. Navigate to `/manual-match`
3. Select a statement from dropdown
4. Verify left column shows invoice lines
5. Verify right column shows receipts/invoices
6. Select one receipt, then one line
7. Verify "Vill du matcha dessa?" modal appears
8. Click "Matcha"
9. Verify success message
10. Verify line now shows as matched
11. Verify receipt no longer appears in "unmatched only" filter

---

## Completion Criteria

- [ ] Backend: `match_status=unmatched` uses `invoice_lines.matched_file_id`
- [ ] Backend: All 3 new tests pass
- [ ] Frontend: ManualMatch uses PUT to `/lines/<id>` with `matched_file_id`
- [ ] Frontend: Confirmation modal shows "Vill du matcha dessa?"
- [ ] Frontend: 409 conflict shows Swedish error message
- [ ] Frontend: All 3 E2E tests pass
- [ ] CompanyCard.jsx unchanged and tests still pass
- [ ] Manual smoke test verified

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking CompanyCard | Run existing tests, no shared code changes |
| Database column mismatch | Verified `matched_file_id` exists in schema |
| Existing matches lost | Fix is additive, no data migration needed |
| Frontend state issues | Use existing working CompanyCard as reference |

---

## Estimated Scope

- Backend fix: 1 line change
- Backend tests: 3 new test functions (~60 lines)
- Frontend rewrite: ~100 lines (handleMatch + modal)
- E2E tests: ~100 lines (3 test cases)
- **Total:** ~260 lines of code changes
