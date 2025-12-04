Here’s a concrete, “do-this-exactly” plan that covers **both** the migration bug and the status mismatch (dropdown vs status column vs log). Everything is written as if you’re giving it straight to your implementation agents.

---

## 1. Technical Summary (for agent context)

**You (the agent) are working in this repo structure:**

* `database/migrations/…`
* `backend/src/services/db/migrations.py`
* `backend/src/services/status_constants.py`
* `backend/src/services/invoice_status.py`
* `backend/src/api/receipts.py`
* `backend/src/api/reconciliation_firstcard/routes/log.py`
* `backend/src/api/reconciliation_firstcard/routes/status.py`
* `backend/src/api/reconciliation_firstcard/routes/…`
* `main-system/app-frontend/src/ui/pages/Process.jsx`
* `shared/status_definitions.json`
* `docs/MIND_STATUS_DEFINITIONS.md`

### 1.1. Known hard bug – migrations (A3)

* In `database/migrations/` there are **duplicate 0031 prefixes**:

  * `0031_add_ocr_raw_to_creditcard_invoices.sql` (must remain active)
  * `0031_create_workflow_tracking.sql` (must be deprecated)
  * Workflow tracking has a newer canonical migration: `0042_create_workflow_tracking.sql`.

* `backend/src/services/db/migrations.py` enforces **unique 4-digit prefixes** for all **non-deprecated** `.sql` files.

* Because `0031_create_workflow_tracking.sql` is *not* marked as deprecated, the migration validator raises `ValueError("Duplicate migration prefix detected: 0031")`.

* `_maybe_apply_migrations()` in `backend/src/api/app.py` swallows this error silently → **DB migrations never finish** → schema may be incomplete → system misbehaves.

### 1.2. Status discrepancies (Process view & log)

You need to understand the three main “status sources” that are currently diverging:

1. **Database fields**

   * `unified_files.ai_status` (values should match `AiStatus` enum).
   * `invoice_documents.processing_status` (`InvoiceProcessingStatus`).
   * `invoice_documents.status` (`InvoiceDocumentStatus`).
   * `invoice_lines.match_status` (`InvoiceLineMatchStatus`).
   * `workflow_runs.status` / `workflow_stage_runs.status`.
   * `ai_processing_history.status`.

2. **Backend usage**

   * `backend/src/services/status_constants.py` defines:

     * `InvoiceProcessingStatus`, `InvoiceDocumentStatus`, `InvoiceLineMatchStatus`,`AiStatus`.
   * `backend/src/api/receipts.py::list_receipts()`:

     * Reads query param `status` into `q_status`.
     * Uses it **only** to filter: `WHERE ai_status = %s`.
     * Selects `u.ai_status` and returns it as **both**:

       * `"status": status`
       * `"ai_status": status`
     * Determines `workflow_stage_status` from `workflow_stage_runs` (subquery).
   * `backend/src/api/reconciliation_firstcard/routes/log.py`:

     * Reads `workflow_runs.status`, `workflow_stage_runs.status`, and `ai_processing_history.status` and sends them straight to frontend.

3. **Frontend usage (Process page)**

   * `main-system/app-frontend/src/ui/pages/Process.jsx`:

     * Imports `statusDefinitions` from `shared/status_definitions.json`, but:

       * **Dropdown options** are hard-coded in `const statusOptions = […]` (not generated from JSON).
     * Dropdown **“Status”** uses `statusOptions` and stores selection in `filters.status`.
     * In `loadReceipts()`:

       * If `filters.status.startsWith('stage:')` → `params.set('status', filters.status.slice(6))`
         (so `stage:src_portal` becomes `status=src_portal`).
       * If `filters.status === 'status:completed'` → `params.set('status', 'passed')`.
         (This is wrong for `AiStatus`, which uses `'completed'`, not `'passed'`.)
       * If `filters.status === 'status:!completed'` → `params.set('status', '!passed')`.
       * If `filters.status === 'match_status:unmatched'` → `params.set('ai_status', 'unmatched')`.
       * If `filters.status === 'status:manual_review'` → `params.set('status', 'manual_review')`.
       * Else → `params.set('status', filters.status)`.
     * **Status column** in the table:

       ```jsx
       <StatusBadge
         status={receipt.workflow_stage_status || receipt.status || receipt.ai_status}
         stageKey={receipt.workflow_stage_key}
         stageStatus={receipt.workflow_stage_state}
       />
       ```

       * So the displayed “Status” uses:

         * First `workflow_stage_status` (e.g. `"src_portal running"`, `"ai3_completed"`, etc.)
         * Fallback `receipt.status` (= `ai_status`)
         * Fallback `receipt.ai_status`.
     * **Log modal**:

       * Shows `run.status`, `stage.status`, and `entry.status` from workflow and AI history.

**Resulting discrepancy:**

* The **dropdown “Status”** filter is mixing:

  * Stage filters (`stage:src_*`), mapped incorrectly to `status` query param.
  * Meta business filters (`status:completed`) mapped to `status=passed` which does **not** match `AiStatus`.
* The **Status column** shows workflow stage or `ai_status`.
* The **log view** shows workflow/AI history statuses from other tables.
* They are not all driven from a single, canonical status definition.

---

## 2. Goals

1. **Fix migration A3** so migrations run cleanly and the schema is complete.
2. **Make all user-visible statuses derive from a single canonical source**:

   * `docs/MIND_STATUS_DEFINITIONS.md`
   * `shared/status_definitions.json`
   * `backend/src/services/status_constants.py`
3. **Align Process view**:

   * The dropdown “Status” should filter on the same concepts that the Status column and log represent.
   * Stage filters must filter by workflow stage, not by `ai_status`.
   * Business-state filters must filter by `AiStatus` (e.g. `completed`, `failed`, `manual_review`, etc.).
4. **Keep behaviour backwards-compatible where possible**, but fix obviously wrong mappings (e.g. `'status:completed' → 'passed'`).

---

## 3. AGENT PLAN – Step-by-step with explicit prompts

### Agent 1: MIGRATION_A3_FIX

**Objective:**
Make `database/migrations/` pass the migration validator by removing the active duplicate `0031_create_workflow_tracking.sql` and leaving `0042_create_workflow_tracking.sql` as the canonical workflow-tracking migration.

**Key files:**

* `database/migrations/0031_add_ocr_raw_to_creditcard_invoices.sql`
* `database/migrations/0031_create_workflow_tracking.sql`
* `database/migrations/0042_create_workflow_tracking.sql`
* `backend/src/services/db/migrations.py`
* `backend/tests/unit/test_migrations_dir.py`
* `backend/tests/unit/test_migrations_ordering.py`

**Constraints:**

* Do **not** renumber any existing migrations.
* Do **not** edit any other migration file except `0031_create_workflow_tracking.sql`.
* `0031_add_ocr_raw_to_creditcard_invoices.sql` must remain **active**.
* `0042_create_workflow_tracking.sql` must remain the canonical file for workflow-tracking tables.
* The validator in `migrations.py` already ignores “deprecated” migrations if the first non-empty line starts with `-- Deprecated migration`.

#### Steps for Agent 1

1. **Convert `0031_create_workflow_tracking.sql` into a deprecated stub**

   * Open `database/migrations/0031_create_workflow_tracking.sql`.

   * Replace the top of the file with:

     ```sql
     -- Deprecated migration (2025-11-26)
     -- This migration has been replaced by database/migrations/0042_create_workflow_tracking.sql
     -- It is kept only for historical reference.
     -- The original SQL content has been commented out below.
     ```

   * Comment out **all remaining SQL** in the file by prefixing each line with `-- `.

2. **Leave `0031_add_ocr_raw_to_creditcard_invoices.sql` unchanged.**

3. **Leave `0042_create_workflow_tracking.sql` unchanged.**

4. **Add a unit test that fails on future duplicate non-deprecated prefixes**

   * In `backend/tests/unit/test_migrations_dir.py` (or create it if missing), add a test that:

     * Scans `database/migrations/*.sql`.
     * Skips any file whose first non-empty line starts with `-- Deprecated migration`.
     * Fails if any 4-digit prefix is used by more than one non-deprecated file.

5. **Run tests and verify**

   * Run backend unit tests (especially migration tests).
   * Confirm:

     * No `ValueError: Duplicate migration prefix detected` from `list_migration_files()`.
     * No other migration validation failures.

#### Prompt for Agent 1 (copy-paste)

> **ROLE:** MIGRATION_A3_FIX_AGENT
> **GOAL:** Fix duplicate migration prefix `0031` and enforce future uniqueness for non-deprecated migrations.
>
> **Context:**
>
> * Repo root contains `database/migrations` and `backend/src/services/db/migrations.py`.
> * Current bug: both `0031_add_ocr_raw_to_creditcard_invoices.sql` and `0031_create_workflow_tracking.sql` have active SQL and share the same prefix. `migrations.py` enforces unique prefixes and treats non-deprecated `.sql` files as active migrations. This causes `ValueError("Duplicate migration prefix detected: 0031")` and prevents migrations from completing.
> * `0042_create_workflow_tracking.sql` is the new canonical workflow-tracking migration. `0031_create_workflow_tracking.sql` must be kept for history but not be treated as an active migration.
>
> **Requirements:**
>
> 1. In `database/migrations/0031_create_workflow_tracking.sql`:
>
>    * Add a header where the first non-empty line starts with `-- Deprecated migration (2025-11-26)` and explicitly states that it is replaced by `0042_create_workflow_tracking.sql`.
>    * Comment out all original SQL content so that the file is effectively a no-op stub.
> 2. Do **not** modify `0031_add_ocr_raw_to_creditcard_invoices.sql` or `0042_create_workflow_tracking.sql`.
> 3. Add a unit test in `backend/tests/unit/test_migrations_dir.py` that:
>
>    * Scans `database/migrations/*.sql`.
>    * Ignores any file whose first non-empty line starts with `-- Deprecated migration`.
>    * Asserts that each 4-digit prefix is unique among non-deprecated files.
> 4. Run backend tests and ensure:
>
>    * Migration validation passes.
>    * No duplicate-prefix error is raised.
>
> **Do NOT:**
>
> * Renumber any migration.
> * Delete any migration file.
> * Change the migration directory layout.
>
> **Deliverables:**
>
> * Updated `0031_create_workflow_tracking.sql` as a fully-commented deprecated stub.
> * A passing unit test that would have caught this duplicate-prefix problem.

---

### Agent 2: STATUS_BACKEND_ALIGNMENT

**Objective:**
Make backend status handling consistent and compatible with:

* `docs/MIND_STATUS_DEFINITIONS.md`
* `shared/status_definitions.json`
* `backend/src/services/status_constants.py`

and expose status data in a way that the frontend can use consistently for:

* Process list filter.
* Status column.
* Log view.

**Key files:**

* `docs/MIND_STATUS_DEFINITIONS.md`
* `shared/status_definitions.json`
* `backend/src/services/status_constants.py`
* `backend/src/services/invoice_status.py`
* `backend/src/api/receipts.py`
* `backend/src/api/reconciliation_firstcard/routes/log.py`
* `backend/src/api/reconciliation_firstcard/routes/status.py`

#### Backend status model you must enforce

1. **Canonical enums (single source of truth):**

   * `AiStatus` in `status_constants.py` must match the “AiStatus Definitions” section in `docs/MIND_STATUS_DEFINITIONS.md`:

     * `uploaded`, `processing`, `ocr_done`, `ocr_failed`, `manual_review`, `completed`, `failed`.
   * `InvoiceProcessingStatus`, `InvoiceDocumentStatus`, `InvoiceLineMatchStatus` stay as already defined but must continue to match the docs.

2. **Receipts API `/receipts` rules:**

   **Inputs (query params) should be:**

   * `ai_status` – filters `unified_files.ai_status` using `AiStatus` values.
   * `status` – alias for `ai_status` (for backwards compatibility), **only** for AiStatus values.
   * `workflow_stage_key` – filters by latest `workflow_stage_runs.stage_key`.
   * `workflow_stage_status` (optional) – filters by `workflow_stage_runs.status` (e.g. `queued`, `running`, `succeeded`, `failed`).
   * `match_status` – filters by line match or receipt-level match status (e.g. `unmatched`).

   **Behavior to implement:**

   * If `ai_status` is present → filter `u.ai_status` accordingly.
   * Else if `status` is present and matches an `AiStatus` value or `!<AiStatus>`:

     * Map `status=<value>` to filter on `u.ai_status`.
     * For negation (e.g. `status=!completed`), filter `u.ai_status <> 'completed'`.
   * If `workflow_stage_key` is present:

     * Join `workflow_runs` and `workflow_stage_runs` (you already have a subquery for `workflow_stage_status`).
     * Filter to rows whose latest `workflow_stage_runs.stage_key` equals the given key.
   * If `match_status` is present and equals `unmatched`:

     * Apply existing logic (or new query) to return receipts that are not matched to any credit card invoice (according to your schema).

   **Output:**

   * Each receipt item returned must include:

     * `"ai_status"` – canonical AiStatus value from `unified_files.ai_status`.
     * `"status"` – kept as alias for `ai_status` for now (for frontend compatibility).
     * `"workflow_stage_status"` – string like `"stage_key status"` (as already implemented).
     * (Optional improvement) `"workflow_stage_key"` and `"workflow_stage_state"` as separate fields, if not already present.

3. **Log endpoint alignment (`reconciliation_firstcard/routes/log.py`):**

   * Make sure the payload clearly separates:

     * Workflow-run level: `workflow_runs[].status` (e.g. `queued`, `running`, `failed`, `succeeded`).
     * Stage level: `workflow_runs[].stages[].status`.
     * AI history: `ai_history[].status` (e.g. `queued`, `running`, `completed`, `failed`).
   * You do **not** need to rename these statuses, but they should be documented in `docs/MIND_STATUS_DEFINITIONS.md` (if not already) and/or added to `shared/status_definitions.json` in a `legacy` or `workflow` category.

4. **Documentation sync:**

   * Update `docs/MIND_STATUS_DEFINITIONS.md` so that:

     * The AiStatus list matches `AiStatus` enum.
     * Workflow stage keys and categories match `shared/status_definitions.json`.
   * If needed, expand `shared/status_definitions.json` with:

     * A section listing allowed AiStatus values and human-readable labels.

#### Prompt for Agent 2 (copy-paste)

> **ROLE:** STATUS_BACKEND_ALIGNMENT_AGENT
> **GOAL:** Align backend status handling with `docs/MIND_STATUS_DEFINITIONS.md`, `shared/status_definitions.json`, and `status_constants.AiStatus`, and expose consistent data for the frontend Process view and log.
>
> **Context:**
>
> * `unified_files.ai_status` should use AiStatus values: `uploaded`, `processing`, `ocr_done`, `ocr_failed`, `manual_review`, `completed`, `failed`.
> * `/receipts` currently:
>
>   * Reads `status` and uses it to filter `ai_status`.
>   * Returns `status` and `ai_status` with identical values from `u.ai_status`.
>   * Ignores stage-specific semantics in the query layer.
> * Process.jsx misuses `status` to send stage filters and also uses non-AiStatus values like `passed`.
>
> **Requirements:**
>
> 1. Make `/receipts` accept and interpret these query params:
>
>    * `ai_status` – canonical filter for `unified_files.ai_status`.
>    * `status` – backwards-compatible alias for AiStatus values **only** (including negations like `!completed`).
>    * `workflow_stage_key` – filter by latest workflow stage key.
>    * `workflow_stage_status` – optionally filter by stage status (`queued`, `running`, `succeeded`, `failed`).
>    * `match_status` – at least support `unmatched`.
> 2. Ensure the `/receipts` query:
>
>    * Filters `ai_status` only with AiStatus values.
>    * Filters workflow stages via a proper join on `workflow_runs` and `workflow_stage_runs` when `workflow_stage_key` or `workflow_stage_status` is provided.
> 3. Ensure the `/receipts` response always includes:
>
>    * `"ai_status"` – AiStatus value.
>    * `"status"` – alias for `ai_status` (keep this for now).
>    * `"workflow_stage_status"` – combined string as today.
>    * (Optional but preferred) `"workflow_stage_key"` and `"workflow_stage_state"` fields.
> 4. Ensure `docs/MIND_STATUS_DEFINITIONS.md` and `shared/status_definitions.json` are updated to match:
>
>    * AiStatus values in `status_constants.AiStatus`.
>    * Workflow stage keys and categories used in `workflow_stage_runs`.
> 5. Do **not** remove any existing status enums or rename DB columns.
>
> **Deliverables:**
>
> * Updated `/receipts` handler that cleanly separates AiStatus filtering, workflow-stage filtering, and match-status filtering.
> * Updated documentation and, if needed, updated `shared/status_definitions.json`.
> * All backend tests still passing or updated appropriately.

---

### Agent 3: STATUS_FRONTEND_ALIGNMENT (Process page + log view)

**Objective:**
Make the Process page dropdown, status column, and log modal all use the same canonical status information, consistent with backend and docs.

**Key file:**

* `main-system/app-frontend/src/ui/pages/Process.jsx`

**You must fix these concrete problems:**

* `statusOptions` is currently hard-coded and partly out-of-sync with status definitions.
* Status filter logic uses `status` param in a way that conflicts with backend semantics.
* The Status column and filters are not using the same source-of-truth as `shared/status_definitions.json`.

#### Steps for Agent 3

1. **Use `shared/status_definitions.json` as source-of-truth for stages**

   * Replace or refactor `const statusOptions = […]` so that:

     * Stage-related options are generated from `STAGE_DEFINITIONS = statusDefinitions.stageKeys`.
     * Use `CATEGORY_ORDER` and `CATEGORY_LABELS` to group and label stage filters.
   * Keep meta filters (“completed”, “not completed”, “unmatched”, “manual review”) explicitly defined at the top of the list.

2. **Fix how filters map to query params**

   In `loadReceipts()`:

   * Introduce this mapping:

     | Dropdown value pattern   | Query params to send            |
     | ------------------------ | ------------------------------- |
     | `''`                     | *Send no status-related params* |
     | `status:completed`       | `ai_status=completed`           |
     | `status:!completed`      | `ai_status=!completed`          |
     | `status:manual_review`   | `ai_status=manual_review`       |
     | `match_status:unmatched` | `match_status=unmatched`        |
     | `stage:<key>`            | `workflow_stage_key=<key>`      |

   * That means changing:

     ```js
     if (filters.status.startsWith('stage:')) {
       params.set('status', filters.status.slice(6))
     }
     ```

     into:

     ```js
     if (filters.status.startsWith('stage:')) {
       params.set('workflow_stage_key', filters.status.slice(6))
     }
     ```

   * And changing:

     ```js
     { value: 'status:completed', label: 'Slutförda (KLAR)' }
     // currently → params.set('status', 'passed')
     ```

     into:

     ```js
     // status:completed → ai_status=completed
     ```

     etc., so that you **never** send `status='passed'` to filter `ai_status`.

3. **Ensure Status column uses the same concepts**

   * Keep the existing `StatusBadge` component, but ensure:

     * If `receipt.workflow_stage_status` is present, it is parsed into:

       * `stageKey` and `stageStatus`.
       * Label/resolution should use `STATUS_LABEL_MAP` or `STAGE_DEFINITIONS` from `status_definitions.json` when possible.
     * If no workflow stage is available, fallback to the AiStatus `receipt.ai_status` and use a label mapping consistent with docs / JSON.
   * The visual badge color class map (`statusClassMap`) should support:

     * The AiStatus values (`uploaded`, `processing`, `ocr_done`, `ocr_failed`, `manual_review`, `completed`, `failed`).
     * The workflow stage states (`queued`, `running`, `succeeded`, `failed`) if they are shown.

4. **Ensure log modal labeling is consistent**

   * For `run.status`, `stage.status`, and `entry.status`:

     * If status values appear in `statusDefinitions` (e.g. stage keys or legacy statuses), use those labels.
     * Otherwise, show the raw status string but keep the style consistent with the StatusBadge type classes where appropriate.

5. **Quick checks after implementation**

   * In the Process view:

     * Selecting “Slutförda (KLAR)” filters to rows whose AiStatus is `completed`.
     * Selecting “Ej slutförda” shows everything where AiStatus is not `completed`.
     * Selecting “Ej matchade” shows only unmatched receipts.
     * Selecting a stage (e.g. “OCR”) filters to rows whose latest workflow stage key corresponds to that stage.
   * The Status column always makes sense relative to the chosen filter: there is no situation where you filter for “OCR” but the status column looks like something unrelated (e.g. `manual_review`).

#### Prompt for Agent 3 (copy-paste)

> **ROLE:** STATUS_FRONTEND_ALIGNMENT_AGENT
> **GOAL:** Align the Process page’s Status dropdown, Status column, and log modal with backend status semantics and `shared/status_definitions.json`.
>
> **Context:**
>
> * Process.jsx currently:
>
>   * Uses a hard-coded `statusOptions` array for the Status dropdown.
>   * Sends a `status` query param which is misused for workflow-stage filters and uses invalid values like `'passed'` for AiStatus.
>   * Displays status via `<StatusBadge status={receipt.workflow_stage_status || receipt.status || receipt.ai_status} … />`.
> * Backend will be updated so `/receipts` accepts:
>
>   * `ai_status`, `workflow_stage_key`, `workflow_stage_status`, `match_status`.
> * `shared/status_definitions.json` and `docs/MIND_STATUS_DEFINITIONS.md` define allowed AiStatus and stage keys.
>
> **Requirements:**
>
> 1. Refactor the Status dropdown so that:
>
>    * Stage options are generated from `statusDefinitions.stageKeys` and grouped by category.
>    * Meta options are:
>
>      * `status:completed` → “Slutförda (KLAR)”
>      * `status:!completed` → “Ej slutförda”
>      * `match_status:unmatched` → “Ej matchade”
>      * `status:manual_review` → “Manuell hantering”
> 2. Change `loadReceipts()` so that:
>
>    * `status:completed` sets `ai_status=completed`.
>    * `status:!completed` sets `ai_status=!completed`.
>    * `status:manual_review` sets `ai_status=manual_review`.
>    * `match_status:unmatched` sets `match_status=unmatched`.
>    * `stage:<key>` sets `workflow_stage_key=<key>` (and does **not** touch `status`).
>    * Do **not** send `status='passed'` or any other non-AiStatus value to filter `ai_status`.
> 3. Ensure `StatusBadge` uses:
>
>    * Workflow stage information when available, with labels from `statusDefinitions`.
>    * AiStatus values (`ai_status`) as a fallback, with correct labels and CSS class mapping.
> 4. Ensure the log modal uses the same visual vocabulary and type classes for statuses where appropriate.
>
> **Deliverables:**
>
> * A Process page where:
>
>   * Status filter and Status column are visibly consistent.
>   * Stage filters actually correspond to workflow stages.
>   * Meta status filters correspond to AiStatus values.

---
