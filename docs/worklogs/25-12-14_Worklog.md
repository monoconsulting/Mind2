# 25-12-14_Worklog.md - Daily Engineering Worklog

---

## 0) TL;DR (3-5 lines)

- **What changed:** Fixed AI4 "account_code is missing" error by actually passing `chart_of_accounts` to LLM, made `item_id` optional for settlement lines, fixed backup script to abort if DB dump missing from zip, repaired `chart_of_accounts` table with BAS 2025 data (1318 rows), updated SoT documentation.
- **Why:** AI4 was failing because chart_of_accounts parameter was being ignored - LLM had no valid accounts to choose from. Settlement lines (e.g., 2440 Leverantörsskulder) correctly have null item_id.
- **Risk level:** Low (bug fixes, no schema changes, backward compatible)
- **Deploy status:** Requires container restart to pick up backend changes.

---

## 1) Metadata

- **Date (local):** 2025-12-14 (Europe/Stockholm)
- **Author:** Claude Opus 4.5
- **Project/Repo:** Mind2
- **Branch:** `dev`
- **Commit range:** `899c00e..WORKING_TREE` (uncommitted changes)
- **Related tickets/PRs:** AI4 failure investigation
- **Template version:** 1.1

---

## 2) Goals for the Day

- Fix AI4 "account_code is missing" error
- Repair corrupted chart_of_accounts table with BAS 2025 data
- Update backup script to enforce DB dump inclusion
- Update Source of Truth documentation

**Definition of done today:** AI4 successfully generates accounting proposals with valid BAS 2025 account codes.

---

## 3) Environment & Reproducibility

- **OS / Kernel:** Windows (host)
- **Runtime versions:** Docker Compose (MySQL/Redis/ai-api/celery-workers)
- **Containers:** `mind2` compose stack (main)
- **Data seeds/fixtures:** `docs/Kontoplan-BAS-2025.csv` for chart_of_accounts import
- **Feature flags:** N/A
- **Env vars touched:** N/A

**Exact repro steps:**

1. `mind_docker_compose_up.bat`
2. Upload receipt and wait for AI4 processing
3. Check `ai_accounting_proposals` table for generated entries

---

## 4) Rolling Log (Newest First)

### Daily Index

| Time | Title | Change Type | Scope | Files Touched |
|---|---|---|---|---|
| 21:20 | Stop migration replay + prompt overwrite | fix | `db/migrations` | `backend/src/services/db/migrations.py`, `backend/src/api/ai_config.py`, `backend/src/api/app.py`, `database/migrations/0044_create_schema_migrations.sql`, `web/tests/ai.spec.ts`, `docs/source_of_truth/*`, `docker-compose.yml` |
| 14:00 | SoT documentation update | docs | `docs/sot` | `docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md` |
| 13:30 | AI4 null account_code handling | fix | `ai4/parser` | `backend/src/services/ai_service.py`, `backend/src/services/ai/parsers/accounting.py` |
| 13:00 | AI4 item_id optional fix | fix | `ai4/parser` | `backend/src/services/ai_service.py`, `backend/src/services/ai/parsers/accounting.py` |
| 12:30 | AI4 chart_of_accounts fix | fix | `ai4` | `backend/src/services/ai_service.py` |
| 11:00 | Chart of accounts repair | data | `database` | `chart_of_accounts` table (1318 rows) |
| 10:00 | Backup script fixes | ops | `scripts` | `create_codebase_archive_db.ps1` |

#### [21:20] Fix: Stop migration replay + prompt overwrite
- **Change type:** fix
- **Scope (component/module):** `db/migrations`
- **Tickets/PRs:** `MISC_REPAIR_PLAN_2025-12-14`
- **Branch:** `fix/misc-repair-plan-2025-12-14`
- **Commit range:** `WORKING_TREE` (uncommitted)
- **Environment:** Docker Compose (main) + MySQL 8 + nginx (8008)
- **Commands run:**
  ```bash
  pytest -q backend/tests/unit/test_migrations_apply_once.py
  npm run test:e2e:report -- web/tests/ai.spec.ts -g "@migrations"
  ```
- **Result summary:** Implemented a migration ledger (`schema_migrations`) with baseline support to stop replay; added guards so legacy migrations cannot overwrite UI-edited prompts; added regression tests (pytest + Playwright) and saved Playwright HTML report with video/screenshot artifacts.
- **Files changed (exact):**
  - `backend/src/services/db/migrations.py` - migration ledger, baseline marker, prompt-safe execution, destructive migration opt-in guard
  - `database/migrations/0044_create_schema_migrations.sql` - creates `schema_migrations`
  - `backend/src/api/app.py` - `/system/apply-migrations` returns `mode`, `baseline_marked`, `available`, etc.
  - `backend/src/api/ai_config.py` - `GET /ai-config/prompts` is read-only (no implicit DB updates)
  - `backend/tests/unit/test_migrations_apply_once.py` - migration runner idempotency + baseline + prompt safety tests
  - `web/tests/ai.spec.ts` - `@migrations` Playwright regression: prompt persistence + idempotent apply-migrations
  - `docs/source_of_truth/40_DATA_MODEL.md`, `50_PIPELINES_AND_JOBS.md`, `55_API_AND_ENDPOINTS.md`, `70_AI_PROMPTS_AND_ROLES.md`, `80_OPERATIONS_RUNBOOK.md`
  - `docker-compose.yml`, `backend/src/database/.gitkeep` - mount `./database` into `ai-api` container as `/app/database` (read-only) for migrations access
- **Tests executed:** `pytest` (pass) + Playwright `@migrations` (pass)
- **Artifacts:** `web/test-reports/2025-12-14_211123/html/index.html`
- **Next action:** Update the active AI3 `data_extraction` prompt via UI to include the credit-card fields (`credit_card_*`) and re-run AI3 on affected receipts (existing rows currently have NULL card metadata).

#### [14:00] Docs: SoT documentation update
- **Change type:** docs
- **Scope:** `docs/source_of_truth`
- **Result summary:** Updated 70_AI_PROMPTS_AND_ROLES.md with AI4 changes: added chart_of_accounts to Input Contract, rewrote Proposal Schema to show item_id as optional, updated version to 2025-12-14.
- **Files changed:**
  - `docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md` - Section 5.3, 5.5, version header

#### [13:30] Fix: AI4 null account_code handling
- **Change type:** fix
- **Scope:** `ai4/parser`
- **Result summary:** LLM sometimes returns `account_code: null` for settlement lines when payment info is missing. Changed `_extract_account_code()` to return `Optional[str]` and filter out proposals with null account_code (with logging) instead of crashing.
- **Files changed:**
  - `backend/src/services/ai_service.py` - `_extract_account_code()`, `_build_accounting_proposal()`, `parse_accounting_proposals()`
  - `backend/src/services/ai/parsers/accounting.py` - same functions (duplicate code)

#### [13:00] Fix: AI4 item_id optional
- **Change type:** fix
- **Scope:** `ai4/parser`
- **Result summary:** Settlement/balancing lines (e.g., 2440 Leverantörsskulder) correctly have null item_id as they don't correspond to specific receipt line items. Made item_id optional in parser validation.
- **Files changed:**
  - `backend/src/services/ai_service.py` - `_build_accounting_proposal()` now accepts null item_id
  - `backend/src/services/ai/parsers/accounting.py` - same change

#### [12:30] Fix: AI4 chart_of_accounts not sent to LLM
- **Change type:** fix
- **Scope:** `ai4`
- **Root cause:** `chart_of_accounts` parameter was passed to `run_ai4_accounting_classification()` but NEVER included in the payload sent to LLM. The LLM had no valid accounts to choose from.
- **Result summary:** Added `_format_chart_of_accounts()` helper and included formatted accounts in LLM payload.
- **Files changed:**
  - `backend/src/services/ai_service.py` - Added `_format_chart_of_accounts()`, modified `run_ai4_accounting_classification()` to include chart in payload

#### [11:00] Data: Chart of accounts repair
- **Change type:** data
- **Scope:** `database`
- **Result summary:** Imported BAS 2025 chart of accounts from `docs/Kontoplan-BAS-2025.csv` with proper UTF-8 encoding. 1318 rows imported successfully. Swedish characters (ö, ä, å) verified working.
- **Method:** Python script with mysql-connector, TRUNCATE + INSERT

#### [10:00] Ops: Backup script fixes
- **Change type:** ops
- **Scope:** `scripts`
- **Result summary:** Changed dump filename format to `mind_db_dump_YYYY-MM-DD.sql`. Added abort logic if MySQL container not running, if dump fails, or if dump not found in final zip.
- **Files changed:**
  - `create_codebase_archive_db.ps1` - timestamp format, abort conditions, zip verification

---

## 5) Changes by File (Exact Edits)

- `create_codebase_archive_db.ps1` - dump naming, abort conditions, zip verification
- `backend/src/services/ai_service.py` - `_format_chart_of_accounts()`, chart inclusion in payload, optional item_id, optional account_code
- `backend/src/services/ai/parsers/accounting.py` - optional item_id, optional account_code with filtering
- `docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md` - AI4 Input Contract, Proposal Schema, version

---

## 6) Database & Migration Notes

- **Schema changes:** None
- **Data changes:** `chart_of_accounts` table repopulated with 1318 BAS 2025 rows
- **Verified:** AI4 now generates proposals with valid account codes (6110, 2641, 2440)

---

## 7) API / Integration Notes

- N/A (no API changes)

---

## 8) Tests & Evidence

- Manual test: AI4 successful with 3 proposals
- Account codes verified against BAS 2025: 6110 (Kontorsmaterial), 2641 (Ingående moms), 2440 (Leverantörsskulder)

---

## 9) Performance & Benchmarks

- N/A

---

## 10) Security, Privacy, Compliance

- N/A

---

## 11) Issues, Bugs, Incidents

- **Root cause identified:** AI4 failures were caused by `chart_of_accounts` parameter being ignored - never sent to LLM despite being passed as function parameter.

---

## 12) Communication & Reviews

- N/A

---

## 13) Stats & Traceability

- **Bug → Fix:** AI4 "account_code is missing" → chart_of_accounts now sent to LLM
- **Bug → Fix:** AI4 "item_id is missing" → item_id now optional for settlement lines
- **SoT updated:** `docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md`

---

## 14) Config & Ops

- Backup script now requires DB dump in zip (aborts otherwise)
- Container restart required for backend changes

---

## 15) Decisions & Rationale

- Made item_id optional because settlement lines (2440, etc.) don't correspond to specific receipt items
- Filter null account_code proposals with logging rather than crash - allows partial success

---

## 16) TODO / Next Steps

- Monitor AI4 success rate after deployment
- Consider adding more validation for account codes against chart_of_accounts

---

## 17) Time Log

- 10:00-14:30: AI4 investigation and fixes

---

## 18) Attachments & Artifacts

- N/A

---
