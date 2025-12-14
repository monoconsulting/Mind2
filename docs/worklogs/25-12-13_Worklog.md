# 25-12-13_Worklog.md - Daily Engineering Worklog

> **Usage:** Save this file as `YY-MM-DD_Worklog.md` (e.g., `25-08-19_Worklog.md`). This template is **rolling/blog-style**: add small entries **as you work**, placing the **newest entry at the top** of the Rolling Log. **Also read and follow `AI_INSTRUCTION_Worklog.md` included in this package.** Fill every placeholder. Keep exact identifiers (commit SHAs, line ranges, file paths, command outputs). Never delete sections-if not applicable, write `N/A`.

---

## 0) TL;DR (3-5 lines)

- **What changed:** Gjorde FirstCard-PDF→bilder mer robust (konfigurerbar DPI + fallback), fixade FC-importkrasch (`create_unified_file(..., source=...)`), exponerade `pages[].url` i FirstCard invoice-endpoints och lade till en enkel bild-förhandsgranskning i Kortmatchning. Förbättrade OCR “quality-first” med deterministiska fallback-pass (resize/zoom/tiling). Uppdaterade SoT + `.env.example`.
- **Why:** Återställa stabil FC-import + ge UI ett säkert preview-flöde, samt förbättra OCR på täta kvitton där text blir läsbar först efter zoom.
- **Risk level:** Medium (berör OCR + FC-import, men med deterministiska fallback-ladders och bakåtkompatibla API-fält).
- **Deploy status:** Lokalt verifierat med Playwright + DB-check; kräver rebuild/recreate av celery-workers om de kör built image.

---

## 1) Metadata

- **Date (local):** 2025-12-13 (Europe/Stockholm)
- **Author:** Codex CLI agent (GPT-5.2)
- **Project/Repo:** Mind2
- **Branch:** `dev`
- **Commit range:** `899c00e..WORKING_TREE` (uncommitted changes)
- **Related tickets/PRs:** `MIND_FC_WORKFLOW_REMAKE_2025-12-13`
- **Template version:** 1.1

---

## 2) Goals for the Day

- Implementera OCR quality-first förbättringar (zoom/tiling) för täta kvitton.
- Göra PDF→PNG-konvertering robust för receipts + FirstCard (konfigurerbar DPI + fallback).
- Fixa FirstCard workflow-fel: `create_unified_file()` saknar `source`.
- Exponera `pages[].url` och bygga minimal FC preview-modal i UI.
- Säkerställa SoT-dokumentation är uppdaterad.

**Definition of done today:** Playwright `web/tests/fc-preview-and-log-grouping.spec.ts` passerar och DB visar att nytt utdrag skapat `invoice_documents` + `invoice_lines` + `unified_files.other_data.pages`.

---

## 3) Environment & Reproducibility

- **OS / Kernel:** Windows (host)
- **Runtime versions:** Node/NPM per repo; Docker Compose (MySQL/Redis/ai-api/celery-workers/frontend)
- **Containers:** `mind2` compose stack (main)
- **Data seeds/fixtures:** N/A (använde testfixture `fc/FC_2503.pdf`)
- **Feature flags:** N/A
- **Env vars touched:** `.env.example` (nya OCR/PDF-nycklar; inga hemligheter)

**Exact repro steps:**

1. `mind_docker_compose_up.bat` (om stacken inte redan kör)
2. Kör testet: `npm run test:e2e:report -- web/tests/fc-preview-and-log-grouping.spec.ts`
3. Verifiera artifacts i `web/test-reports/20251213_062738-fc-preview-and-log-grouping/html/index.html`

---

## 4) Rolling Log (Newest First)

> Add each work item as a compact **entry** while you work. **Insert new entries at the top** of this section. Each entry must include the central parameters below and explicitly list any **system documentation files** updated.

### Daily Index (auto-maintained by you)

| Time | Title | Change Type | Scope | Tickets | Commits | Files Touched |
|---|---|---|---|---|---|---|
| [06:52](#0652) | Fix .env radbrytning | ops | `config/env` | MIND_FC_WORKFLOW_REMAKE_2025-12-13 | `899c00e..WORKING_TREE` | `.env, docs/worklogs/25-12-13_Worklog.md` |
| [06:30](#0630) | FC workflow remake + OCR quality boosts | feat,fix,docs,test,ops | `ocr, fc-import, fc-preview` | MIND_FC_WORKFLOW_REMAKE_2025-12-13 | `899c00e..WORKING_TREE` | `backend/src/services/ocr.py, backend/src/services/tasks/creditcard_tasks.py, backend/src/services/tasks/ocr_tasks.py, backend/src/api/reconciliation_firstcard/routes/status.py, backend/src/api/receipts.py, main-system/app-frontend/src/ui/components/DocumentPreviewModal.jsx, main-system/app-frontend/src/ui/pages/CompanyCard.jsx, docs/source_of_truth/55_API_AND_ENDPOINTS.md, .env.example` |

#### [06:52] Ops: Fix .env radbrytning
- **Change type:** ops
- **Scope (component/module):** `config/env parsing`
- **Tickets/PRs:** `MIND_FC_WORKFLOW_REMAKE_2025-12-13`
- **Branch:** `dev`
- **Commit(s):** `899c00e..WORKING_TREE` (uncommitted)
- **Environment:** N/A
- **Commands run:** N/A
- **Result summary:** Fixade trasig radbrytning i `.env` så `DB_AUTO_MIGRATE` och `QUEUE_STALL_THRESHOLD_SECONDS` blir två separata env-nycklar.
- **Files changed (exact):**
  - `.env` - L130-L131 - keys: `DB_AUTO_MIGRATE`, `QUEUE_STALL_THRESHOLD_SECONDS`
- **Tests executed:** N/A
- **System documentation updated:**
  - `docs/worklogs/25-12-13_Worklog.md` - lade till loggpost + indexrad
- **Artifacts:** N/A
- **Next action:** N/A

#### [06:30] FC workflow remake + OCR quality boosts
- **Change type:** feat, fix, docs, test, ops
- **Scope (component/module):** `ocr`, `creditcard/firstcard import`, `company-card UI preview`, `api/sot`
- **Tickets/PRs:** `MIND_FC_WORKFLOW_REMAKE_2025-12-13`
- **Branch:** `dev`
- **Commit(s):** `899c00e..WORKING_TREE` (uncommitted)
- **Environment:** Docker Compose (ai-api + celery workers + mind-web-main-frontend-dev + mysql)
- **Commands run:**
  ```bash
  npm run test:e2e:report -- web/tests/fc-preview-and-log-grouping.spec.ts
  docker compose restart mind-web-main-frontend-dev
  # Copy report for evidence (per docs/TEST_RULES.md)
  # -> web/test-reports/20251213_062738-fc-preview-and-log-grouping/html/index.html
  docker compose exec -T mysql mysql -uroot -proot mono_se_db_9 -e "SELECT id, invoice_type, uploaded_at, status, processing_status FROM invoice_documents ORDER BY uploaded_at DESC LIMIT 1;"
  ```
- **Result summary:** FC-import klarar PDF→bilder via DPI-fallback och kraschar inte på `source`-arg. API exponerar sid-URLs och UI kan öppna/stänga preview modal. Playwright-test passerar och DB visar nya `invoice_lines` + `pages_count`.
- **Files changed (exact):**
  - `.env.example` - L28-L57 - env keys: `OCR_INPUT_LONG_SIDE`, `OCR_ZOOM_*`, `OCR_TILE_*`, `OCR_PDF_DPI`
  - `backend/src/services/ocr.py` - L24-L230, L665 - functions: `_env_bool`, `_env_int`, `_env_float`, `_prepare_image_for_ocr`, `run_ocr`
  - `backend/src/services/tasks/ocr_tasks.py` - L222-L265 - PDF render DPI fallback (`OCR_PDF_DPI`) för WF2 receipts
  - `backend/src/services/tasks/creditcard_tasks.py` - L154-L220 - PDF render DPI fallback + `create_unified_file(..., source=...)` fix
  - `backend/src/api/reconciliation_firstcard/routes/status.py` - L40-L205, L261-L470 - functions: `_build_receipt_image_url`, `_page_refs_from_parent`, endpoints `.../invoices/<id>` + `.../status` inkluderar `pages[].url`
  - `backend/src/api/receipts.py` - L903-L920 - default `include_credit=1` när param saknas
  - `main-system/app-frontend/src/ui/components/DocumentPreviewModal.jsx` - L1-L180 - FC preview modal (image-only) + close button “Stäng”
  - `main-system/app-frontend/src/ui/pages/CompanyCard.jsx` - L1908-L2220 - “Förhandsgranska” knapp + modal state
  - `docs/source_of_truth/55_API_AND_ENDPOINTS.md` - L242, L372-L460 - dokumenterar FirstCard invoice endpoints + `pages[].url` + `include_credit` default
- **Unified diff (minimal, consolidated):**
  ```diff
  --- a/backend/src/services/tasks/creditcard_tasks.py
  +++ b/backend/src/services/tasks/creditcard_tasks.py
  @@
  -create_unified_file(... )
  +create_unified_file(..., source=other_data.get("source"))
  --- a/backend/src/api/reconciliation_firstcard/routes/status.py
  +++ b/backend/src/api/reconciliation_firstcard/routes/status.py
  @@
  +def _build_receipt_image_url(file_id: str) -> str:
  +    return f"/ai/api/receipts/{file_id}/image?size=original&quality=high"
  @@
  +metadata["pages"] = page_records
  --- a/backend/src/api/receipts.py
  +++ b/backend/src/api/receipts.py
  @@
  +include_credit = True if include_credit_raw is None else ...
  ```
- **Tests executed:** `web/tests/fc-preview-and-log-grouping.spec.ts` (try #1 fail p.g.a. frontend-dev stale bundle; try #2 fail; try #3 pass efter `docker compose restart mind-web-main-frontend-dev`)
- **Database verification:**
  - `invoice_documents` skapad: `adf5909e-e66a-4c2c-85ac-5813c409c8da` (credit_card_invoice)
  - `invoice_lines`: `43` rader för invoice_id ovan
  - `unified_files.other_data.pages`: `pages_count=3` för invoice_id ovan
- **System documentation updated:**
  - `docs/source_of_truth/55_API_AND_ENDPOINTS.md` - lade till FirstCard invoice endpoints + previewfält, och klargjorde default för `include_credit`
- **Artifacts:** `web/test-reports/20251213_062738-fc-preview-and-log-grouping/html/index.html` (inkl. video `.webm` och screenshot `.png` i `html/data/`)
- **Next action:** Om detta ska deployas: rebuild `ai-api` image och recreate `celery-worker*` så workers plockar upp backend task-ändringar (compose workers kör built image).

---

## 5) Changes by File (Exact Edits)

- `.env.example` - nya OCR/PDF parametrar (quality-first defaults)
- `backend/src/services/ocr.py` - deterministiska fallback-pass (resize/zoom/tiling) och robust env-parsning
- `backend/src/services/tasks/ocr_tasks.py` - `OCR_PDF_DPI` + fallback-ladder för PDF→PNG
- `backend/src/services/tasks/creditcard_tasks.py` - `OCR_PDF_DPI` + fallback-ladder; fix för `create_unified_file(..., source=...)`; bättre hantering av de-dup pages
- `backend/src/api/reconciliation_firstcard/routes/status.py` - `pages[].url` på invoice detail + status; fallback till `other_data.pages` vid content-hash de-dup
- `backend/src/api/receipts.py` - default `include_credit=1` (om param saknas)
- `main-system/app-frontend/src/ui/components/DocumentPreviewModal.jsx` - image-only preview modal för FirstCard invoices
- `main-system/app-frontend/src/ui/pages/CompanyCard.jsx` - “Förhandsgranska” knapp som öppnar preview modal
- `docs/source_of_truth/55_API_AND_ENDPOINTS.md` - SoT uppdaterad för nya fält och semantics

---

## 6) Database & Migration Notes

- **Schema changes:** N/A
- **Verified writes (local):**
  - `invoice_documents`: ny rad (invoice_id ovan) vid upload
  - `invoice_lines`: 43 rader kopplade till invoice_id ovan
  - `unified_files.other_data.pages`: `pages_count=3` och child-page `unified_files` existerar (via JSON_TABLE)

---

## 7) API / Integration Notes

- `GET /ai/api/reconciliation/firstcard/invoices/{invoice_id}` returnerar `invoice.pages[]` med `url` (receipt-image endpoint) för frontend preview.
- `GET /ai/api/reconciliation/firstcard/invoices/{invoice_id}/status` returnerar `ocr_progress.pages[]` med `url`.
- `GET /ai/api/receipts` inkluderar nu creditcard invoices om `include_credit` inte anges (Process-vyn skickar explicit `include_credit=0`).

---

## 8) Tests & Evidence

- **Test available:** `web/tests/fc-preview-and-log-grouping.spec.ts`
- **Failing run evidence:** `web/test-results/_artifacts/fc-preview-and-log-groupin-ba881-modal-and-log-date-grouping-chromium-ultrawide/`
- **Passing report (required location):** `web/test-reports/20251213_062738-fc-preview-and-log-grouping/html/index.html`

---

## 9) Performance & Benchmarks

- N/A

---

## 10) Security, Privacy, Compliance

- N/A (inga nya secrets loggades; `.env.example` innehåller endast exempelvärden)

---

## 11) Issues, Bugs, Incidents

- N/A

---

## 12) Communication & Reviews

- N/A

---

## 13) Stats & Traceability

- **Ticket → Test:** `MIND_FC_WORKFLOW_REMAKE_2025-12-13` → `web/tests/fc-preview-and-log-grouping.spec.ts`
- **Ticket → Artifacts:** `MIND_FC_WORKFLOW_REMAKE_2025-12-13` → `web/test-reports/20251213_062738-fc-preview-and-log-grouping/html/index.html`
- **Ticket → SoT:** `MIND_FC_WORKFLOW_REMAKE_2025-12-13` → `docs/source_of_truth/55_API_AND_ENDPOINTS.md`

---

## 14) Config & Ops

- `.env.example`:
  - Nya OCR-quality nycklar (resize/zoom/tiling)
  - `OCR_PDF_DPI` för PDF→PNG render DPI
- **Ops note:** `celery-worker*` kör built image, så backend task-förändringar kräver rebuild + recreate för att slå igenom.

---

## 15) Decisions & Rationale (ADR-style snippets)

- Valde deterministiska fallback-ladders (DPI samt OCR-pass) för att maximera reproducerbarhet och minimera “random flakiness”.
- Exponerade `pages[].url` server-side för att undvika frontend-gissning och möjliggöra stabil preview.

---

## 16) TODO / Next Steps

- (Om önskat) Lägg till separat SoT-sida för OCR env keys (om sådan SoT-konvention finns).
- (Om önskat) Commit/pusha ändringarna i en PR med länk till `web/test-reports/.../index.html`.

---

## 17) Time Log

- 06:30–06:31: Worklog + artifacts + DB-verifiering

---

## 18) Attachments & Artifacts

- `web/test-reports/20251213_062738-fc-preview-and-log-grouping/html/index.html`

---

## 19) Appendix A - Raw Console Log (Optional)

- N/A

---

## 20) Appendix B - Full Patches (Optional)

- N/A (se `git diff`)
