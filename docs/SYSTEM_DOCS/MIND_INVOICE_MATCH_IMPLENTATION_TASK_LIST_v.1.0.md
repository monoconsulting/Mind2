# MIND Invoice Match Implementation Task List v1.0

All phases, sprints, tasks, and subtasks reference the adjustments captured in section 12 of `docs/SYSTEM_DOCS/MIND_INVOICE_MATCH_IMPLEMENTATION_PLAN.md`. Numbering uses the format Phase.Sprint.Task.Subtask (e.g., 2.1.1.3). All test work must comply with `docs/TEST_RULES.md` and reporting instructions in `web/TEST_AGENT_INSTRUCTIONS.md`.

## Phase 1 - Backend Foundations

### Sprint 1.1 - API and Persistence Readiness

- **Task 1.1.1 - Implement invoice upload and status endpoints**
  - **Description:** Build production-ready implementations for `/reconciliation/firstcard/upload-invoice`, `/reconciliation/firstcard/invoices/<id>/status`, and `/reconciliation/firstcard/invoices/<id>/lines`, reusing shared helpers from `api.ingest` to avoid duplicated storage logic.
  - **Subtasks:**
    - 1.1.1.1 Validate multipart uploads (PDF/image) with duplicate-hash checks via shared helper.
    - 1.1.1.2 Persist parent/child `unified_files` entries, set `invoice_documents` records, and enqueue OCR tasks.
    - 1.1.1.3 Implement status polling response with page-level OCR progress, AI summary, and match counts.
    - 1.1.1.4 Expose extracted line data, including match metadata, via `/lines` with pagination guardrails.
  - **Test Guidance:**
    - Add backend integration tests in `backend/tests/integration/` to cover happy-path PDF and image uploads (store fixtures under `web/test/` following timestamp naming).
    - Record results in `/web/test-results/` and post metadata via the test-results API.
    - Confirm database updates by querying `invoice_documents`, `invoice_lines`, and `unified_files` after each test run.

- **Task 1.1.2 - Define processing status lifecycle**
  - **Description:** Map explicit transitions for `invoice_documents.processing_status`, `invoice_documents.status`, and `invoice_lines.match_status` throughout OCR, AI extraction, and matching.
  - **Subtasks:**
    - 1.1.2.1 Document state machine in code comments and system docs.
    - 1.1.2.2 Implement atomic updates within Celery tasks to reflect each stage.
    - 1.1.2.3 Add database assertions ensuring illegal transitions trigger alerts.
  - **Test Guidance:**
    - Write unit tests around helper functions managing state transitions.
    - Extend integration tests to assert final statuses per scenario (successful match, partial, failure).

- **Task 1.1.3 - Align database schema and migration numbering**
  - **Description:** Rename the proposed migration to the next free sequence number, reconcile new columns with the current schema, and regenerate SQL diffs.
  - **Subtasks:**
    - 1.1.3.1 Inventory existing migration numbers and reserve the next open slot.
    - 1.1.3.2 Update `invoice_*` column definitions to match actual code requirements (data types, defaults, indexes).
    - 1.1.3.3 Regenerate migration files and document rollback steps.
  - **Test Guidance:**
    - Run migration on a disposable database, verify schema via `SHOW CREATE TABLE`, and document results in `/web/test-results/`.

## Phase 2 - Processing Pipeline Modernisation

### Sprint 2.1 - OCR and AI Control Flow

- **Task 2.1.1 - Branch invoice OCR pipeline**
  - **Description:** Update `process_ocr` (and related helpers) to route invoice files into the dedicated invoice extraction chain instead of the receipt pipeline.
  - **Subtasks:**
    - 2.1.1.1 Introduce file-type guards before triggering `process_ai_pipeline`.
    - 2.1.1.2 Invoke new invoice-specific tasks (`process_invoice_ai_extraction`, `process_invoice_matching`) when appropriate.
    - 2.1.1.3 Backfill history logging to differentiate invoice vs receipt jobs.
  - **Test Guidance:**
    - Add unit tests for routing logic.
    - Execute integration tests ensuring receipt uploads still follow the legacy path while invoices do not.

- **Task 2.1.2 - Optimise multi-page OCR orchestration**
  - **Description:** Implement Celery groups/chords (or equivalent) to process invoice pages in parallel and trigger extraction when all pages complete.
  - **Subtasks:**
    - 2.1.2.1 Define chord/group signatures for multi-page invoices.
    - 2.1.2.2 Implement aggregation callback that records `ocr_progress`.
    - 2.1.2.3 Handle timeouts or failed pages with retries and status updates.
  - **Test Guidance:**
    - Simulate multi-page invoices in integration tests, asserting `ocr_progress` in status responses.
    - Benchmark processing time and include findings in the test report.

- **Task 2.1.3 - Avoid duplicate file writes**
  - **Description:** Ensure `pdf_to_png_pages` outputs are reused directly, preventing redundant saves via `FileStorage` while still registering page metadata.
  - **Subtasks:**
    - 2.1.3.1 Refactor storage logic to accept pre-existing file paths for invoice pages.
    - 2.1.3.2 Add cleanup routines for temporary files when processing fails.
    - 2.1.3.3 Update documentation to reflect the new storage pattern.
  - **Test Guidance:**
    - Add unit tests for storage helpers verifying idempotency.
    - During integration tests, inspect storage directories to confirm single copies per page.

## Phase 3 - Matching and Data Surfacing

### Sprint 3.1 - Matching Accuracy and Visibility

- **Task 3.1.1 - Merge enhanced matching with existing routes**
  - **Description:** Consolidate the improved fuzzy/exact matching algorithm into `/reconciliation/firstcard/match` and extend `list_statements` to include `invoice_type='credit_card_invoice'` entries for the frontend.
  - **Subtasks:**
    - 3.1.1.1 Refactor matching logic into reusable service functions.
    - 3.1.1.2 Expand REST responses to expose match confidence, history, and unmatched counts.
    - 3.1.1.3 Update observability metrics (`record_invoice_decision`) for new states.
  - **Test Guidance:**
    - Extend existing integration tests to verify exact and fuzzy matches, including negative cases.
    - Add regression tests confirming legacy statement imports still succeed.

- **Task 3.1.2 - Deliver performant status polling**
  - **Description:** Ensure the status endpoint aggregates OCR progress, AI extraction counts, and match statistics efficiently (joins, indexes, caching if required).
  - **Subtasks:**
    - 3.1.2.1 Profile SQL queries used for status responses.
    - 3.1.2.2 Add required indexes (if not covered in Phase 1) and document them.
    - 3.1.2.3 Implement caching or memoisation where latency exceeds SLA.
  - **Test Guidance:**
    - Create performance benchmarks (e.g., pytest-benchmark) to prove response time under load and store reports per instructions.

## Phase 4 - Frontend Experience

### Sprint 4.1 - Upload and Review UX

- **Task 4.1.1 - Integrate upload modal and progress polling**
  - **Description:** Wire the new upload modal components to the completed backend endpoints, ensuring accurate progress updates and error handling.
  - **Subtasks:**
    - 4.1.1.1 Update `CompanyCard.jsx` to fetch new invoice types and open the modal.
    - 4.1.1.2 Connect modal actions to `/upload-invoice` and `/status` endpoints, reflecting all processing states.
    - 4.1.1.3 Surface matched/unmatched lines via `/lines`, including pagination or filtering if response size warrants.
  - **Test Guidance:**
    - Implement Playwright scenarios under `web/tests/` (reuse or extend existing specs) covering upload, polling, and review flows.
    - Save video (1900x120) and snapshot (1900x1200) artefacts per `docs/TEST_RULES.md`.

- **Task 4.1.2 - Manual review tooling (optional Nice-to-Have)**
  - **Description:** Provide UI for manual matching/unmatching if prioritised later, honoring the matching history log.
  - **Subtasks:**
    - 4.1.2.1 Design modal/table interactions for manual decisions.
    - 4.1.2.2 Hook into backend update endpoints and refresh state.
    - 4.1.2.3 Respect audit trail requirements when updating matches.
  - **Test Guidance:**
    - Add UI automation tests once the feature is scheduled; follow the same storage and reporting rules for artefacts.

## Phase 5 - Quality, Observability, and Documentation

### Sprint 5.1 - Testing and Compliance

- **Task 5.1.1 - Restructure automated test suites**
  - **Description:** Move or recreate new tests under `web/tests/`, ensuring fixtures and reports follow the naming conventions from `web/TEST_AGENT_INSTRUCTIONS.md`.
  - **Subtasks:**
    - 5.1.1.1 Relocate Playwright specs and adjust imports/paths.
    - 5.1.1.2 Update package scripts or CI workflows to target the new test locations.
    - 5.1.1.3 Document the new layout in project READMEs.
  - **Test Guidance:**
    - Run `npm run test:e2e:report` (Chromium headless) and archive artefacts as required.

- **Task 5.1.2 - Expand automated coverage**
  - **Description:** Add targeted unit and integration tests for AI extraction, matching heuristics, and failure handling (duplicate uploads, OCR errors, partial matches).
  - **Subtasks:**
    - 5.1.2.1 Write fixtures representing multi-page invoices and store under `/web/test/` with timestamps.
    - 5.1.2.2 Cover edge cases such as refunds, foreign currency, and multi-merchant statements.
    - 5.1.2.3 Ensure tests log database verification steps (table + data summary) in their reports.
  - **Test Guidance:**
    - Produce HTML reports via the standard Playwright command or pytest-html equivalents and publish them under `/web/test-results/`.

- **Task 5.1.3 - Operational readiness checks**
  - **Description:** Validate monitoring, logging, and rollback procedures reflect the new pipeline stages.
  - **Subtasks:**
    - 5.1.3.1 Update observability dashboards to include invoice-specific metrics (upload rate, match accuracy, error rate).
    - 5.1.3.2 Create runbooks for pausing invoice processing and rolling back schema changes.
    - 5.1.3.3 Document required environment variables and secrets (AI keys, storage paths).
  - **Test Guidance:**
    - Execute tabletop exercises or scripted smoke tests to verify runbook steps, recording outcomes per the reporting standard.

