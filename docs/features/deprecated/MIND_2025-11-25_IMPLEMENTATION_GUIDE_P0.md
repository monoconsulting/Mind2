Here’s a **very detailed, P0-only implementation plan** you can hand directly to a code agent.

It is **grounded in the current repo layout** (`database/migrations`, `backend/migrations`, `backend/src/services/db/migrations.py`, `workflow_runs`, `workflow_stage_runs`, etc.) and uses concrete file names and example code.

---

## P0 – Baseline: Migrations & Workflow Status Health

### High–level objective

1. Make **migrations** a single, validated, canonical source of truth.
2. Make **status fields** (AI, workflow, file processing) **consistent, centralized, and introspectable**, without changing behaviour.

All steps below must follow your global rules: **no deleted code**, no new “features”, and **no behaviour change**, only structure/consistency improvements.

---

## P0.1 – Canonical migrations and schema

### P0.1.0 – Files and directories involved

The agent must work with these paths:

* Migration runner:

  * `backend/src/services/db/migrations.py`
* Canonical migrations (current):

  * `database/migrations/0001_unified-migration-fixed.sql`
  * `database/migrations/0002_ai_schema_extension.sql`
  * …
  * `database/migrations/0033_add_invoice_document_soft_delete.sql`
* Extra/backend migrations:

  * `backend/migrations/0032_fix_fc_file_types.sql`
  * `backend/migrations/0033_cleanup_fc_receipt_items.sql`
  * `backend/migrations/0034_reset_fc_processing.sql`
  * `backend/migrations/0035_add_workflow_type_flag.sql`
  * `backend/migrations/0036_add_currency_column.sql`
  * `backend/migrations/0037_add_workflow_tracking_tables.sql`
  * `backend/migrations/0038_add_updated_at_to_invoice_documents.sql`
* Suspicious entries:

  * `database/migrations/0007_add_ai_accounting_proposals.sql`
  * `database/migrations/0007_add_ai_llm_tables.sql`   ← duplicate number
  * `database/migrations/0031_add_ocr_raw_to_creditcard_invoices.sql`
  * `database/migrations/0031_create_workflow_tracking.sql` ← duplicate number
  * `database/migrations/0015_QUICKSTART.md` ← non-SQL file in migrations dir

---

### P0.1.1 – Confirm canonical migrations directory & runner

**Goal:** make sure `database/migrations` is *the* canonical folder, and the runner always resolves it correctly in both dev and container.

1. Open `backend/src/services/db/migrations.py` and inspect:

   ```python
   def _resolve_migrations_dir() -> Path:
       here = Path(__file__).resolve()
       # Try repo layout: backend/src/services/db/ -> repo/database/migrations
       try:
           repo_root = here.parents[4]
           candidate = repo_root / "database" / "migrations"
           if candidate.exists():
               return candidate
       except Exception:
           pass
       # Try container layout: /app/database/migrations
       container_candidate = Path("/app/database/migrations")
       if container_candidate.exists():
           return container_candidate
       # Fallback to sibling database/migrations relative to source tree
       return here.parents[2] / "database" / "migrations"
   ```

   ```python
   MIGRATIONS_DIR = _resolve_migrations_dir()

   def list_migration_files() -> Iterable[Path]:
       return sorted(MIGRATIONS_DIR.glob("*.sql"))
   ```

2. **Constraints for the agent:**

   * `database/migrations` **remains** the canonical directory for all SQL migrations.
   * `backend/migrations` will be treated as **historical / transitional** content (see P0.1.3), not as a second live migrations tree.
   * `list_migration_files()` must continue to only pick `*.sql` files (so `0015_QUICKSTART.md` is ignored).

3. **Acceptance criteria:**

   * `_resolve_migrations_dir()` still resolves to `database/migrations` in dev (repo) and `/app/database/migrations` in container.
   * `list_migration_files()` returns a list of **only SQL** files in `database/migrations` in correct lexical order.

No functional changes here; just confirm and rely on this behaviour for the rest of P0.1.

---

### P0.1.2 – Introduce migration sequence validation

**Goal:** detect broken numbering, duplicates, and invalid filenames **before** executing SQL.

#### Step P0.1.2.a – Add a validator in `backend/src/services/db/migrations.py`

1. In `backend/src/services/db/migrations.py`, after `list_migration_files`, add a helper that:

   * Accepts the list of files.
   * Extracts the 4-digit numeric prefix from each filename (`0001`, `0002`, …).
   * Detects:

     * non-matching patterns,
     * duplicates (e.g. two `"0007_"` files),
     * gaps (optional; logging only).

   Example (illustrative; agent must adapt to the existing logging and style):

   ```python
   import re

   MIGRATION_NAME_PATTERN = re.compile(r"^(\d{4})_(.+)\.sql$")

   def validate_migration_sequence(files: Iterable[Path]) -> None:
       """
       Validate that migration files follow the expected naming convention
       (0001_name.sql, 0002_name.sql, ...) and that there are no duplicate numbers.

       Raises:
           ValueError: if invalid names or duplicate numbers are detected.
       """
       numbers = {}
       invalid = []

       for path in files:
           name = path.name
           match = MIGRATION_NAME_PATTERN.match(name)
           if not match:
               invalid.append(name)
               continue
           num = int(match.group(1))
           numbers.setdefault(num, []).append(name)

       if invalid:
           raise ValueError(
               f"Invalid migration file names in {MIGRATIONS_DIR}: {', '.join(sorted(invalid))}"
           )

       duplicate_numbers = {num: names for num, names in numbers.items() if len(names) > 1}
       if duplicate_numbers:
           details = "; ".join(
               f"{num:04d}: {', '.join(sorted(names))}"
               for num, names in sorted(duplicate_numbers.items())
           )
           raise ValueError(
               f"Duplicate migration numbers detected in {MIGRATIONS_DIR}: {details}"
           )
   ```

2. Integrate into `apply_migrations`:

   ```python
   def apply_migrations(seed_demo: bool = True) -> None:
       MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
       files = list(list_migration_files())
       validate_migration_sequence(files)

       for sql_file in files:
           logger.info(f"Applying migration: {sql_file.name}")
           ...
   ```

3. Keep all existing logic in `apply_migrations` untouched, especially:

   * The `_split_sql` function.
   * The idempotency error handling (`Duplicate column name`, `Unknown column`, etc).
   * The disabled seed block (`if False and seed_demo:`).

#### Step P0.1.2.b – Unit tests for the validator

Create a new test file, e.g.:

* `backend/tests/unit/test_migration_sequence_validation.py`

Test scenarios:

1. **Valid sequence** (no duplicates, all names match pattern):

   * Use `tmp_path` to create:

     ```text
     database/migrations/0001_init.sql
     database/migrations/0002_second.sql
     ```

   * Call `validate_migration_sequence` directly with these Paths.

   * Expect **no exception**.

2. **Invalid filename**:

   * Include `database/migrations/foo.sql` or `001_invalid.sql`.
   * Expect `ValueError` mentioning the invalid file.

3. **Duplicate numbers**:

   * Include `0007_add_ai_accounting_proposals.sql` and `0007_add_ai_llm_tables.sql`.
   * Expect `ValueError` that clearly lists both names.

Ensure tests import `validate_migration_sequence` properly using the project’s import style (e.g. `from services.db.migrations import validate_migration_sequence` relative to test configuration).

**Acceptance criteria:**

* Validator raises for duplicate number patterns present in the real tree (e.g. `0007_*`, `0031_*`).
* All unit tests pass.

---

### P0.1.3 – Reconcile duplicated and backend migrations

**Goal:** clear up confusion between `database/migrations` and `backend/migrations`, while keeping behaviour intact.

#### Step P0.1.3.a – Map backend migrations to database migrations

For each file under `backend/migrations`:

* `0032_fix_fc_file_types.sql`
* `0033_cleanup_fc_receipt_items.sql`
* `0034_reset_fc_processing.sql`
* `0035_add_workflow_type_flag.sql`
* `0036_add_currency_column.sql`
* `0037_add_workflow_tracking_tables.sql`
* `0038_add_updated_at_to_invoice_documents.sql`

Perform:

1. Check whether its SQL content is already represented (identical or equivalent) in any `database/migrations/00XX_*.sql`.

   * For example, `backend/migrations/0037_add_workflow_tracking_tables.sql` and `database/migrations/0031_create_workflow_tracking.sql` both create `workflow_runs` and `workflow_stage_runs`.

2. If a backend migration is **unique** (not present under `database/migrations`):

   * Create a **new** migration in `database/migrations` with the next free number (e.g. `0034_*` if `0033` is the last).
   * Copy the SQL body from the backend migration into this new file.
   * Leave the original `backend/migrations/003X_*.sql` file **unchanged** in content, but add a top comment:

     ```sql
     -- Deprecated duplicate migration.
     -- This file has been superseded by database/migrations/00YY_descriptive_name.sql.
     -- Kept for historical reference only; not used by the migration runner.
     ```

3. If a backend migration is **semantically duplicated** by an existing `database/migrations/0031_create_workflow_tracking.sql` (or similar):

   * Do **not** create a new migration.
   * Document the duplication at the top of the backend file as above, pointing to the canonical `database/migrations` file.

4. Ensure that **only** `database/migrations` is used by `apply_migrations`. Do **not** change the runner to touch `backend/migrations`.

#### Step P0.1.3.b – Resolve duplicate numbers in `database/migrations`

Specific duplicates:

* `0007_add_ai_accounting_proposals.sql`
* `0007_add_ai_llm_tables.sql`
* `0031_add_ocr_raw_to_creditcard_invoices.sql`
* `0031_create_workflow_tracking.sql`

The goal is **not** to change the executed SQL order in production (where the schema already exists), but to make future runs sane.

Recommended approach:

1. Decide canonical order based on actual feature dependencies:

   * For `0007` pair:

     * If both migrations are meant to be applied, choose a new number for one of them. For instance:

       * Keep `0007_add_ai_accounting_proposals.sql` as `0007`.
       * Rename `0007_add_ai_llm_tables.sql` to `0008_add_ai_llm_tables.sql`, and shift subsequent numbers if necessary **only forward**.
   * For `0031` pair:

     * If `workflow_tracking` is more foundational, keep:

       * `0031_create_workflow_tracking.sql` as `0031`.
       * Rename `0031_add_ocr_raw_to_creditcard_invoices.sql` to `0032_add_ocr_raw_to_creditcard_invoices.sql` (again, updating future numbers if possible).

2. In practice, because production DBs already have all columns/tables, renaming the files and reordering them will **not** break anything:

   * The migration system is idempotent:

     * `apply_migrations` ignores “Duplicate column name”, “already exists”, etc.
   * So changed order is acceptable as long as the final schema is the same.

3. Implement the renames as **new files** rather than editing/removing the originals:

   * Keep the **original** `0007_*.sql` and `0031_*.sql` in place but **do not run them**.

   * For each original with a conflicting number:

     * Create a new file with a non-conflicting number (e.g. `0034_...sql`) and copy the SQL body.
     * Inside the original file, comment out the SQL and add a header:

       ```sql
       -- Deprecated: superseded by 0034_add_ocr_raw_to_creditcard_invoices.sql
       -- Kept for historical reference only; do NOT include in new deployments.
       ```

   * Then, ensure `validate_migration_sequence` only sees the **non-deprecated** files:

     * Two options:

       * Either physically move deprecated files out of `database/migrations` (e.g. to `database/migrations/deprecated/`).
       * Or rename them to `0007_add_ai_accounting_proposals.deprecated.sql` (no longer matching `*.sql` glob) and keep comments inside.

   **Important:** the agent must not remove content; only comment/rename in a way that prevents accidental execution.

4. Run `validate_migration_sequence` in a dev environment and ensure:

   * No duplicate numbers remain.
   * All remaining `*.sql` files follow `NNNN_*` naming.

#### Step P0.1.3.c – Non-SQL file in migrations directory

There is a documentation file:

* `database/migrations/0015_QUICKSTART.md`

`list_migration_files()` already uses:

```python
return sorted(MIGRATIONS_DIR.glob("*.sql"))
```

So the `.md` file is not executed. We still want to make intent clear:

1. **Do not delete or move it**, but add a prominent comment **inside the `.md` itself** explaining:

   * That it is documentation.
   * That it must never be renamed to `.sql`.

   For example, at the top of `0015_QUICKSTART.md`:

   ```markdown
   > NOTE: This file is documentation only.
   > It intentionally lives in database/migrations to stay close to schema evolution,
   > but is never executed because the migration runner only loads `*.sql` files.
   > Do NOT rename this file to `.sql`.
   ```

2. Optionally, add a short comment in `migrations.py` near `list_migration_files` noting that only `.sql` files are considered.

---

### P0.1.4 – Keep seed_demo behaviour frozen

In `apply_migrations`, you currently have:

```python
# Optional seed of a few demo rows for instant UI sanity
# NOTE: Seed data disabled - mock data is forbidden per CLAUDE.md
# If re-enabled in future, must:
# 1. Create companies first in companies table
# 2. Link via company_id, not merchant_name column (which doesn't exist)
if False and seed_demo:
    try:
        with db_cursor() as cur:
            ...
```

**Agent instructions:**

* Do **not** change this block’s semantics.
* It must remain effectively disabled (`if False and seed_demo:`).
* You may tighten the comment if you want, but do not re-enable it.

**Acceptance criteria:**

* Running `apply_migrations(seed_demo=True)` on a fresh DB does **not** insert any mock/demo data.
* The code and comments still clearly indicate demo seeding is forbidden.

---

### P0.1.5 – Verification against DB dump

To ensure migrations still produce the schema seen in your latest backup:

1. Use the `.dbbackup` dumps:

   * `.dbbackup/Mind2_mono_se_db_9_2025-11-25_12-34.sql`

2. Agent workflow for verification (conceptual, not CI-enforced here):

   * In a scratch environment:

     * Create an empty MySQL database.
     * Run `apply_migrations()` from the codebase using the **canonical** `database/migrations` only.
     * Export the resulting schema (no data) with e.g. `mysqldump --no-data`.
     * Compare high-level structure (tables, main columns, indexes) with the production dump.

3. Any differences must be analysed:

   * If production has extra columns/tables that are not covered by migrations:

     * Add new migration(s) that bring the canonical schema in line with production.
   * If migrations create something that doesn’t exist in production:

     * Confirm if that’s expected (e.g. new feature not yet deployed).
     * If not expected, add a corrective migration (e.g. drop unused columns) but only if this matches your current architecture decisions.

**Acceptance criteria:**

* Canonical migration chain from `0001_` to the last migration yields a schema compatible with the latest production dump.

---

## P0.2 – Workflow & status consistency

### P0.2.0 – Files and tables involved

Code modules:

* Status usage in scripts:

  * `backend/check_status.py`
  * `backend/check_workflows.py`
  * `backend/resume_all_uploaded.py`
  * `backend/set_workflow_type_fc.py`
* API endpoints (status usage):

  * `backend/src/api/app.py`
  * `backend/src/api/ai_processing.py`
  * `backend/src/api/receipts.py`
  * `backend/src/api/export.py`
  * `backend/src/api/fetcher.py`
  * `backend/src/api/ingest.py`
  * `backend/src/api/reconciliation_firstcard/routes/status.py`
  * `backend/src/api/reconciliation_firstcard/routes/log.py`
* Services / tasks / DB layer:

  * `backend/src/services/tasks/*.py`
  * `backend/src/services/db/*.py`
  * `backend/src/services/ai_service.py`
* Models:

  * `backend/src/models/receipts.py` (already has `ReceiptStatus` Enum)
  * `backend/src/models/company_card.py`
  * `backend/src/models/ai_processing.py`

Database tables:

* `unified_files` (columns: `ai_status`, process-related fields, soft delete, etc.)
* `workflow_runs` (status ENUM, workflow_key, current_stage).
* `workflow_stage_runs` (status, stage_key, message).
* `creditcard_invoices_main`, `creditcard_invoice_items`, `creditcard_receipt_matches` (status columns).
* `ai_processing_history`, `ai_processing_queue` (result status).

---

### P0.2.1 – Inventory all statuses

**Goal:** build a definitive list of all status values used in code & schema.

Steps for the agent:

1. Search for `ai_status` in code:

   * Already appears in:

     * `backend/src/api/app.py`
     * `backend/src/api/ai_processing.py`
     * `backend/src/api/receipts.py`
     * `backend/src/api/export.py`
     * `backend/src/api/fetcher.py`
     * `backend/src/api/ingest.py`
     * `backend/src/api/reconciliation_firstcard/routes/*`
     * `backend/tests/*`
     * `scripts/*.py`
   * Extract:

     * All literal strings assigned to `ai_status`.
     * All filters using `WHERE ai_status = '...'` and similar.

2. Search for `workflow_runs` and `workflow_stage_runs`:

   * Check:

     * `database/migrations/0031_create_workflow_tracking.sql`
     * `backend/migrations/0037_add_workflow_tracking_tables.sql`
   * Note the `ENUM('queued','running','succeeded','failed','canceled')` in `workflow_runs.status`.
   * Search for `workflow_runs` / `workflow_stage_runs` usage in Python:

     * `backend/src/api/receipts.py` uses a subquery joining `workflow_stage_runs` to find `latest_stage_status`.
     * Any service/task modules that write to these tables.

3. Search for other “status” columns:

   * `status` in `creditcard_` tables.
   * `status` in `ai_processing_history`, `ai_processing_queue`.

4. Document everything you find into an internal table (in code comments only, not persisted):

   * For example, in a new docs comment block, or in `docs/SYSTEM_DOCS/MIND_WORKFLOW.md`, add a section:

     ```markdown
     ### Status inventory (source of truth for P0.2 refactor)

     - unified_files.ai_status:
       - Values observed in DB/code: "new", "queued", "processing", "processed", "error", ...
     - workflow_runs.status:
       - ENUM('queued','running','succeeded','failed','canceled')
     - workflow_stage_runs.status:
       - Observed values: "queued", "running", "succeeded", "failed", "skipped", ...
     - creditcard_invoices_main.status:
       - Observed values: "uploaded", "processing", "ready_for_export", "exported", ...
     - ReceiptStatus (backend/src/models/receipts.py):
       - PROCESSING = "Processing"
       - PASSED = "Passed"
       - FAILED = "Failed"
       - MANUAL_REVIEW = "Manual Review"
       - COMPLETED = "Completed"
     ```

   (The agent must fill actual values from grep results & DB schema.)

**Acceptance criteria:**

* A single, up-to-date status table exists in documentation showing all status fields and their string values.

---

### P0.2.2 – Introduce central status definitions module

**Goal:** remove scattered string literals by centralizing statuses in one module, then gradually referencing it across code.

1. Create a new module, e.g.:

   * `backend/src/models/statuses.py`

2. Define enums or constant classes using the actual values found in P0.2.1. For example (illustrative only; agent must use real values):

   ```python
   from enum import Enum

   class WorkflowRunStatus(str, Enum):
       QUEUED = "queued"
       RUNNING = "running"
       SUCCEEDED = "succeeded"
       FAILED = "failed"
       CANCELED = "canceled"


   class WorkflowStageStatus(str, Enum):
       QUEUED = "queued"
       RUNNING = "running"
       SUCCEEDED = "succeeded"
       FAILED = "failed"
       # Add other values actually used, e.g. "skipped" if present


   class AIStatus(str, Enum):
       # Fill with actual ai_status values used in unified_files and code
       NEW = "new"
       PROCESSING = "processing"
       PROCESSED = "processed"
       ERROR = "error"
       # etc.


   class CreditCardInvoiceStatus(str, Enum):
       # Derived from creditcard_invoices_main / code usage
       UPLOADED = "uploaded"
       PROCESSING = "processing"
       READY_FOR_EXPORT = "ready_for_export"
       EXPORTED = "exported"
       # etc.
   ```

3. Keep `ReceiptStatus` in `backend/src/models/receipts.py` but you may import shared values if appropriate (optional). Do **not** change its string values.

4. Add short docstrings explaining that:

   * These enums define the **canonical set of statuses** used across the system.
   * All status reads/writes in code should migrate to these enums where feasible.

**Acceptance criteria:**

* `backend/src/models/statuses.py` exists and contains enums reflecting real status strings.
* No status values are invented; all come from P0.2.1 inventory.

---

### P0.2.3 – Wire status enums into workflow tables

**Goal:** ensure that uses of `workflow_runs.status` and `workflow_stage_runs.status` in Python code use the enums instead of raw strings.

1. Identify all code paths writing to `workflow_runs` and `workflow_stage_runs`:

   * Likely in:

     * `backend/src/services/tasks/workflow_tasks.py`
     * `backend/src/services/tasks/file_management_tasks.py`
     * `backend/src/services/tasks/invoice_tasks.py`
     * Possibly in direct DB helper modules if they exist.

2. For each write:

   * If you see hard-coded strings like `"queued"`, `"running"`, `"succeeded"`, `"failed"`, `"canceled"`, replace them with:

     ```python
     from models.statuses import WorkflowRunStatus, WorkflowStageStatus

     status=WorkflowRunStatus.QUEUED.value
     ```

   * For stage statuses, similarly use `WorkflowStageStatus`.

3. For reads, especially in `backend/src/api/receipts.py`, look for SQL snippets like:

   ```sql
   SELECT wr.file_id,
          wr.source_channel,
          SUBSTRING_INDEX(GROUP_CONCAT(wsr.stage_key ORDER BY wsr.started_at DESC SEPARATOR ','), ',', 1) AS latest_stage_key,
          SUBSTRING_INDEX(GROUP_CONCAT(wsr.status ORDER BY wsr.started_at DESC SEPARATOR ','), ',', 1) AS latest_stage_status
   FROM workflow_stage_runs wsr
   JOIN workflow_runs wr ON wr.id = wsr.workflow_run_id
   GROUP BY wr.file_id, wr.source_channel
   ```

   * This is fine as raw SQL, but whenever you compare `latest_stage_status` to string literals in Python, replace those with enum values.

4. Do not change the actual SQL schema for `workflow_runs.status` / `workflow_stage_runs.status` in this phase. Only the Python side.

**Acceptance criteria:**

* All Python code that writes to workflow status columns uses `WorkflowRunStatus` / `WorkflowStageStatus`.
* No new status strings appear in code without going through the enums module.

---

### P0.2.4 – Wire AI and credit card statuses into the enums

**Goal:** standardize `ai_status` and credit card–related statuses via `models/statuses.py`.

1. `ai_status` usage:

   * Search files that touch `unified_files.ai_status`, e.g.:

     * `backend/src/api/ai_processing.py`
     * `backend/src/api/receipts.py`
     * `backend/src/api/ingest.py`
     * `backend/src/services/tasks/ocr_tasks.py`
     * `backend/src/services/tasks/invoice_tasks.py`
     * `backend/tests/...`
   * Replace string literals like `"new"`, `"processing"`, `"processed"`, `"error"` with:

     ```python
     from models.statuses import AIStatus

     ai_status = AIStatus.PROCESSING.value
     ```

2. Credit card statuses:

   * Check:

     * `backend/src/api/reconciliation_firstcard/routes/status.py`
     * `backend/src/services/tasks/creditcard_tasks.py`
     * Any DB helpers touching `creditcard_invoices_main.status`.
   * Replace string literals with `CreditCardInvoiceStatus` enum values.

3. Unit tests:

   * Update tests that assert on raw strings to either:

     * still assert on raw strings (no need to enforce enums in tests), or
     * import enums from `models.statuses` and use `.value` for clarity.
   * Do **not** change expected JSON payloads or API contracts.

**Acceptance criteria:**

* All writes to `unified_files.ai_status` use `AIStatus` enum.
* All writes to credit card invoice statuses use `CreditCardInvoiceStatus` enum.
* Existing test expectations still pass (no behavioural change).

---

### P0.2.5 – Status and workflow regression tests

**Goal:** ensure that all refactors in P0.2 did not break behaviour.

Add or update tests under `backend/tests`:

1. **Receipts API listing** (`backend/tests/unit/test_receipt_modal_api.py`, `backend/tests/integration/test_receipt_approve_endpoint.py`):

   * Confirm that:

     * `ai_status` fields in the JSON response are still strings with the same values as before refactor.
     * Any derived fields based on workflow status (e.g. latest stage) still use the same semantics.

2. **Workflow debugging scripts**:

   * `backend/check_status.py` and `backend/check_workflows.py` are external tools.
   * Ensure they still work without modification:

     * They hit API endpoints (`/receipts`), parse JSON, and print statuses.
     * No need to change them, but you may add comments pointing to `models/statuses` if helpful.

3. **Full flow tests**:

   * `backend/tests/integration/test_full_flow.py`
   * `backend/tests/integration/test_invoice_upload_status.py`
   * `backend/tests/integration/test_company_card_manual_edit_and_export.py`

   Confirm:

   * All status transitions asserted in these tests still pass.
   * No additional or missing statuses appear.

**Acceptance criteria:**

* All test suites pass (unit + integration).
* Manual smoke tests (if you run them locally) show unchanged behaviour in UI/API.

---

If you want, I can next write this as a **machine-tight agent prompt file** (e.g. `.github/prompts/mind_P0_implementation.prompt.md`) where every step is phrased as “You MUST … / You MUST NOT …” so your VS Code agent can just follow it without improvising.



