Jag har gått igenom:

* Python-backendet (`backend/src/...`)
* Databasmigrationer (`database/migrations` + `backend/migrations`)
* MySQL-dumpen (`.dbbackup/Mind2_mono_se_db_9_2025-11-25_12-34.sql`)
* Dokumentation (framför allt `docs/SYSTEM_DOCS/MIND_WORKFLOW.md`, `FULL_TECHNICAL_REVIEW_20250922_0959.md`, AI-dokument osv)
* Förråds-/hjälpkod (`services/db`, `services/tasks`, `services/ai`, `services/fetch_ftp*`, `services/storage`, osv)
* Testerna under `backend/tests`

Nedan först en *mänsklig* analys på svenska, och sedan en *engelskspråkig, extremt hård agent-plan* i prioriterad ordning som du kan stoppa direkt i en kod-agent.

---

## 1. Överblick – vad du har idag

**Backend**

* Flask-app i `backend/src/api/app.py` med:

  * System-endpoints (`/health`, `/system/status`, `/system/stats`, `/system/metrics`, `/system/config`).
  * Routing till kvitto/FC/invoice-flöden via separata moduler (`api/receipts.py`, `api/reconciliation_firstcard.py`, `api/ingest.py`, `api/fetcher.py`, osv).
  * CORS, auth-middleware, rate limiting, JSON-logging & Prometheus-metrics via `api/middleware.py`, `observability/*`, `api/limits.py`.

* **Tjänstelager** i `backend/src/services`:

  * DB-lager (`services/db/connection.py`, `services/db/files.py`, `services/db/migrations.py`).
  * AI-lager (`services/ai_service.py`, `services/ai/providers/*`, modeller i `models/ai_processing.py`).
  * OCR/PDF/filer (`services/pdf_conversion.py`, `services/ocr.py`, `services/file_detection.py`, `services/storage.py`).
  * Ingest/FTP (`services/fetch_ftp.py`, `fetch_ftp_enhanced.py`, `fetch_ftp_updated.py`, `fetch_ftp_backup.py`).
  * Workflow & Celery-tasks (`services/tasks/*`, inkl. `legacy.py`, `workflow_tasks.py`, `file_management_tasks.py`, `creditcard_tasks.py`, `invoice_tasks.py`, `ocr_tasks.py`).

* **Domänmodeller** i `backend/src/models/*` (t.ex. `accounting.py`, `receipts.py`, `company_card.py`, `ai_processing.py`) – huvudsakligen `dataclass`-baserade.

* **Konfiguration** via `backend/src/config.py` + `.env` (DB, Redis, AI-providers, feature flags osv).

* **Tester**: hyfsat omfattande pytest-suite under `backend/tests` (unit + en del integrerade scenarion: file detection, invoice-tasks, AI-pipeline, m.m.).

**Databas (MySQL 8.4.6)** – 27 tabeller i dumpen, bl.a.:

* AI-relaterat:

  * `ai_accounting_proposals`, `ai_accounting_proposals_fc_backup`
  * `ai_llm`, `ai_llm_model`, `ai_processing_history`, `ai_processing_history_fc_backup`
  * `ai_processing_queue`, `ai_system_prompts`
* Bokföring/struktur:

  * `chart_of_accounts`, `companies`
* Kort & matchning:

  * `creditcard_invoices_main`, `creditcard_invoice_items`, `creditcard_receipt_matches`
* Kvitton & fakturor:

  * `unified_files`, `receipt_items`, `receipt_items_fc_backup`
  * `invoice_documents`, `invoice_lines`, `invoice_line_history`
* Taggar & metadata:

  * `tags`, `tag_categories`, `file_categories`, `file_suffix`, `file_locations`
* Workflow:

  * `workflow_runs`, `workflow_stage_runs`

Migrationerna ligger huvudsakligen under `database/migrations/0001..0031`, plus några “senare” i `backend/migrations/0032..0038`.

**Dokumentation**

* `MIND_WORKFLOW.md` beskriver ett ganska tydligt steg-för-steg-flöde (FTP → OCR → AI-klassning → AI-data → manuell kontroll → export).
* `FULL_TECHNICAL_REVIEW_20250922_0959.md` visar att en större omtagning (v2.0, ren Python-stack) är genomförd men att systemet fortsatt växer.
* Flera AI-/pipeline-dokument som beskriver AI-stegen, prompts och historik.

---

## 2. Viktigaste problemområden jag ser

### 2.1 Kodstruktur & lager – bra grund, men mycket “läckage”

**Bra:**

* Tydliga mappar: `api`, `services`, `models`, `observability`, `services/db`, `services/tasks`.
* DB-åtkomst ligger i separata moduler (`services/db/*`).
* Workflow-tänk i tabellerna `workflow_runs` och `workflow_stage_runs`.

**Mindre bra / problem:**

1. **Direkt SQL överallt**

   * Många funktioner i `services/db/files.py`, `services/db/..`, `services/tasks/*`, `api/*` kör SQL direkt.
   * Statusfält (`ai_status`, process-statuses, soft delete osv) uppdateras på många ställen, ofta med hårdkodade strängar.

2. **Blandning av ansvar**

   * Vissa service-funktioner gör allt: hämtar filer, kallar AI, uppdaterar DB, triggar nästa steg, loggar, hanterar fel, mm.
   * `ai_service.py` blandar:

     * LLM-anrop via providers
     * Parsering/validering av resultat
     * Domän-logik (company detection, belopp, moms, etc).

3. **Inkonsekvent domänmodellering**

   * Domändataclasses finns, men används inte konsekvent genom hela koden.
   * Vissa API-endpoints returnerar “råa JSON-dicts”, andra använder tydligare modeller.

**Konsekvens:** Svårt att:

* Förutse hur en ändring påverkar flödet.
* Lägga till nya workflows/filtyper utan att kopiera/klippa-och-klistra.
* Lita på att statusar alltid följer samma transitionsregler.

---

### 2.2 Duplicerad och “legacy” kod

Det här sticker ut som refactor-guld:

* **FTP & ingest:**

  * `services/fetch_ftp.py`
  * `services/fetch_ftp_enhanced.py`
  * `services/fetch_ftp_updated.py`
  * `services/fetch_ftp_backup.py`

  De gör i princip samma sak med små skillnader (logik för filter, metadata, kategorisering, felhantering).

* **Tasks & workflow:**

  * `services/tasks/legacy.py` innehåller gamla Celery-tasks som fortfarande importerar massa grejer från `common.py` och `services.tasks`.
  * Nya tasks finns i `workflow_tasks.py`, `file_management_tasks.py`, `invoice_tasks.py`, `creditcard_tasks.py`, osv.

* **Databas-migrationer:**

  * “Gamla” under `database/migrations/0001..0031`.
  * Senare patchar under `backend/migrations/0032..0038`.
  * `services/db/migrations.py` försöker vara generisk och hitta migrationsmapp i både repo och container.

**Konsekvens:**

* Risk att olika vägar (t.ex. “gammal FTP” vs “ny FTP”) gör *nästan* samma sak men skiljer lite på statusar, metadata eller error-handling.
* Svårt för en agent (eller människa) att veta vilken fil som är “sanningen”.
* Risk att vissa migrations inte körs (fel mapp, dubbla 0007, olika 0015-filer etc).

---

### 2.3 Workflow & status-hantering

Du har:

* Workflowtabeller: `workflow_runs`, `workflow_stage_runs`.
* Statusfält direkt på `unified_files`, `invoice_documents`, osv.
* Dokumentation i `MIND_WORKFLOW.md` som säger hur status *bör* röra sig.

I koden:

* Många `UPDATE unified_files SET ai_status=...`, `process_status`, “soft delete” osv på olika ställen.
* Tasks i `services/tasks/*` driver workflowet men i praktiken uppdateras status även från t.ex. API-endpoints (manuell återstart, upload, resume osv).
* Kreditkortsflödet (`reconciliation_firstcard.py`, `creditcard_tasks.py`) har egna statusar och “FC-backup” tabeller.

**Konsekvens:**

* Soft-delete, reprocessing och “resume” blir lätt glitchiga.
* Svårt att implementera nya steg (t.ex. extra AI-kontroll) utan att paja nån kantlogik.
* Att felsöka kräver att man “gör en mental join” mellan:

  * `unified_files`,
  * `creditcard_*`,
  * `workflow_runs`,
  * `ai_processing_history` / `ai_processing_queue`.

---

### 2.4 AI-lagret

* Bra att du har `services/ai/providers/*` och `ai_service.py`.
* Tabeller för prompts, modeller, queue, history är tydliga (`ai_system_prompts`, `ai_llm_model`, `ai_processing_queue`, `ai_processing_history`).

Men:

* `ai_service.py` har en docstring som säger att rule-baserade funktioner är borttagna och att AI3 *bara* kör LLM – men själva klassen beskriver fortfarande “deterministic extraction” etc. Det tyder på att koden varit ombyggd flera gånger.
* Valideringen med Pydantic är bra, men det finns fortfarande rätt mycket specialfall/procedurer som sitter direkt i service-klassen.

**Konsekvens:**

* Hög kognitiv belastning för den som ska ändra i AI-flödet.
* Svårt att plugga in en annan provider/konfiguration utan att röra domänlogik.

---

### 2.5 Observability, felhantering & encoding

* Du har redan:

  * `configure_json_logging` i `observability/logging.py`.
  * Prometheus-metrics i `observability/metrics.py`.
  * CORS & auth-middleware i `api/middleware.py`.
* Men i services finns fortfarande:

  * `print` / “halv-loggning”.
  * Ställen där exceptions endast loggas och sedan returnerar `None` (t.ex. FTP-kod), vilket ger otydliga 500-fel längre upp.
* Encodning/locale är viktigt för dig (svenska kvitton, `SWEDISH_ENCODING_RULES.md`), men inte konsekvent centraliserat – vissa endpoints sätter content-type manuellt, andra litar på Flask default.

---

### 2.6 Tester

* Det finns mycket testkod, men:

  * Den speglar i första hand “hur det funkade då”, inte nödvändigtvis nuvarande workflow-dokumentation.
  * E2E-/scenariotester för fulla flöden (FTP → OCR → AI → export) verkar mer spridda, och Playwright-tester finns i ett separat web-doc-/test-repo.

**Konsekvens:** Refactoring är farlig men också nödvändig – vi måste ha en väldigt tydlig plan för vad agenten får/inte får göra, så den kan förlita sig på testerna utan att bända sönder beteenden.

---

### 2.7 Dokumentation & “single source of truth”

* Du har **många** bra dokument, inklusive en tidigare full teknisk review.
* Men när koden ändrats (AI3, nya workflowtabeller, extra migrations) har inte alla doc-filer följts upp.
* Det finns t.o.m. olika versioner av migrations-dokumentation (flera 0007, flera 0015-filer).

**Konsekvens:** Svårt att veta om “sanningen” står i:

* databasen (dumpen),
* `database/migrations`,
* docs,
* eller i folks huvuden.

---

## 3. Prioriterad förbättrings- och refactor-plan

Nedan kommer nu **den engelska, agent-anpassade planen**.

### Viktigt om formatet:

* Den är **helt riktad till en kod-agent** som arbetar i detta repo.
* Den är uppdelad i **P0, P1, P2, P3** (prio-ordning).
* Den innehåller:

  * *Scope-regler* (vad agenten får göra).
  * *Tekniska constraints* (ingen ny funktionalitet, inga mockar, inga påhittade värden).
  * *Konkreta tasks med fil- och tabellnamn*.

Den här planen kan du lägga i t.ex. `.github/prompts/implement_mind_refactor.prompt.md` eller köra via din befintliga agent-setup.

---

## IMPLEMENTATION PLAN FOR CODE AGENT (ENGLISH, HARD SCOPE)

### 0. Global rules for the agent

You are working on the **Mind** backend codebase and its MySQL schema.

You must obey these rules strictly:

1. **Scope & Safety**

   * Do **not** add new end-user features.
   * Your mission is:
     **“Refactor and harden the existing system so that it is easier to maintain, and its workflows become more predictable and observable – without changing the external behaviour.”**
   * If you need to choose between “pretty code” and “behaviour parity”, you must always prefer **behaviour parity**.

2. **No invented data, no mocks, no pseudo-schemas**

   * You must not invent:

     * fake DB tables,
     * fake columns,
     * fake config values,
     * or mock implementations.
   * All schema knowledge must come from:

     * `database/migrations/*.sql`
     * `backend/migrations/*.sql`
     * and the existing code.
   * When writing tests, you must use the **real schema** and real migrations. No hand-written pseudo schemas.

3. **No silent deletions**

   * You must **not** delete code outright.
   * If you need to retire or replace a function/module:

     * Keep the original implementation, **comment it out**, and prepend a clear explanation in English:

       * Why it is commented.
       * Which new function/module replaces it.
       * Which ticket / task this change belongs to (if available).
   * This is especially important for:

     * `services/fetch_ftp*.py`
     * `services/tasks/legacy.py`
     * any workflow-related code.

4. **No cross-cutting “drive-by” changes**

   * Do not touch files that are outside the current task’s scope.
   * If you must touch a file (even a small import), document in a comment at the top of the diff **why this file is affected**.

5. **Preserve public API**

   * All existing HTTP endpoints and their JSON formats must remain compatible:

     * URLs
     * HTTP methods
     * Response structure and field names
     * Error codes
   * You may improve internal validation and error messages, but **not** the public contract.

6. **Migrations and database compatibility**

   * You must not break existing production data.
   * Any change to the schema must:

     * be implemented as a new migration under `database/migrations/XXXX_name.sql` (or in the already used numbering pattern),
     * be idempotent when applied to an existing production DB that already contains previous migrations,
     * be reflected in `services/db/*` code.
   * You must not edit old migrations; add new ones instead.

7. **Tests**

   * Before changing any non-trivial logic:

     * Locate the relevant tests under `backend/tests`.
     * If no tests exist, add **targeted** tests for the behaviour that you are about to refactor.
   * After refactoring:

     * All existing tests must still pass.
     * New tests must be clear and deterministic, and use the real schema/migrations.

8. **Encoding and locale**

   * Follow the rules in `docs/SWEDISH_ENCODING_RULES.md`:

     * UTF-8 everywhere.
     * Swedish characters must be stored and returned correctly.
   * When touching endpoints that return JSON, ensure `application/json; charset=utf-8` is set (as already done in `api/app.py`).

---

### P0 – Baseline: Schema, migrations & workflow health

**Goal:** Ensure that **database structure, migrations and code are aligned** so that all workflows (receipts, invoices, credit card, AI) run on a stable foundation.

#### P0.1 – Canonical migrations and schema

1. Inspect:

   * `database/migrations/0001_...` – `0031_...`
   * `backend/migrations/0032_...` – `0038_...`
   * `backend/src/services/db/migrations.py`
   * MySQL dump structure (table names and columns – you can infer from the codebase even if the dump is not present in your environment).

2. Enforce a **single source of truth** for migrations:

   * Keep `database/migrations` as the canonical location.
   * For each file under `backend/migrations`:

     * Check if it’s already represented under `database/migrations`.
     * If not, move its content into a **new** numbered migration in `database/migrations` and comment the old file body:

       * Add a comment at the top:
         `-- Deprecated: content moved to database/migrations/00XX_...sql (keep for historical reference only).`
   * Update `services/db/migrations.py` so that:

     * It resolves **only** `database/migrations` in a repo context.
     * It still handles the container path resolution (no behaviour change for production).

3. Introduce a simple, explicit migration order check:

   * In `services/db/migrations.py`, add a small testable function that:

     * Lists all `.sql` files in `MIGRATIONS_DIR`,
     * Sorts them lexicographically,
     * Fails with a clear exception if:

       * A file name breaks the numbering pattern,
       * Or there are duplicate numbers (e.g. two `0007_*.sql`).
   * Add unit tests in `backend/tests/unit` to cover this.

#### P0.2 – Workflow status consistency

1. Collect all status values used in code:

   * Search in:

     * `backend/src/services/tasks/*`
     * `backend/src/services/db/*`
     * `backend/src/api/*`
   * Focus on:

     * `unified_files` statuses (AI, process, soft delete).
     * `invoice_documents` / `invoice_lines` statuses.
     * `creditcard_*` statuses.
     * Workflow stages in `workflow_runs` / `workflow_stage_runs`.

2. Create a single **status definition module**:

   * Use `backend/src/models` or `backend/src/services` (for example `models/statuses.py` or `services/workflow_statuses.py`).
   * Define:

     * Python `Enum` or constant classes for:

       * File process status
       * AI status
       * Workflow stage types (if applicable)
       * Credit card reconciliation statuses
   * Replace all hard-coded status strings with these centralized constants.
   * Do **not** change existing values; only centralize them.

3. Ensure that **all status transitions** follow `docs/SYSTEM_DOCS/MIND_WORKFLOW.md`:

   * For each major workflow:

     * Receipts
     * Invoices
     * Credit card statements
   * Identify where transitions happen:

     * Celery tasks (`services/tasks/*`),
     * API endpoints (`api/receipts.py`, `api/reconciliation_firstcard.py`, `api/ingest.py`, etc).
   * If you find a deviation from the documented workflow:

     * First, add/extend tests that capture current behaviour.
     * Then introduce a small, **documented**, migration towards the documented flow (for example, map an obsolete status to a new canonical one).
     * Document the change in a comment, and cross-reference `MIND_WORKFLOW.md`.

---

### P1 – Ingestion & file lifecycle refactor

**Goal:** Make file ingestion and lifecycle (FTP + upload → storage → unified_files) predictable, deduplicated and easy to extend.

#### P1.1 – Unify FTP ingestion

Scope: **Only** FTP ingestion and its direct helpers.

1. Identify all FTP-related modules:

   * `backend/src/services/fetch_ftp.py`
   * `backend/src/services/fetch_ftp_enhanced.py`
   * `backend/src/services/fetch_ftp_updated.py`
   * `backend/src/services/fetch_ftp_backup.py`
   * Any usages in:

     * `backend/src/api/fetcher.py`
     * `backend/src/services/tasks/file_management_tasks.py`
     * `backend/src/services/storage.py`
     * `backend/src/services/db/files.py`

2. Design a single **FTP ingestion service**:

   * Create a coherent implementation in one module, e.g. `services/fetch_ftp_enhanced.py` or `services/fetch_ftp_unified.py`.
   * Steps to standardize:

     * Connection (FTP vs FTP_TLS, timeouts, TLS settings).
     * File enumeration and filtering.
     * File category detection via DB (`file_suffix`, `file_categories`).
     * Metadata extraction and JSON sidecar handling.
     * Error handling and logging (structured logs via `logging`).

3. Migrate call sites:

   * Update all callers to use the new unified service.
   * In each of the older modules that you no longer want to use:

     * Comment out the old logic.
     * Leave a clear comment at the top:

       * `# Deprecated: replaced by services.fetch_ftp_unified.<function>. Kept for historical reference only.`

4. Tests:

   * Add unit tests for the unified FTP service:

     * Happy path (new files fetched, stored, statuses set).
     * Error conditions (failed connection, partial failures, file category not found).
   * Ensure that existing FTP tests (if any) are updated to the new implementation.

#### P1.2 – File storage and unified_files alignment

Scope: `services/storage.py`, `services/db/files.py`, any direct `unified_files` insert/update.

1. Standardize the **“create file”** path:

   * Introduce a single public function in `services/db/files.py`, e.g. `create_unified_file(...)`, that:

     * Inserts into `unified_files`.
     * Sets:

       * `file_type`
       * `ai_status`
       * `process_status`
       * `content_hash` (if available)
       * `company_id` (if known)
       * `submitted_by` (if applicable)
     * Handles duplicates by raising `DuplicateFileError` (already defined).

   * Ensure **all** file creation (FTP and upload) uses this function.

2. Deduplication:

   * Confirm use of `content_hash` (see migration `0016_add_content_hash_to_files.sql`).

   * Implement deduplication in `create_unified_file`:

     * If a file with the same content hash and company already exists:

       * Decide based on current behaviour whether to:

         * skip creation, or
         * store as “duplicate” with a flag (there is already an `is_duplicate` pattern).

   * Add tests for:

     * Duplicate detection path.
     * Correct setting of duplicate flags.

3. Align with workflow tables:

   * When a file is created, ensure that the corresponding **workflow run** is created (if this is expected by the design).
   * If currently the workflow tables are not consistently populated, you can:

     * Add a “bridge” function, e.g. `services/workflow_runs.start_workflow_for_file(unified_file_id, workflow_type)` that creates a `workflow_runs` row.
     * Call that function from the ingestion path, without changing the external API.

---

### P2 – AI pipeline refactor (structure, not behaviour)

**Goal:** Make the AI pipeline easier to reason about and configure, without changing what the AI does.

#### P2.1 – Separate orchestration, providers and domain validation

Scope: `services/ai_service.py`, `services/ai/providers/*`, `models/ai_processing.py`, `services/tasks/ai_pipeline_tasks.py`, `ai_*` tables.

1. Split responsibilities:

   * **Provider layer** (`services/ai/providers/*.py`):

     * Contains all code that talks to external AI APIs (OpenAI, Azure, Ollama).
     * Must not contain domain-specific business logic (no “Swedish VAT rules” here).
   * **Orchestration layer** (`services/ai_service.py`):

     * Coordinates provider calls.
     * Applies prompts and model selection using `ai_llm_model`, `ai_system_prompts`.
     * Handles retries, timeouts, rate limiting.
   * **Domain validation layer** (`models/ai_processing.py` + helper functions):

     * Uses Pydantic models to validate and normalize AI results into:

       * Document classification.
       * Receipt/invoice items.
       * Accounting proposals.

2. Refactor `ai_service.py`:

   * Extract any remaining hardcoded parsing logic into smaller, well-named functions.
   * Ensure that for each AI step described in `MIND_WORKFLOW.md` (AI1, AI2, AI3 etc) there is:

     * A clear orchestrator method.
     * A clear provider call.
     * A clear validation/data-mapping function.

3. Ensure full traceability into `ai_processing_history`:

   * For each AI call:

     * Write a row to `ai_processing_history` including:

       * document id (receipt, invoice, credit card),
       * prompt id or key,
       * model id,
       * result status (success/failure),
       * any error message.
   * If this already exists, ensure that **all** AI calls go through the same function that writes the history row.

4. Tests:

   * Strengthen tests under `backend/tests/unit` for:

     * Schema validation (`models/ai_processing.py`).
     * Provider selection logic.
     * Error handling (timeouts, invalid JSON, missing fields).

---

### P3 – Tasks, workflows and observability

**Goal:** Make Celery tasks and workflow execution easier to debug and operate.

#### P3.1 – Clarify legacy vs new tasks

1. Identify all task entry points:

   * `services/tasks/legacy.py`
   * `services/tasks/workflow_tasks.py`
   * `services/tasks/file_management_tasks.py`
   * `services/tasks/invoice_tasks.py`
   * `services/tasks/creditcard_tasks.py`
   * `services/tasks/ocr_tasks.py`

2. For each task:

   * Determine whether it is:

     * **actively used in the current workflow** (search in code and tests),
     * **only used by legacy paths**,
     * or **dead code** (no references).

3. Refactor:

   * For actively used tasks:

     * Ensure they use the centralized status module from P0.2.
     * Ensure they log with structured logging (no prints).
   * For legacy/dead tasks:

     * Comment them out (do not delete).
     * Add explanatory comments stating:

       * If they are still used by any external system.
       * That the new recommended path is `workflow_tasks.<...>` (if applicable).

#### P3.2 – Observability and error propagation

1. Use `observability/logging.py` and `observability/metrics.py` consistently:

   * Replace ad-hoc logging in:

     * FTP services,
     * tasks,
     * AI orchestration,
     * file ingestion.
   * Ensure that each task:

     * logs start, key parameters, and outcome (success/failure),
     * increments relevant metrics (if available).

2. Ensure error propagation is explicit:

   * Do not hide exceptions by returning `None` silently.
   * When exceptions must be swallowed to preserve behaviour:

     * Log them with level `ERROR` and enough context (file id, company id, task name).
     * Return a clear error state that the caller can handle.

---

### P4 – Documentation & dev UX

**Goal:** Make it easy for future humans and agents to understand the system.

1. Synchronize docs with code:

   * Update `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` to reflect any clarifications made in P0–P3.
   * Add a short “schema overview” doc that:

     * Lists all 27 tables and their main purposes.
     * Links each table to:

       * its migration file,
       * its primary service module.

2. Developer “quickstart” for debugging workflows:

   * Under `docs/SYSTEM_DOCS`, add a “WORKFLOW_DEBUGGING.md” that explains:

     * How to run the backend locally.
     * How to run migrations.
     * How to inspect workflow/run state for a given file id.
     * How to re-run a workflow step for a single file without side effects.

3. Agent instructions file:

   * Add an **explicit** agent prompt file under `.github/prompts` or `.prompts` (you already have several), e.g. `mind_refactor.prompt.md`.
   * This file should contain:

     * The global rules from section 0 above.
     * The phase descriptions (P0–P3).
     * Pointers to the key files and directories.

---
