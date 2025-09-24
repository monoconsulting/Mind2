# Tasks: Mind system — receipt capture, AI processing, admin review, SIE export

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract tech stack, libraries, structure
2. Load design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
   → quickstart.md: Extract scenarios → integration tests
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI/HTTP endpoints
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules: [P] different files; tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Output tasks.md
```

## Phase 3.1: Setup
 - [x] T001 Initialize Python backend project structure (backend/src, backend/tests) per plan.md (done in commit e7090b5)
 - [x] T002 Add dependencies: Flask, Celery, Redis, MySQL client, Prometheus client, pytest, coverage (requirements.txt, pytest.ini)
 - [x] T003 [P] Configure linting/formatting: black, isort, flake8 + pre-commit hooks (.flake8, pyproject.toml, .pre-commit-config.yaml, .editorconfig)
 - [x] T004 Initialize Docker Compose profiles (main, monitoring) and env templates (docker-compose.yml, .env.example)
 - [x] T005 Configure Nginx proxy for `/ai/api` and disable deprecated PHP ports in port ledger (nginx/nginx.conf, docs/MIND_PORTS.md)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
- [x] T006 [P] Create contract tests for receipts API from contracts/receipts.yaml → backend/tests/contract/test_receipts_api.py (added; currently failing as expected)
- [x] T007 [P] Create contract tests for FirstCard reconciliation API → backend/tests/contract/test_firstcard_api.py (added; currently failing as expected)
- [x] T008 [P] Create contract tests for export API → backend/tests/contract/test_export_api.py (added; currently failing as expected)
- [x] T009 Extract integration scenarios from quickstart.md and write integration tests → backend/tests/integration/test_end_to_end.py (added; currently failing as expected)

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [x] T010 [P] Implement data models per data-model.md (Receipt, LineItem, Tag, Company, CompanyCardInvoice, CompanyCardLine, AccountingRule, ValidationReport, AccountingEntry, ExportJob) → backend/src/models/ (commit 1a1a673)
- [x] T011 Implement DB layer and migrations in canonical order (unified → ai → invoice) → backend/src/services/db/ and database/migrations/ (added connection, migrations helper, 0001/0002 SQL)
   - Added container bind mounts for `database/migrations` (api + worker) in `docker-compose.yml` to avoid install-time delays.
   - Improved migration runner: path resolution in dev/container, SQL comment stripping and safe splitting, idempotent execution (ignores duplicate/already-exists), and extended retry on startup.
   - Introduced manual POST `/system/apply-migrations` endpoint to (re)apply migrations on demand.
   - Optional demo seed: inserts 3 sample receipts into `unified_files` when empty for instant UI sanity.
- [x] T012 Implement receipts endpoints: list, get, update, monthly-summary → backend/src/api/receipts.py (filters/pagination, validation; DB-safe fallbacks)
- [x] T013 Implement reconciliation endpoints: import, match, confirm, reject → backend/src/api/reconciliation_firstcard.py (minimal persistence in queue/history)
- [x] T014 Implement export endpoint: generate SIE for date range → backend/src/api/export.py (blueprint + placeholder SIE text)
- [x] T015 Implement Celery tasks: process_ocr, process_classification, process_invoice_document, matching → backend/src/services/tasks.py (updates ai_status/history)
 - [x] T016 Implement validation service for receipts (math checks, confidence thresholds) → backend/src/services/validation.py
    - Implemented checks: VAT rate validity, numeric/non-negative VAT amounts, gross≈net+VAT with small rounding tolerance, missing fields (gross/net/merchant/date), date plausibility (future/very old), confidence threshold. Escalation: any ERROR→Failed, any WARNING (no errors)→Manual Review, else Passed. Added unit tests in backend/tests/unit/test_validation_service.py.
 - [x] T017 Implement enrichment service to resolve orgnr → company name → backend/src/services/enrichment.py
    - Added orgnr normalization (strip, 12→10 digits, Luhn), provider protocol with dict provider, and enrich_receipt(). Added unit tests in backend/tests/unit/test_enrichment_service.py.
 - [x] T018 Implement accounting proposal service (BAS mapping + rules engine) → backend/src/services/accounting.py
    - Added propose_accounting_entries() using simple BAS accounts, rule-based expense account selection, VAT debits per rate, and balanced credit to 2440/1930. Unit tests in backend/tests/unit/test_accounting_service.py.

## Phase 3.4: Integration & Observability
 - [x] T019 Wire Celery + Redis configuration; queue definitions and retry/backoff → backend/src/services/queue_manager.py
    - Centralized Celery app with Redis URLs from env, acks_late, single prefetch, visibility timeout, defaults. Tasks refactored to use shared app. Added unit test.
 - [x] T020 Add structured JSON logging and Prometheus metrics in API and workers → backend/src/observability/
    - Added JSON logger and Prometheus metrics util. Instrumented Flask endpoints and Celery tasks; exposed /system/metrics. Unit test added.
 - [x] T021 Add auth middleware (JWT Bearer) and CORS config per admin domains → backend/src/api/middleware.py
    - Implemented HS256 JWT verification with exp, decorators for auth, and CORS handling (preflight + headers). Wired into app; added tests.
 - [x] T022 Add image storage handlers and file refs for multi‑page receipts → backend/src/services/storage.py
    - Implemented filesystem adapter with safe path join and CRUD. Added unit tests for save/load/list/delete and traversal protection.

## Phase 3.5: Polish [P]
 - [x] T023 [P] Unit tests for services (validation, enrichment, accounting) → backend/tests/unit/
    - Added expanded validation tests (edge cases, ≥90% coverage) and accounting VAT multi-rate balancing test.
 - [x] T024 [P] Performance tests for API p95 < 200ms and memory budget checks → backend/tests/perf/
    - Added latency p95 checks for /ingest/upload and /system/metrics using Flask test client; included a simple memory growth stability test with tracemalloc.
  - [x] T025 [P] Documentation updates: API docs from OpenAPI, runbooks for ops, update docs/SYSTEMDOCS references
    - Added docs/API_DOCS.md och docs/RUNBOOKS.md; cross-referenced contracts; will expand as endpoints evolve.
    - 2025-09-22: Export-endpoint korrigerad (GET /export/sie) och nya referenser tillagda: `docs/MIND_ENDPOINTS.md`, `docs/MIND_ENV_VARS.md`.
 - [x] T026 [P] Security hardening: secrets scanning, dependency audit, error message review
    - Added Bandit to pre-commit; created docs/SECURITY_HARDENING.md with audit/secrets guidance.
- [x] T027 [P] Integrate Darkmind UI design guides into Admin SPA → ui-design/MIND_DESIGN_GUIDES.md, frontend/
   - When frontend is scaffolded, follow the guide to build and link design assets (CSS/JS), apply global classes and viewport meta, and integrate components.
 - [x] T028 [P] Finalize frontend scaffold and connect initial components → frontend/
    - Added basic nav shell (Dashboard/Receipts), API ping button, and a Receipts view that fetches `/ai/api/receipts`. CSS now points to `/darkmind.css`.

## Phase 3.6: Auth, Health, and E2E login
- [x] T029 Implement auth login endpoint and blueprint registration → backend/src/api/auth.py, backend/src/api/app.py
   - POST /auth/login that issues HS256 JWT using ADMIN_PASSWORD and JWT_SECRET_KEY; registered blueprint; returns access_token + expires_in
- [x] T030 Add system probes for stack checks → backend/src/api/app.py
   - GET /health, GET /system/db-ping, GET /system/celery-ping + minimal JSON responses
- [x] T031 Tests for auth and probes → backend/tests/unit/test_auth_login.py, backend/tests/integration/test_login_flow.py
   - Unit: login_disabled (503 when ADMIN_PASSWORD missing), invalid creds (401), success (200 + token), token expiry rejection; Integration: login via Nginx then /admin/ping 200 with Bearer



## Phase 3.8: Public Capture UI (Mobile-first)
- [x] T039 Public capture route/app for users (camera + gallery + multi-page) → capture-frontend/ (new) or frontend route `/capture`
   - Implemented as frontend route `/capture` in `frontend/src/views/capture.js` with camera, gallery, multi-page queue, and confirm flow.
- [x] T040 Tag selection UI and simple location opt-in → capture-frontend/
   - Added tags input and optional geolocation capture in the same view; sends JSON via multipart.
- [x] T041 Backend endpoints for capture submission (images + metadata) → backend/src/api/ingest.py
   - Added `POST /capture/upload`: stores files via `FileStorage`, inserts `unified_files` + `file_tags` (best-effort), enqueues OCR; integration test added `backend/tests/integration/test_capture_upload.py`.

## Phase 3.9: Missing Backend endpoints and tests
- [x] T042 Rules API (CRUD) backing Settings page → backend/src/api/rules.py, backend/tests/contract/test_rules_api.py
   - CRUD implemented (file-backed JSON); added contract test for basic flow acknowledging auth.
- [x] T043 Receipt update APIs to support detail edits (fields + line items) → backend/src/api/receipts.py (extend), backend/tests/contract/test_receipt_update.py
   - Added PATCH alias; ai_status/status mapping; purchase_date; file-backed line-items GET/PUT; contract test added.
- [x] T044 Export job endpoint improvements (status/history, size limits) → backend/src/api/export.py, backend/tests/contract/test_export_api.py (extend)
   - Added Content-Disposition for filename and X-Export-Job-Id header; basic in-memory job id creation.

## Phase 3.10: Observability & Ops polish
 - [x] T045 Prometheus scrape config + Grafana dashboard → prometheus/prometheus.yml, grafana/provisioning/
   - Scrape API and Celery metrics; baseline dashboard for latency, error rate, task counts
 - [x] T046 Switch API container to Gunicorn → docker-compose.yml (ai-api command)
   - Replace Flask dev server; verify health/login still pass via Nginx; update docs
- [x] T047 Rate limit and log /auth/login → backend/src/api/auth.py (Flask-Limiter), backend/tests/unit/test_rate_limit.py
   - Basic 429 on bursts; ensure logs include failures (without leaking secrets)
- [x] T048 Resolve docker compose YAML warning → docker-compose.yml, docs/GIT_SANITY_CHECK.md
   - Run `docker compose config`, fix formatting/quoting; ensure zero warnings
 - [x] T049 Secrets management runbook (non-dev) → docs/SECRETS_RUNBOOK.md
   - How to inject JWT_SECRET_KEY/ADMIN_PASSWORD via secrets manager/orchestrator; no secrets in images or VCS
 - [x] T050 DB migrations runbook and bootstrap → docs/RUNBOOKS.md (extend), backend/services/db/migrations.py
   - Steps for fresh env schema; ensure idempotent migration path

## Phase 3.11: End-to-End & Frontend Tests
- [x] T051 End-to-end backend flow test: capture→AI→review→approve→export → backend/tests/integration/test_full_flow.py
   - Implemented full flow test: upload image with tags, update receipt fields and line items, approve status, generate export with headers, verify file storage and line items persistence.
 - [x] T052 Frontend E2E (Playwright) for auth + navigation + receipts → frontend/tests/e2e/
    - Implemented: `frontend/tests/e2e.spec.ts`, config in `frontend/playwright.config.ts`, scripts in `frontend/package.json`; Vite proxy in `frontend/vite.config.js`.
    - Covers: login with admin, Dashboard ping (expects 200), Receipts loaded with rows, page size change, navigation back, logout.
    - Verified locally: from `frontend/` ran `npm run test:e2e` → 1 test passed (chromium).

## ⚠️ ARCHITECTURE CORRECTION REQUIRED (Post-Implementation Analysis)

**FINDING**: Current implementation incorrectly mixes admin and public interfaces in single frontend SPA, violating MIND v2.0 architecture.

**PROBLEM**: 
- Current `frontend/` contains BOTH admin interface (Dashboard, Receipts, Company Card, Export, Settings) AND public capture (`/capture` route) in same SPA
- Missing `mind-web-main-frontend` container in docker-compose.yml 
- No separation between mobile (public) vs admin (local) applications per MIND Technical Plan v2.0

**REQUIRED CORRECTIONS**:
- [x] **T053** [P] Create separate `mobile-capture-frontend/` for public receipt capture only (camera, gallery, tags, location) → deployable to web hotel, contains only capture.js functionality
- [x] **T054** [P] Add `mind-web-main-frontend` container to docker-compose.yml per MIND v2.0 → serves admin SPA on port 8008 via Nginx (Dashboard, Receipts, Company Card, Export, Settings)
- [x] **T055** Remove capture route from admin frontend and update navigation → `frontend/src/main.js`, `frontend/src/wireframe.js` (remove capture imports/routes)
- [x] **T056** Update nginx.conf to serve both admin frontend + mobile capture app → separate location blocks for different deployments
- [x] **T057** Update specs to reflect correct MIND v2.0 architecture → plan.md, contracts/, data-model.md align with ai-api + mind-web-main-frontend structure

**NOTE**: The mobile capture functionality itself (images + metadata → unified_files + file_tags) is correctly implemented and working per v2.0 requirements.

## Acceptance Criteria (System 100% working)
- Login via /ai/api/auth/login works with ADMIN_PASSWORD and JWT_SECRET_KEY; protected routes require Bearer token
- **Admin SPA** (mind-web-main-frontend, port 8008) enforces auth, shows Dashboard and Receipts; Detail & Review supports edits and approval; Settings manages rules; Company Card matching is usable; Export produces SIE
- **Mobile web app** (separate deployment) allows multi-page upload with tags and location flag; pipeline processes and surfaces in Admin SPA
- Prometheus scrapes API and Celery; Grafana dashboard shows live metrics
- API served via Gunicorn; docker compose config has no warnings; .env not committed; secrets handled via env/secrets manager
- Test suite includes unit, contract, integration, and frontend E2E; CI passes; coverage meets targets for new modules

## Dependencies
- Tests before implementation: T006–T009 → T010+
- Models (T010) before services (T011, T015–T018)
- Services before endpoints (T012–T014)
- Queue/observability (T019–T020) before performance tests (T024)

## Parallel Execution Examples
- Group A [P]: T003, T006, T007, T008, T023 in parallel (different files)
- Group B [P]: T010 (models) can be split by entity across files if needed
- Group C [P]: T024, T025, T026 in parallel after core endpoints are green

## Context for generation
Derived from plan.md, data-model.md, contracts/*.yaml, research.md, quickstart.md.

## Status Update – 2025-09-22 (post-implementation)
- [x] T056 Update Nginx to serve Mobile Capture alongside Admin (added `/capture/` alias). Files: `nginx/nginx.conf`, `docker-compose.yml` (mount of `mobile-capture-frontend`).
- [x] T057 Sync docs/specs to v2.0 (added `docs/MIND_ENDPOINTS.md`, `docs/MIND_ENV_VARS.md`; corrected `docs/API_DOCS.md`).
- [x] T058 Implement `/ai/api/system/status` in `backend/src/api/app.py`.
- [x] T059 Implement `/ai/api/system/stats` in `backend/src/api/app.py`.
- [x] T060 Implement `/ai/api/system/config` (GET/PUT, whitelisted) in `backend/src/api/app.py`.

## Phase 3.13: Functional Parity with MIND_FUNCTION_DESCRIPTION
- [x] T061 Fix `file_tags` schema mismatch (add `created_at`) and align ingest writes
  - Add migration `0004_add_created_at_to_file_tags.sql` (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
  - Update any INSERTs to match schema; backfill optional
- [x] T062 Persist location data from capture uploads
  - Option A: add `file_locations(file_id, lat, lon, acc, created_at)`; Option B: add `location_json` to `unified_files`
  - Update `POST /capture/upload` to store it and return via `GET /receipts/{id}`
- [x] T063 Tags management (admin)
  - Add `tags` CRUD API (GET/POST/PUT/DELETE) and admin UI page; Mobile Capture fetches tags dynamically
- [x] T064 Expose/Filter tags and user in Receipts
  - Extend `/receipts` to include tags (aggregate) and support `tags=` filter; add User column (requires `submitted_by` field)
  - Update `frontend/src/views/receipts.js` to display and filter
- [x] T065 Receipt image endpoints
  - Implement `GET /receipts/{id}/image` (+ optional `/thumbnail`) serving from `STORAGE_DIR`
  - Hook up `frontend/src/views/receipt_detail.js` to display image (works after endpoint)
- [x] T066 Validation + Accounting proposal endpoints
  - Implement `GET /receipts/{id}/validation` and `GET /receipts/{id}/accounting/proposal` (or include in details)
  - Render in `receipt_detail.js`; allow editing of suggested accounting
- [x] T067 Approval workflow endpoint
  - Implement `POST /receipts/{id}/approve` (and state transitions); adjust UI approve action
- [x] T068 Align Company Card statements list payload/UI
  - Either return `file_id`/`created_at` in API or adjust UI to use `uploaded_at`/`status`
- [x] T069 Manual edit for Company Card line match
  - Implement `PUT /reconciliation/firstcard/lines/{line_id}` to set `matched_file_id`; add UI affordance to pick a receipt
- [x] T070 Company Card export bundle
  - Implement `GET /export/company-card?period=YYYY-MM` returning invoice + receipts bundle (format TBD) per functional spec
- [x] T071 Integrate real OCR/Classification (feature‑flagged)
  - Wire OCR engine + field extraction into `process_ocr`/`process_classification`; produce line items + bounding boxes for highlights
 - [x] T072 External enrichment provider (Bolagsverket)
  - Implement provider + config; enrich `orgnr` to legal name; cache results
- [x] T073 Company card vs expense detection rules
  - Add rules/config used in classification; propagate to accounting proposal (credit account selection)
- [x] T074 UI field highlights on image
  - Use OCR bounding boxes to overlay highlights in `receipt_detail.js` (hover shows field name)
 - [x] T075 Tests for new endpoints/features
   - Added integration tests for images/boxes, tags API, receipt validation/proposal, manual edit + export, and approve endpoint


## Phase 4: Implement Core AI Functionality
- [x] T076 [P] Replace placeholder OCR with a real implementation.
  - **Context:** The current OCR service in `backend/src/services/ocr.py` is a placeholder that returns static, hardcoded data. This is the most critical missing piece of the AI functionality.
  - **Agent Prompt:** '''Your task is to replace the placeholder OCR implementation in `backend/src/services/ocr.py`. You must integrate a real OCR engine (e.g., a cloud service like Google Vision AI, or a powerful open-source library). The new implementation must take a file path to an image, perform OCR, and extract all required fields as defined in `MIND_FUNCTION_DESCRIPTION.md`: Merchant Name, orgnr, Date/Time, Total Amount, Net Amount, VAT per rate, and individual line items. The function must also return the bounding box coordinates for each extracted field. The outcome is a fully functional `run_ocr` function that populates the database with real, extracted data. To test, you will need to modify the integration test `backend/tests/integration/test_full_flow.py` to upload a real test receipt image (e.g., `inbox/test_receipt.pdf` or a new image file) and assert that the extracted data in the database is correct after the pipeline runs.'''
- [x] T077 [P] Implement AI-powered parsing for Company Card PDF invoices.
  - **Context:** The company card import at `POST /reconciliation/firstcard/import` currently expects pre-parsed JSON data. The functional spec requires the system to read the invoice file (e.g., a PDF) directly.
  - **Agent Prompt:** '''Your task is to modify the company card import process. The endpoint `POST /reconciliation/firstcard/import` should be updated to accept a file upload (e.g., `application/pdf`). You will create a new service function that uses an AI document parsing model (like Google Vision AI or other document AI services) to read the PDF invoice, extract the transaction lines (date, merchant, amount), and then populate the `invoice_documents` and `invoice_lines` tables. The existing logic that uses a JSON payload should be replaced. To test, extend the integration test `backend/tests/integration/test_firstcard_invoice_flow.py` to upload a sample PDF invoice and verify that the transaction lines are correctly extracted and saved to the database.'''

## Phase 5: Complete Automated Backend Pipeline
- [x] T078 Wire the Validation service into the automated pipeline.
  - **Context:** The `validation.py` service is implemented but is not called automatically. It needs to be the next step in the Celery chain after classification.
  - **Agent Prompt:** '''Your task is to modify the Celery task chain in `backend/src/services/tasks.py`. After the `process_classification` task successfully completes, it must trigger a new task, `process_validation`. This new task will call the `validate_receipt` function from `backend/src/services/validation.py`. Based on the validation result (Passed, Failed, Manual Review), you must update the `ai_status` of the receipt in the `unified_files` table. The outcome is that every processed receipt automatically gets a validation status. To test, run the `test_full_flow.py` integration test and assert that the `ai_status` is correctly updated to 'passed' or 'manual_review' after processing.'''
- [x] T079 Wire the Accounting Proposal service into the automated pipeline.
  - **Context:** The `accounting.py` service is implemented but not called automatically. It should run after a receipt has passed validation.
  - **Agent Prompt:** '''Your task is to modify the Celery task chain in `backend/src/services/tasks.py`. The `process_validation` task should, upon a 'Passed' status, trigger a new task, `process_accounting_proposal`. This task will call the `propose_accounting_entries` function from `backend/src/services/accounting.py`. The generated accounting entries must be saved to a new database table, `ai_accounting_proposals`. You will need to create a new migration file (`0007_...`) to add this table. The outcome is that valid receipts get an automatic accounting proposal. To test, extend `test_full_flow.py` to check that after processing, the correct entries exist in the new `ai_accounting_proposals` table.'''
- [x] T080 Persist company enrichment results to the database.
  - **Context:** The `enrichment.py` service successfully looks up company data, but the result is discarded and not saved.
  - **Agent Prompt:** '''Your task is to modify the `process_classification` task in `backend/src/services/tasks.py`. After the call to `enrich_receipt`, you must update the corresponding `unified_files` record in the database, setting the `merchant_name` to the canonical `legal_name` returned by the enrichment service if one is found. The outcome is that the merchant name is corrected to the official company name. To test, add a mock company to the `org_registry.json` file and assert in `test_full_flow.py` that the `merchant_name` in the database has been updated after processing.'''
- [x] T081 Enhance the document classification task.
  - **Context:** The current classification only identifies company card expenses. It needs to fulfill the spec of identifying Receipts, Invoices, and Other document types.
  - **Agent Prompt:** '''Your task is to enhance the `process_classification` task in `backend/src/services/tasks.py`. You need to implement logic, likely based on keywords found during the OCR phase, to classify the document type. The `ai_status` should be updated to reflect this classification (e.g., 'classified_receipt', 'classified_invoice'). For now, the pipeline should only continue for receipts. The outcome is a more intelligent classification step. To test, modify `test_full_flow.py` to check the `ai_status` after classification.'''

## Phase 6: Implement Export Functionality
- [x] T082 [P] Implement SIE file generation.
  - **Context:** The `GET /export/sie` endpoint in `export.py` is a placeholder.
  - **Agent Prompt:** '''Your task is to replace the placeholder implementation of the `export_sie` function in `backend/src/api/export.py`. You must query the database for all accounting entries (from the `ai_accounting_proposals` table created in T079) that belong to receipts with a status of 'completed' within the given date range. Then, format this data into a valid SIE 4 standard text file. The outcome is a fully functional SIE export. To test, extend the `test_export_api.py` contract test to approve a receipt, call the export endpoint, and verify that the content of the downloaded file is a valid SIE string containing the correct accounting data.'''
- [x] T083 [P] Implement the Company Card bundle export.
  - **Context:** The `GET /export/company-card` endpoint is a placeholder.
  - **Agent Prompt:** '''Your task is to implement the `export_company_card` function in `backend/src/api/export.py`. This function should, for a given statement ID, fetch the original invoice data and all its matched and approved receipt data (including images). You must bundle this information into a structured format, for example, a ZIP file containing the invoice summary as a JSON file and all related receipt images. The outcome is a complete export bundle for a reconciled company card statement. To test, extend the `test_firstcard_invoice_flow.py` to run a full match/approve cycle and then call this export endpoint, verifying the contents of the returned bundle.'''

## Phase 7: Finalize Admin UI
- [x] T084 [P] Display the detailed Validation Report in the UI.
  - **Context:** The receipt detail view only shows a raw status, not the detailed validation messages.
  - **Agent Prompt:** '''Your task is to modify the receipt detail view in `frontend/src/views/receipt_detail.js`. You must make a new API call to `GET /ai/api/receipts/<rid>/validation`. The JSON response, which contains a list of messages with severity, must be parsed and displayed in a human-readable format in the 'Validation' section of the UI. Errors should be red, warnings yellow. The outcome is an admin who can clearly see why a receipt failed validation. To test, you can manually run the frontend against a backend where a receipt is known to have validation errors.'''
- [x] T085 [P] Display and manage Proposed Accounting Entries in the UI.
  - **Context:** The receipt detail view has a placeholder for accounting entries.
  - **Agent Prompt:** '''Your task is to modify the receipt detail view in `frontend/src/views/receipt_detail.js`. You must call the `GET /ai/api/receipts/<rid>/accounting/proposal` endpoint (or its equivalent that fetches the saved proposals from T079). The proposed accounting entries must be rendered as a table in the 'Proposed Accounting' section. Each field (account, debit, credit) must be editable. A 'Save Proposal' button should send the (potentially modified) entries back to a new `PUT` endpoint on the backend. The outcome is an admin who can review and adjust the final accounting. To test, run the frontend and verify the accounting table is populated and editable.'''
- [x] T086 [P] Display and manage Line Items in the UI.
  - **Context:** The receipt detail view does not show or allow editing of line items.
  - **Agent Prompt:** '''Your task is to modify the receipt detail view in `frontend/src/views/receipt_detail.js`. You must call `GET /ai/api/receipts/<rid>/line-items` and render the line items in a new table. Each line item should be editable. A 'Save' button should send the updated list of line items back to the `PUT /ai/api/receipts/<rid>/line-items` endpoint. The outcome is that an admin can correct OCR errors in the line items. To test, run the frontend and verify the line items table is populated and can be edited and saved.'''





