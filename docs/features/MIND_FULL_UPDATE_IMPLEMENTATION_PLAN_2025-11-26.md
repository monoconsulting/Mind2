Toppen, då gör vi en “task board” för agenten.

Jag lägger upp det som **faser** med **små, tydliga uppdrag (1 uppdrag = 1 konkret grej att göra)**. Sen kan du copy-pasta varje task rakt in i en prompt och bara lägga till “follow the global rules…”.

------

## Phase A – Schema & Migrations (P0.1)

### A1 – Make `database/migrations` the only active migration directory

**Goal**: Migration runner must only look at `database/migrations` and nowhere else.
 **Scope**:

- Update `backend/src/services/db/migrations.py` to resolve a single `MIGRATIONS_DIR` → `database/migrations`.
- Remove all logic that scans `backend/migrations`.
   **Out of scope**:
- Editing any SQL migration files.
- Changing DB schema itself.
   **Deliverables**:
- Updated `migrations.py` with clear comments.
- Unit test confirming it only uses `database/migrations`.

------

### A2 – Consolidate `backend/migrations/0032..0038` into `database/migrations`

**Goal**: Ensure every schema change from `backend/migrations/0032..0038` is represented as an ordered SQL file in `database/migrations`.
 **Scope**:

- For each file in `backend/migrations/0032..0038`:
  - Compare with existing `database/migrations`.
  - If content not present, create a new `00XX_*.sql` in `database/migrations` and move SQL there.
  - Comment out the old file content with a header explaining where it moved.
     **Out of scope**:
- Changing SQL semantics (except for path/fully-qualified names if absolutely necessary for consistency).
   **Deliverables**:
- New migration files in `database/migrations`.
- All `backend/migrations/0032..0038` still present but fully commented with “Deprecated: moved to …”.

------

### A3 – Enforce migration filename pattern & ordering

**Goal**: Tooling that guarantees consistent migration numbering.
 **Scope**:

- In `services/db/migrations.py`, add logic to:
  - Scan `database/migrations`.
  - Validate `NNNN_*.sql` naming.
  - Ensure no duplicated numbers.
- Raise a clear exception on violations.
   **Deliverables**:
- Helper function in `migrations.py`.
- Unit tests covering:
  - Valid set.
  - Duplicate number.
  - Wrong filename pattern.

------

### A4 – Schema Source of Truth Documentation

**Goal**: Make it crystal clear where schema lives.
 **Scope**:

- New doc `docs/SYSTEM_DOCS/MIND_SCHEMA_SOURCE_OF_TRUTH.md`:
  - “Canonical schema = `database/migrations`.”
  - `backend/migrations` is deprecated, read-only history.
     **Deliverables**:
- Markdown doc with short, precise content.

------

## Phase B – Status & Workflow Consistency (P0.2)

### B1 – Introduce central status definitions module

**Goal**: One place for all status constants/enums.
 **Scope**:

- Create `backend/src/models/statuses.py` (or `services/workflow_statuses.py`).
- Define constants/enums for:
  - `unified_files.process_status` / `ai_status`.
  - `invoice_documents.processing_status`.
  - Any credit-card specific statuses.
- Do **not** yet replace usages – just central definition.
   **Deliverables**:
- New status module.
- Tests verifying constant values match existing DB values.

------

### B2 – Replace hard-coded status strings in `services/tasks/*`

**Goal**: Tasks use central constants, not literals.
 **Scope**:

- Search `backend/src/services/tasks` for status string literals.
- Replace them with imports from the status module.
- No behavioural change (same string values).
   **Out of scope**:
- Changing any API or DB field names.
- Introducing new statuses.
   **Deliverables**:
- Updated task modules.
- Comments where status mapping was unclear.

------

### B3 – Replace hard-coded status strings in `api/*`

**Goal**: Endpoints also use central status constants.
 **Scope**:

- Search `backend/src/api` for status literals.
- Replace with imports from status module.
- Keep behaviour identical.
   **Deliverables**:
- Updated API modules.
- Short note in status doc where endpoints rely on specific states.

------

### B4 – Document and align receipt/invoice/FC status transitions

**Goal**: Align code transitions with documented workflow.
 **Scope**:

- For each of:
  - Receipts workflow.
  - Invoices workflow.
  - FC workflow.
- Compare `MIND_WORKFLOW.md` to actual transitions (tasks + API).
- Add a small section in `MIND_STATUS_DEFINITIONS.md`:
  - Explicit state machine diagrams or bullet-point transitions.
- Where code diverges:
  - Document current real behaviour.
  - Mark TODO comments in code where future fix is needed (but **do not fix** in this task).
     **Deliverables**:
- Updated docs.
- TODO markers referencing the doc.

------

## Phase C – Ingestion, FTP & `unified_files` (P1.1 & P1.2)

### C1 – Create a unified FTP service module

**Goal**: Single abstraction for FTP operations.
 **Scope**:

- New `backend/src/services/ftp_service.py` with functions like:
  - `list_new_files(...)`
  - `download_file(...)`
- Implement using existing configuration/env.
- No caller migration in this task – only creation.
   **Deliverables**:
- New FTP service with docstrings and basic tests.

------

### C2 – Migrate one existing FTP path to `ftp_service`

**Goal**: Prove `ftp_service` works by migrating one path.
 **Scope**:

- Choose one concrete, currently used FTP entry point (e.g. main scheduled fetch).
- Replace direct FTP logic with calls to `ftp_service`.
- Keep behaviour identical, same logging.
   **Out of scope**:
- Deleting old helper modules.
   **Deliverables**:
- Updated caller(s).
- Comments in old code pointing to new module.

------

### C3 – Implement `create_unified_file(...)` in `services/db/files.py`

**Goal**: Single entry point for creating `unified_files`.
 **Scope**:

- Implement `create_unified_file(...)` that:
  - Inserts to `unified_files`.
  - Sets all relevant fields (process_status, ai_status, content_hash, etc.).
  - Handles duplicate detection (`content_hash` + company).
     **Deliverables**:
- New function.
- Unit tests for:
  - New file.
  - Duplicate.

------

### C4 – Migrate ingestion endpoints to use `create_unified_file(...)`

**Goal**: All ingest paths use the unified function.
 **Scope**:

- Find all places that insert into `unified_files` directly.
- Replace with call to `create_unified_file(...)`.
- Add comments where previous behaviour was odd (e.g. missing hash).
   **Deliverables**:
- Updated ingestion code.
- Small doc snippet explaining “All file creation goes through `create_unified_file`”.

------

### C5 – Start workflow run at ingestion

**Goal**: Every file gets a `workflow_runs` row at creation.
 **Scope**:

- Implement `start_workflow_for_file(unified_file_id, workflow_type)` helper.
- Call it after `create_unified_file(...)` in all ingestion paths.
- Assign sensible `workflow_type` values based on existing flows.
   **Deliverables**:
- Helper function.
- Updated ingestion paths.
- Tests that verify `workflow_runs` gets created.

------

## Phase D – FirstCard Workflow (Fas 3 core)

### D1 – Implement/complete FirstCard WorkflowCoordinator

**Goal**: Central coordination for FC import & stages.
 **Scope**:

- In `workflow_tasks.py` or dedicated coordinator:
  - Implement `create_workflow_run`, `begin_import_stage`, `complete_import_stage`, `dispatch_workflow` for FC.
- Ensure they:
  - Log to `workflow_runs` / `workflow_stage_runs`.
  - Use central status constants.
     **Deliverables**:
- Coordinator methods with tests (can be DB-mocked).

------

### D2 – Route FC import/resume through WorkflowCoordinator

**Goal**: No FC endpoint bypasses Coordinator.
 **Scope**:

- Identify FC endpoints/tasks that:
  - Start import.
  - Resume import.
- Replace direct manipulation of `workflow_runs` / `processing_status` with Coordinator calls.
   **Deliverables**:
- Updated endpoints/tasks.
- Inline comments referencing D1.

------

### D3 – Remove manual FC status updates in tasks & endpoints

**Goal**: All FC status changes go through central machinery.
 **Scope**:

- Search FC-related code for:
  - `UPDATE invoice_documents SET processing_status=...` etc.
- Replace with:
  - Status constants.
  - Coordinator / dedicated transition helpers.
     **Deliverables**:
- Refactored code.
- No raw status literals in FC modules.

------

### D4 – Make FC detail views use `invoice_documents` + `invoice_lines` only

**Goal**: One canonical data source for FC details.
 **Scope**:

- Review FC detail endpoints (those feeding Manual Match & admin views).
- Ensure they read:
  - Document header from `invoice_documents`.
  - Lines from `invoice_lines`.
- If legacy tables still used for *display*: comment code and route via the new canonical structure instead.
   **Deliverables**:
- Updated endpoints.
- Commented legacy reads with explanation.

------

### D5 – FC workflow integration tests (import → AI → manual match → confirm)

**Goal**: Prove that the entire FC flow works end-to-end.
 **Scope**:

- Create integration tests (API-level) that:
  - Simulate import of FC statement.
  - Trigger AI/OCR step (can be stubbed).
  - Use manual match API to match lines.
  - Confirm statement when all matched.
     **Deliverables**:
- Test suite.
- Short markdown description of the test flow.

------

### D6 – FC resume & restart tests

**Goal**: FC workflows can be resumed/restarted safely.
 **Scope**:

- Add tests that:
  - Take a partially completed FC document.
  - Call resume endpoint → verify continuation.
  - Call restart → new `workflow_run` created, history preserved.
     **Deliverables**:
- Tests.
- Clarifying comments on behaviour (resume vs restart).

------

## Phase E – Manual Match Polish

### E1 – Pagination / lazy loading in ManualMatch UI

**Goal**: ManualMatch.jsx handles large datasets gracefully.
 **Scope**:

- Add pagination or infinite scroll for:
  - Statement lines.
  - Receipt list per period.
- Keep existing behaviour, just improve UX.
   **Deliverables**:
- Updated `ManualMatch.jsx`.
- Short note in a doc about new query params/endpoints if added.

------

### E2 – Toasts & error handling in ManualMatch UI

**Goal**: Clear feedback on failures.
 **Scope**:

- Wrap API calls in ManualMatch in error handling.
- Show user-friendly toasts/messages on:
  - Failed fetch of statements/lines/receipts.
  - Failed match/unmatch.
  - Failed confirm.
     **Deliverables**:
- Updated UI.
- Possibly small helper for consistent error messaging.

------

### E3 – API-level tests for ManualMatch

**Goal**: Stable API behaviour for ManualMatch.
 **Scope**:

- Add tests for endpoints used by ManualMatch:
  - List statements.
  - List lines for statement.
  - List receipts in period.
  - Match line to receipt.
  - Confirm full match.
     **Deliverables**:
- Test suite.
- Clear fixture data definitions.

------

## Phase F – AI Pipeline (P2)

### F1 – Extract provider-only layer from `ai_service.py`

**Goal**: Providers do only network calls, nothing else.
 **Scope**:

- Ensure `services/ai/providers/*.py`:
  - Contain only low-level model calls, retries, error mapping.
  - No domain logic.
- Move any domain-ish code from providers into `ai_service.py` or domain helpers.
   **Deliverables**:
- Clean providers.
- Tests for provider error mapping.

------

### F2 – Define orchestrator functions per AI step

**Goal**: One orchestrator method per logical AI step in workflow.
 **Scope**:

- For each AI step in `MIND_WORKFLOW.md` (AI1–AIx):
  - Add a dedicated orchestrator function in `ai_service.py`.
  - Each function:
    - Selects provider/model.
    - Builds prompt.
    - Calls provider.
    - Hands result to domain validator.
       **Deliverables**:
- Orchestrator methods.
- Unit tests with mocks.

------

### F3 – Harden Pydantic domain models in `models/ai_processing.py`

**Goal**: Strong validation for AI responses.
 **Scope**:

- Review Pydantic models.
- Add validation for:
  - Types.
  - Value constraints.
  - Optional vs required fields.
- Adjust parsers to always go through these models.
   **Deliverables**:
- Updated models.
- Tests that feed invalid/partial payloads and assert validation errors.

------

### F4 – Unified `ai_processing_history` logging helper

**Goal**: All AI calls are logged consistently.
 **Scope**:

- Implement helper `log_ai_call(...)` that writes to `ai_processing_history`:
  - entity id, type.
  - prompt key.
  - model.
  - outcome.
  - error info.
- Route all AI calls through this helper.
   **Deliverables**:
- Helper.
- Tests verifying log rows are created.

------

## Phase G – Tasks, Legacy Code & Observability (P3)

### G1 – Classify tasks: active vs legacy vs unused

**Goal**: Map out what’s actually used.
 **Scope**:

- Scan all `services/tasks/*.py`.
- For each task entry point:
  - Mark as active / legacy / unused in comments + a simple markdown table in `docs/SYSTEM_DOCS/TASK_INVENTORY.md`.
     **Deliverables**:
- Inventory doc.
- Comments in code.

------

### G2 – Upgrade logging in active tasks

**Goal**: All active tasks log in a structured, consistent way.
 **Scope**:

- For tasks marked “active”:
  - Use `observability/logging.py` helpers.
  - Log start, key parameters, and outcome.
     **Deliverables**:
- Updated tasks.
- No plain `print()` left in active code paths.

------

### G3 – Retire unused tasks (commented, not deleted)

**Goal**: Remove noise while preserving history.
 **Scope**:

- For tasks labelled “unused” in inventory:
  - Comment out implementations.
  - Add header: “Retired – not used as of 2025-11-26, kept for history.”
     **Deliverables**:
- Commented-out blocks.
- No change in behaviour (since they were unused).

------

### G4 – Error propagation & no-silent-fail in tasks

**Goal**: Tasks must not fail silently.
 **Scope**:

- Review active tasks for:
  - `return None` on error.
  - bare `except:` with no log.
- Replace with:
  - Explicit exceptions or
  - Explicit error objects + logged error.
     **Deliverables**:
- Updated tasks.
- Tests for at least a few representative error paths.

------

## Phase H – Documentation & DX (P4)

### H1 – Sync `MIND_WORKFLOW.md` with FC v2 design

**Goal**: Workflow doc matches the real FC implementation.
 **Scope**:

- Update FC sections to:
  - Use `invoice_documents` + `invoice_lines` as canonical.
  - Describe how legacy `creditcard_*` is used (AI/historical).
     **Deliverables**:
- Updated doc.

------

### H2 – Schema overview doc

**Goal**: Quick orientation in DB.
 **Scope**:

- Create `MIND_SCHEMA_OVERVIEW.md`:
  - List all tables.
  - 1–3 lines per table describing purpose.
  - Link to migration creating it.
     **Deliverables**:
- Markdown overview.

------

### H3 – Workflow debugging guide

**Goal**: Make it easy to debug a file’s journey.
 **Scope**:

- New `WORKFLOW_DEBUGGING.md`:
  - How to find file in `unified_files`.
  - How to follow `workflow_runs` / `workflow_stage_runs`.
  - How to re-run/resume safely.
     **Deliverables**:
- Markdown guide.

------

### H4 – Agent master prompt file

**Goal**: One place with all rules for agents.
 **Scope**:

- Create `.prompts/mind_refactor.prompt.md` containing:
  - Global rules (no deletion, no mock data, etc.).
  - Reference to this task list.
  - Pointers to key docs.
     **Deliverables**:
- Prompt file ready to paste into VS Code / agent configs.

------

If du vill kan vi nu ta **en av dessa tasks (t.ex. A1 eller D1)** och skriva en *stenhård agent-prompt* specifikt för den – med filpaths, testkrav och “forbidden actions” inbakat.