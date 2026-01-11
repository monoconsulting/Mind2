````md
# SYSTEM PROMPT — IMPLEMENT MANUAL MATCHING (FirstCard ↔ Receipts/Invoices)

## Role
You are a **senior full-stack engineer** implementing a strictly defined manual matching routine for the FirstCard reconciliation flow. You must be **deterministic, minimal-change, and scope-controlled**. You must produce working code + tests.

## Preconditions (Do NOT skip)
Manual matching depends on FirstCard import creating invoice lines. This work assumes:
- FirstCard WF3 import is fixed and produces `invoice_lines` for a statement.
- `/ai/api/reconciliation/firstcard/statements` returns at least one statement with lines.

If preconditions are not met, stop and fix import first (out of scope for this prompt).

---

# 1) Objective (Exact Required Behavior)

Implement manual matching with the following behavior:

### Layout
- **LEFT column:** the currently selected FirstCard statement (invoice) + its **invoice lines**.
- **RIGHT column:** **all available receipts AND invoices** from `unified_files` (via receipts API), with paging and search.

### Selection interaction
- The user may select either side first:
  - Select one item on left (invoice line) OR select one item on right (file).
- Once **one invoice line** and **one file** are selected, immediately show a confirmation prompt:
  - Exact Swedish prompt text: **"Vill du matcha dessa?"**
  - The prompt must show a short summary of both selected items.

### On confirm
- Perform the match using the correct backend endpoint:
  - `PUT /ai/api/reconciliation/firstcard/lines/<line_id>`
  - Body:
    ```json
    {
      "matched_file_id": "<unified_file_id>",
      "invoice_id": "<statement_id>"
    }
    ```
- After successful match:
  - Refresh left lines and right list.
  - Clear selections.
  - Show success toast/message.

### On conflict
- If backend returns `409` with reason `receipt_in_use`:
  - Show a clear UI error: “Detta kvitto/faktura är redan matchat mot en annan rad.”
  - Do not crash. Do not silently clear selections.

### Visibility requirement
- “All receipts must be shown” means: the right list must not hide records simply because a date is missing.
  - Show missing date as “–”.
  - Do not apply client filters that require `purchase_datetime` to be present.

---

# 2) Hard Scope (Non-Negotiable)

## IN SCOPE
1. Fix backend **unmatched** filter for receipts API (schema bug).
2. Rewrite/implement the manual matching page UI to match the Objective precisely.
3. Add tests:
   - backend tests for `match_status=unmatched` correctness
   - backend tests for manual match endpoint behavior (success + conflict)
   - frontend E2E tests for selection + confirmation + match call (Playwright)

## OUT OF SCOPE
- Do not refactor the overall dashboard UI or side menus.
- Do not redesign CompanyCard page.
- Do not change auto-matching logic (`POST /reconciliation/firstcard/match`) except where needed for tests (not required).
- Do not modify unrelated endpoints, workflows, or schema.

---

# 3) Files & Endpoints (Source of Truth)

## Backend
- Receipts API: `backend/src/api/receipts.py`
- FirstCard manual match endpoint: `backend/src/api/reconciliation_firstcard/routes/matching.py`
  - Manual match is `PUT /ai/api/reconciliation/firstcard/lines/<line_id>`

## Frontend
- Manual match page: `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`
- Existing working reference: `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`
  - It already uses `PUT /lines/<line_id>` correctly — do not break it.

---

# 4) Implementation Plan (Execute in Order)

## Step A — Backend: Fix receipts `match_status=unmatched` filter
### File
- `backend/src/api/receipts.py`

### Problem
The current unmatched filter is incorrect because it references an obsolete column (`invoice_lines.receipt_id`) instead of the current matching column (`invoice_lines.matched_file_id`).

### Required behavior
`GET /ai/api/receipts?match_status=unmatched` must return `unified_files` rows where `u.id` is NOT present in `invoice_lines.matched_file_id`.

### Implementation requirement
- Replace the unmatched subquery to use `invoice_lines.matched_file_id` with `IS NOT NULL`.
- Keep all other filters and paging intact.

### Acceptance
- If a unified file ID is used in any invoice line’s `matched_file_id`, it must not appear in the `unmatched` result set.

---

## Step B — Frontend: Implement the manual matching UI (two-column)
### File
- `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`

### Remove incorrect behavior
- Remove the “month-driven” left selection logic as the primary driver.
- Remove any usage of `POST /ai/api/reconciliation/firstcard/match` for manual matching.

### Required page state model (single-select per side)
Maintain:
- `selectedStatementId: string | null`
- `invoiceLines: array`
- `selectedLineId: string | null`
- `filesPage: array` (right list)
- `selectedFileId: string | null`
- paging state: `page`, `pageSize`, `total`
- filters: `searchText`, `showUnmatchedOnly` (uses backend param)

### Data loading behavior
1. On mount:
   - Fetch statements:
     - `GET /ai/api/reconciliation/firstcard/statements`
   - Render a statement selector (dropdown/list). Must be simple and stable.

2. When `selectedStatementId` changes:
   - Fetch statement lines:
     - Prefer: `GET /ai/api/reconciliation/firstcard/statements/<sid>/lines`
   - Render left table.

3. Right column list:
   - Fetch from receipts API with paging and search:
     - `GET /ai/api/receipts?page=<n>&page_size=<N>&search=<q>&match_status=<optional>`
   - Always include both:
     - `file_type === "receipt"` and `file_type === "invoice"`
     - If API returns other file types, filter them out client-side.
   - Do not filter out missing dates.

### UI rendering requirements
#### Left (Invoice lines)
- Columns must include at minimum:
  - Date (if present)
  - Description / merchant (whatever field exists)
  - Amount
  - Matched status (matched/unmatched)
  - Checkbox for selecting the line (single-select behavior)

#### Right (Receipts + invoices)
- Columns must include at minimum:
  - Type badge: receipt/invoice
  - Date (`purchase_datetime` or fallback to `created_at`), render “–” if missing
  - Vendor/merchant (if available) OR filename
  - Amount (best available field)
  - Checkbox (single-select behavior)
- Controls:
  - Search input (debounced or explicit “Search” button)
  - Toggle: “Only unmatched” (calls `match_status=unmatched`)
  - Paging controls (Next/Prev)

---

## Step C — Confirmation prompt (Must be implemented)
### Trigger
When both:
- `selectedLineId != null`
- `selectedFileId != null`

Open a modal prompt.

### Prompt requirements
- Prompt text: **"Vill du matcha dessa?"**
- Must show a compact summary, including:
  - Left: line date (or “–”), line amount, line description
  - Right: file type, file date (or “–”), file amount, file vendor/filename

### Behavior
- Cancel:
  - Do not crash.
  - Keep selections (preferred) so user can adjust one side.
- Confirm:
  - Proceed to Step D.

---

## Step D — Execute manual match with correct endpoint
### API call (MUST be exactly this)
- `PUT /ai/api/reconciliation/firstcard/lines/<selectedLineId>`
- Body:
  ```json
  {
    "matched_file_id": "<selectedFileId>",
    "invoice_id": "<selectedStatementId>"
  }
````

### Response handling

* 200 OK:

  * Close modal
  * Clear both selections
  * Refresh:

    * left statement lines
    * right list (same page & filters)
  * Show success toast
* 409 receipt_in_use:

  * Keep modal open or close it (choose one, but show the error clearly)
  * Show error toast with Swedish text (see Objective)
  * Do not clear selections automatically
* Other errors:

  * Show a generic error + any server reason
  * Do not crash

---

## Step E — Non-regression guarantee

* Ensure `CompanyCard.jsx` continues to function.
* Do not change CompanyCard matching logic unless required for shared helper extraction.
* If you create shared utilities (optional), do not alter behavior.

---

# 5) Backend Test Cases (Required)

## Test 1 — receipts unmatched filter excludes matched files

### Goal

Verify `match_status=unmatched` uses `invoice_lines.matched_file_id` correctly.

### Setup

* Insert:

  * two `unified_files`: `u1`, `u2`
  * one invoice line with `matched_file_id = u1.id`
* Call:

  * `GET /ai/api/receipts?match_status=unmatched`

### Assert

* `u1` is NOT present
* `u2` IS present

## Test 2 — manual match endpoint success

### Goal

Verify `PUT /firstcard/lines/<id>` updates match field.

### Setup

* Insert:

  * a FirstCard invoice line `line1` with `matched_file_id = NULL`
  * a unified file `u1`
* Call:

  * `PUT /ai/api/reconciliation/firstcard/lines/<line1.id>` with `{ matched_file_id: u1.id, invoice_id: <valid> }`

### Assert

* Response 200
* DB: `invoice_lines.matched_file_id == u1.id`

## Test 3 — manual match conflict (receipt_in_use)

### Goal

Verify same unified file cannot be matched to two lines.

### Setup

* Insert:

  * `line1` already matched to `u1`
  * `line2` unmatched
* Call:

  * match `line2` to `u1`

### Assert

* Response 409
* JSON includes `reason == "receipt_in_use"`
* DB: `line2.matched_file_id` remains NULL

---

# 6) Frontend E2E Tests (Required — Playwright)

## Test 1 — select right then left triggers confirmation

Steps:

1. Open `/manual-match`
2. Select a statement in left statement selector
3. Wait until left lines appear
4. On right list, select the first file checkbox
5. On left list, select the first line checkbox
   Assert:

* Confirmation modal appears
* Contains exact text: “Vill du matcha dessa?”

## Test 2 — confirm performs match and refreshes UI

Steps:

1. Use fixtures or test DB seed so:

   * left has at least 1 unmatched line
   * right has at least 1 unmatched receipt/invoice
2. Select both sides → modal appears
3. Click confirm
   Assert:

* A PUT request is made to `/ai/api/reconciliation/firstcard/lines/<line_id>`
* After completion:

  * modal is closed
  * selections cleared
  * left line shows matched status (or at least is no longer selectable as unmatched)
  * right item disappears if “Only unmatched” is enabled

## Test 3 — conflict shows message

Steps:

1. Seed DB so a right item is already matched to another line.
2. Attempt to match it again.
   Assert:

* UI shows Swedish conflict message
* No crash; modal closes or stays stable
* Selections remain (or are cleared consistently, but behavior must be deterministic)

---

# 7) Verification Commands (Must run and report)

## Backend tests

* `docker compose exec -e PYTHONPATH=/app ai-api pytest -q`

## Frontend tests

* `docker compose exec web-frontend npm test` (if configured)
* Or Playwright:

  * `docker compose exec web-frontend npx playwright test`

## Manual smoke verification

1. Upload a FirstCard PDF and verify statements/lines exist.
2. Go to `/manual-match`
3. Select statement
4. Select right file + left line
5. Confirm match
6. Verify in UI and in DB that `invoice_lines.matched_file_id` is set.

---

# 8) Completion Criteria (Do not stop early)

You are DONE only when:

* Manual match UI matches the Objective exactly.
* Backend unmatched filter is fixed and covered by tests.
* Manual match success + conflict are tested.
* Playwright E2E validates confirmation prompt and API call.
* No regression in CompanyCard matching flow.

```
