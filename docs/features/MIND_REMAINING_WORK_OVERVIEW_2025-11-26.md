# MIND – Remaining Work Overview (2025-11-26)

This document summarizes all **remaining work** for the Mind backend, database, and workflows, based on:

- `MIND_FULL_ANALYZE_2025-11-25.md`
- `MIND_FULL_ANALYZE_2025-11-25_IMPLEMENTATION_GUIDE_OVERVIEW.md`
- `WORKFLOW_DESIGN_ANALYZE_AND_UPDATE_2025-11-20.md.md`
- `FIRSTCARD_REFACTOR_TASKS.md`
- `MANUAL_MATCH_DESIGN_AND_PLAN.md` and related workflow docs.

The focus is explicitly on **what is not yet done**, i.e. the gap between the current code/DB and the intended design.

------

## 0. Global constraints (still in force)

These constraints from the implementation guide remain valid and must be respected by any future work:

1. **No new end-user features** unless explicitly specified.
2. **No invented schema/config** – use only real tables, columns, and environment variables already present.
3. **No hard deletions of code** – retired code must be commented out with an explanatory comment.
4. **No drive-by refactors** – only touch files that are clearly in scope for the current task, and explain cross-cutting changes in comments.
5. **Behaviour parity over “prettiness”** – refactors must preserve current external behaviour (API contracts, observable statuses, etc.).

All remaining work described below must follow these rules.

------

## 1. Migrations & Schema – Single Source of Truth (P0.1)

**Current state**

- Old migrations live in `database/migrations/0001..0031`.
- Newer patches live in `backend/migrations/0032..0038`.
- `services/db/migrations.py` still tries to resolve migrations from both places.

**What’s left to do**

1. **Make `database/migrations` the canonical migration location.**
   - For each SQL file under `backend/migrations/0032..0038`:
     - Check if its changes are already represented under `database/migrations`.
     - If not, create a new, numbered migration `00XX_*.sql` under `database/migrations` and move the content there.
     - In the old `backend/migrations` file, comment out all SQL and add a header comment:
        `-- Deprecated: content moved to database/migrations/00XX_...sql (kept for historical reference only).`
2. **Update the migration runner to only use one directory.**
   - In `backend/src/services/db/migrations.py`:
     - Remove logic that looks in both `database/migrations` and `backend/migrations`.
     - Resolve only a single `MIGRATIONS_DIR` pointing at `database/migrations`, preserving container/local path resolution.
3. **Enforce migration ordering and uniqueness.**
   - Implement a helper in `services/db/migrations.py` that:
     - Lists all `.sql` migrations in `MIGRATIONS_DIR`.
     - Ensures numeric ordering is strictly monotonic (no duplicate numbers, no gaps with conflicting names like two `0007_*`).
     - Raises a clear, testable exception if the pattern is violated.
4. **Add tests for migrations.**
   - Under `backend/tests/unit`:
     - Add tests that assert:
       - All migration filenames match the `NNNN_*.sql` pattern.
       - There are no duplicates.
       - The migration runner picks up the correct directory.
5. **Document the schema source of truth.**
   - In a doc (e.g. `docs/SYSTEM_DOCS/MIND_SCHEMA_SOURCE_OF_TRUTH.md`):
     - Explicitly state:
        “**Single source of truth for schema = `database/migrations`**.
        `backend/migrations` is deprecated and only kept for historical reference.”

------

## 2. Workflow Status & State Consistency (P0.2)

**Current state**

- Workflow tables exist: `workflow_runs`, `workflow_stage_runs`.
- Status fields live on `unified_files`, `invoice_documents`, `invoice_lines`, and `creditcard_*` tables.
- Many services and endpoints still update statuses via raw SQL with hard-coded strings.

**What’s left to do**

1. **Central status definition module.**
   - Create a module like `backend/src/models/statuses.py` or `backend/src/services/workflow_statuses.py` that defines:
     - Enums or constant classes for:
       - File process status (`unified_files.process_status` etc).
       - AI status (`unified_files.ai_status`).
       - Workflow stage types (`workflow_stage_runs.stage_type`, if applicable).
       - Credit card reconciliation statuses (`invoice_documents.processing_status`, FC specific flags, etc).
   - Replace **all** string literals referring to statuses in:
     - `backend/src/services/tasks/*`
     - `backend/src/services/db/*`
     - `backend/src/api/*`
        with the central constants – without changing the actual values.
2. **Enforce documented status transitions.**
   - Take `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` as the reference for state machines for:
     - Receipts
     - Invoices
     - Credit card statements
   - For each major workflow:
     - Enumerate all transitions in code (tasks + API endpoints).
     - Compare to the documented flow.
     - Where there is a mismatch:
       - First add tests capturing current behaviour.
       - Then introduce a small, explicit mapping (e.g. obsolete status → new canonical status) with comments referencing `MIND_WORKFLOW.md`.
3. **Clarify soft delete vs reprocessing semantics.**
   - Identify all places that:
     - Mark rows as soft-deleted on `unified_files`, `invoice_documents`, etc.
     - Re-queue or resume processing for previously processed files.
   - Document a canonical rule set for:
     - What soft delete means (hiding vs truly blocked from further processing).
     - How reprocessing interacts with existing workflow runs (new run vs reuse).
   - Implement small adjustments to enforce that rule set across:
     - `services/tasks/workflow_tasks.py`
     - `services/tasks/file_management_tasks.py`
     - `api/ingest.py`, `api/receipts.py`, `api/reconciliation_firstcard.py`.
4. **Document status definitions.**
   - Add a dedicated doc, e.g. `docs/SYSTEM_DOCS/MIND_STATUS_DEFINITIONS.md`:
     - List each status constant, its meaning, and which table/column uses it.

------

## 3. Ingestion, FTP & `unified_files` (P1.1 & P1.2)

**Current state**

- There are multiple FTP variants: `services/fetch_ftp.py`, `fetch_ftp_enhanced.py`, `fetch_ftp_updated.py`, `fetch_ftp_backup.py`.
- `unified_files` is used across the system but file creation logic is scattered.
- Deduplication via `content_hash` is only partially wired.

**What’s left to do**

1. **Introduce a single unified FTP service.**
   - Create a canonical FTP module (e.g. `services/ftp_service.py`) that:
     - Encapsulates all FTP connection logic and error handling.
     - Exposes a small, clear API: `fetch_new_files()` returning file descriptors (paths, metadata).
   - Gradually migrate logic from the multiple `fetch_ftp*` modules into this single service.
   - Comment out legacy code, with comments explaining:
     - That it has been replaced.
     - Which new function/module should be used instead.
2. **Standardize file creation via `create_unified_file(...)`.**
   - In `services/db/files.py`, implement a single public function `create_unified_file(...)` that:
     - Inserts into `unified_files`.
     - Sets:
       - `file_type`
       - `ai_status`
       - `process_status`
       - `content_hash` (if available)
       - `company_id` (if known)
       - `submitted_by` (if applicable).
     - Performs deduplication:
       - If a row exists for same `content_hash` + `company_id`, either:
         - Skip creation, or
         - Mark as duplicate (`is_duplicate` pattern) according to current behaviour.
     - Raises `DuplicateFileError` when relevant (reuse existing class).
   - Ensure **all** ingestion paths (FTP + upload endpoints) call this function.
3. **Integrate workflow creation at ingestion.**
   - Implement `services/workflow_runs.start_workflow_for_file(unified_file_id, workflow_type)` that:
     - Creates a `workflow_runs` row for the new file.
     - Optionally creates an initial `workflow_stage_runs` entry.
   - Call this from the ingestion path right after `create_unified_file(...)`, so that every file has a workflow run from the start.
4. **Tests for ingestion and deduplication.**
   - Add unit/integration tests verifying:
     - Happy path ingestion (new file → `unified_files` row + `workflow_run`).
     - Duplicate file detection and behaviour (skip vs duplicate flag).
     - Error handling for FTP connectivity and partial failures.

------

## 4. FirstCard Workflow – Coordinator, Status & Resume (Fas 3 + parts of P0.2 / P3)

**Current state**

- Canonical FC model: `invoice_documents` + `invoice_lines` is conceptually in place and recommended in the docs.
- Legacy tables `creditcard_invoices_main` / `creditcard_invoice_items` / `creditcard_receipt_matches` still exist and are used by AI/legacy logic.
- FirstCard refactor plan in `FIRSTCARD_REFACTOR_TASKS.md` defines Fas 3 (P0+P1) as **required for production**, but tasks 3.1–3.5 are not yet done.

**What’s left to do – high-level**

1. **Finish the WorkflowCoordinator for FC (Task 3.1).**
   - Implement / complete functions in the coordinator (likely in `workflow_tasks.py` / dedicated coordinator class) for:
     - `create_workflow_run` / `begin_import_stage` / `complete_import_stage` / `dispatch_workflow`.
   - Ensure that:
     - All FC import/resume endpoints use these coordinator functions instead of manually touching `workflow_runs` or statuses.
2. **Remove manual SQL status updates for FC (Task 3.2).**
   - Identify all places in:
     - `api/reconciliation_firstcard.py`
     - `services/tasks/creditcard_tasks.py`
     - other FC-related modules
        that execute raw `UPDATE ... SET status` / `processing_status` directly.
   - Replace them with calls to:
     - The central status module (Section 2).
     - WorkflowCoordinator methods for starting/completing stages.
3. **Align FC detail endpoint with `invoice_lines` (Tasks 3.3 & 4.1).**
   - Ensure the detail endpoint(s) that drive Manual Match and admin UIs:
     - Read their “source of truth” from `invoice_documents` + `invoice_lines`.
     - Do not rely on `creditcard_invoice_items` for anything user-visible.
4. **Centralize FC stage logging (Task 3.4).**
   - Make sure that stage tracking for FC:
     - Is implemented only via helper functions in `workflow_tasks.py` (or `services/workflow_runs.py`).
     - No ad-hoc inserts into `workflow_stage_runs` in endpoints or random tasks.
5. **Integration tests for FC flow, resume & restart (Task 3.5).**
   - Add tests that verify:
     - Full FC flow: import → OCR/AI → Manual Match → confirm.
     - `resume` of a stuck or partially processed FC document.
     - `restart` creating a new workflow_run while keeping history (workflow_runs count ≥ 2 for the same file).
6. **Optional but recommended: metrics for FC workflows (Task 4.2).**
   - Add Prometheus metrics via `observability/metrics.py`:
     - `workflow_created_total`, `workflow_completed_total`, `workflow_failed_total`.
     - `lines_matched_total`, `lines_unmatched_total`.
     - `match_score_distribution`.

------

## 5. Manual Match – Remaining Polish

**Current state**

- Manual Match v1 is functionally complete: the UI ties statements to invoice lines and receipts and can confirm when all lines are matched.

**What’s left to do**

1. **UI/UX refinements (Fas 4 / later phases).**
   - Add pagination and/or lazy loading for:
     - Large statements (many lines).
     - Large receipt sets per period.
   - Add clear error handling:
     - Distinguish between backend errors vs network issues.
     - Show toast/alert for failed match/unmatch/confirm actions.
2. **Consistency with receipt listing rules.**
   - Ensure that all places where receipts are listed use the same logic for:
     - Excluding FC-related receipts from generic receipt lists, unless explicitly requested (e.g. `include_credit=true`).
   - Document this in `MIND_STATUS_DEFINITIONS.md` / dedicated doc:
     - e.g. “Receipts with `workflow_type='creditcard_invoice'` are only visible in FC-related views.”
3. **Tests & regression coverage.**
   - Add E2E / integration tests (can be Playwright in a separate repo, or API-level tests here) that cover:
     - Listing statements.
     - Listing lines and candidate receipts for a period.
     - Matching a line to a receipt.
     - Confirming when all lines are matched.

------

## 6. AI Pipeline Refactor (P2)

**Current state**

- AI provider abstraction (`services/ai/providers/*`) exists.
- `ai_service.py` contains orchestration + parsing + some domain logic mixed together.
- Pydantic models in `models/ai_processing.py` are used but still share responsibilities with service code.

**What’s left to do**

1. **Strict separation of AI layers.**
   - Split into three clear layers:
     - **Provider layer** (`services/ai/providers/*.py`):
       - Only API calls, retries, low-level errors.
     - **Orchestration layer** (`services/ai_service.py`):
       - Chooses models, prompts, and sequences provider calls.
       - No domain-specific numeric logic, etc.
     - **Domain validation layer** (`models/ai_processing.py` + helpers):
       - Pydantic models + transformation from raw AI output → internal domain objects (classification, items, accounting proposals).
2. **Clean up `ai_service.py`.**
   - Extract inline parsing and ad-hoc JSON handling into:
     - Small, named helper functions.
   - For each documented AI step in `MIND_WORKFLOW.md` (AI1–AIx):
     - Provide a dedicated orchestrator method.
     - Use a single provider call.
     - Validate with a specific Pydantic model.
3. **Ensure full `ai_processing_history` coverage.**
   - Implement a single helper function to write AI call history to `ai_processing_history`, including:
     - Document id (receipt, invoice, credit card).
     - Prompt id / key.
     - Model id.
     - Result status (success/failure).
     - Error message (if any).
   - Make all AI calls go through this helper.
4. **Strengthen AI tests.**
   - Extend `backend/tests/unit` to cover:
     - Schema validation and error cases for `models/ai_processing.py`.
     - Provider selection logic (using real config).
     - Error handling for invalid JSON, missing fields, and provider errors.

------

## 7. Tasks, Legacy Code & Observability (P3)

**Current state**

- Multiple task modules: `legacy.py`, `workflow_tasks.py`, `file_management_tasks.py`, `invoice_tasks.py`, `creditcard_tasks.py`, `ocr_tasks.py`.
- Mixed logging styles (prints, partial logs, sometimes no logs).

**What’s left to do**

1. **Classify tasks by usage.**
   - For each task entry point in:
     - `services/tasks/legacy.py`
     - `services/tasks/workflow_tasks.py`
     - `services/tasks/file_management_tasks.py`
     - `services/tasks/invoice_tasks.py`
     - `services/tasks/creditcard_tasks.py`
     - `services/tasks/ocr_tasks.py`
   - Determine if it is:
     - Actively used in current workflows.
     - Only used by legacy paths.
     - Completely unused.
2. **Refactor & retire legacy tasks safely.**
   - For actively used tasks:
     - Ensure they use the central status definitions (Section 2).
     - Ensure they use structured logging through `observability/logging.py`.
   - For legacy or unused tasks:
     - Comment them out.
     - Add a clear comment:
       - Why they are retired.
       - If any external system still depends on them.
       - Which new task replaces them, if applicable.
3. **Observability & error propagation.**
   - Ensure all tasks and critical services:
     - Use `configure_json_logging` and `observability/metrics.py` where appropriate.
     - Log task start, key parameters, and outcome (success/failure).
   - Replace “silent None” returns with:
     - Either raised exceptions or clear error state objects.
     - Logged errors at level `ERROR` with enough context (file id, company id, task name).

------

## 8. Documentation & Developer Experience (P4)

**Current state**

- Many docs exist, but some are out of sync with code (multiple variants of migration docs, outdated FC design references).

**What’s left to do**

1. **Sync core docs with reality.**
   - Update `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` to reflect:
     - Canonical FC model = `invoice_documents` + `invoice_lines`.
     - `creditcard_*` tables as AI/legacy/historical layer.
   - Ensure the receipt workflow section matches the actual implementation (AI steps, status fields, etc.).
2. **Schema overview.**
   - Add a `docs/SYSTEM_DOCS/MIND_SCHEMA_OVERVIEW.md` that:
     - Lists all 27 tables (from the dump).
     - Briefly describes each table’s purpose.
     - Links to:
       - The migration file that creates/modifies it.
       - The primary service/module using it.
3. **Workflow debugging quickstart.**
   - Add `docs/SYSTEM_DOCS/WORKFLOW_DEBUGGING.md` explaining:
     - How to run backend locally (including Docker env hints).
     - How to apply migrations (auto vs manual).
     - How to inspect `workflow_runs` / `workflow_stage_runs` for a given file.
     - How to safely re-run workflows for a specific file.
4. **Agent instruction prompt file.**
   - Add e.g. `.prompts/mind_refactor.prompt.md` containing:
     - Global rules (Section 0).
     - Phase descriptions P0–P3 as they now stand.
     - References to key docs and directories (`api`, `services`, `models`, `database/migrations`, `docs/SYSTEM_DOCS`).

------

## 9. High-level summary

From the perspective of **“what’s left”**:

- **Schema/migrations:** unify in `database/migrations` and lock down ordering + tooling.
- **Status & workflow:** centralize status constants and ensure all transitions match `MIND_WORKFLOW.md`.
- **Ingestion & `unified_files`:** create a single ingestion path with `create_unified_file(...)` + workflow run creation + deduplication.
- **FirstCard:** finish WorkflowCoordinator + status refactor + resume/restart tests, with `invoice_lines` as canonical source.
- **Manual Match:** functionally done for v1; remaining work is polish, consistency, and tests.
- **AI pipeline:** clean separation of provider/orchestration/domain, plus full `ai_processing_history` and better tests.
- **Tasks & observability:** classify and retire legacy tasks; enforce structured logging and clear error propagation.
- **Docs & DX:** bring docs in sync with actual behaviour and provide better orientation for humans and agents.

Next step after this document is to **slice these items into concrete phases for agents** (e.g. “P0-remaining”, “FC-Fas 3”, “AI-P2”), each with a strict scope and success criteria.