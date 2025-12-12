
---

## 0) Hard scope and guardrails (mandatory)

### Scope (ONLY these items)

1. **Image uploads (JPG/PNG):** ensure exactly one image is available in `/data/storage/<file_id>/` so OCR can run.
2. **PDF uploads:** ensure the **parent PDF** gets a preview image in `/data/storage/<parent_file_id>/` (first page) while WF2 still creates per-page files and merges OCR into the parent.
3. **Receipts list “Upload” column:** compute upload stage from the **source stage** (src_*) regardless of later stages (do not rely on “latest stage”).
4. **Receipt modal (preview DTO):** do not 500/abort when `company_id` is missing; modal must load (company can be empty).
5. **Verification + SoT compliance:** statuses and workflow behavior must remain within `docs/source_of_truth/30_STATUS_MODEL.md` and workflow structure within `docs/source_of_truth/50_PIPELINES_AND_JOBS.md`.

### Non-goals (explicitly forbidden)

* No UI redesign.
* No workflow redesign.
* No new tables/migrations unless absolutely required (it shouldn’t be).
* No renaming of stage keys, status values, or existing columns.
* No changes to unrelated import paths (FirstCard etc.).
* No “auto-create company” redesign here (only unblock preview; do not invent matching logic).

### Read SoT first (mandatory)

* `docs/source_of_truth/30_STATUS_MODEL.md` (allowed `ai_status`, transitions).
* `docs/source_of_truth/50_PIPELINES_AND_JOBS.md` (WF1_RECEIPT, WF2_PDF_SPLIT responsibilities).
* `docs/analyses/workflow_analyze_codex_20251212.md` (expected runtime behavior + observed failures).
* `docs/analyses/workflow_pdf_conversion_issues_2025-12-10.md` (PDF conversion expectations).

---

## 1) Fix JPG/PNG: make OCR see exactly 1 image for the file

### Problem to solve

Upload currently saves only to `/data/storage/originals/<file_id>.<ext>`. OCR enumerates images from `/data/storage/<file_id>/`, so it finds **0 images**, causing OCR/AI chain to stall.

### Implementation location

* `backend/src/api/ingest.py` (upload endpoint)
* Uses `FileStorage` from `backend/src/services/storage.py`

### Required change (minimal)

When the uploaded document is a **single-page image** (JPG/JPEG/PNG/TIF/TIFF):

1. Keep the existing `fs.save_original(file_id, safe_filename, data)` call unchanged.
2. Add one additional storage write into the receipt folder:

   * Save the same bytes to `/data/storage/<file_id>/page-0001.<ext>`
   * Use FileStorage `fs.save(file_id, "page-0001.<ext>", data)`

### Constraints

* Do not convert formats.
* Do not modify how `unified_files` rows are created.
* Do not alter workflow dispatching.
* The filename must be deterministic and safe. Use `page-0001` naming (consistent with WF2 pages).

### Acceptance checks

* After uploading a PNG/JPG: `/ai/api/receipts/<rid>/image?size=preview` returns 200 (not 404).
* OCR logs show “Processing 1 images” (not “Images: 0”).
* `unified_files.ai_status` progresses within SoT allowed states.

---

## 2) Fix PDF parent preview: parent must have an image in `/data/storage/<parent_id>/`

### Problem to solve

WF2 creates per-page images under each **page file_id** directory, but the **parent PDF file_id** has no image in `/data/storage/<parent_id>/`. The image endpoint `/receipts/<rid>/image` searches only `/data/storage/<rid>/`.

### Implementation location

* `backend/src/services/tasks/ocr_tasks.py`

  * `wf2_prepare_pdf_pages()` is the right place (it already has access to page paths and file_ids).

### Required change (minimal)

Inside `wf2_prepare_pdf_pages()` after the first page has been created/adopted:

1. Determine the stored path to the first page’s image **as stored under the page file_id**.
2. Copy bytes (copy, not move) into the **parent’s** storage dir:

   * Save `/data/storage/<parent_file_id>/page-0001.png`
   * Only create it if the parent folder has no existing image file (idempotent).

### Must handle both cases

* **Normal conversion:** first page has a fresh `target_file_id` and `fs.adopt(target_file_id, "page-0001.png", page.path)` runs.
* **Duplicate reuse:** first page `target_file_id` is reused; the source image already exists under `/data/storage/<target_file_id>/page-0001.png`. Copy from there.

### Constraints

* Do not change how WF2 stores per-page images.
* Do not change `other_data.pages` structure.
* Do not change OCR merge behavior.
* Do not add “preview generation” logic elsewhere (the project explicitly removed it; we’re only placing the real image where the existing endpoint expects it).

### Acceptance checks

* Upload a multi-page PDF:

  * `/ai/api/receipts/<parent_id>/image?size=preview` returns 200
  * The receipts list shows the parent row (pdf_page rows remain hidden per current logic).
  * Modal preview opens and image loads.

---

## 3) Fix “Upload” column in receipts list: compute from src_* stage, not latest stage

### Problem to solve

`/receipts` currently sets `upload_stage` only if the **latest** workflow stage key starts with `src_`. That’s incorrect because later stages (OCR/AI/finalize) replace it, so Upload appears empty.

### Implementation location

* `backend/src/api/receipts.py` `/receipts` endpoint (list query + response mapping)

### Required change (minimal, deterministic)

Modify the list SQL query to fetch:

* `upload_stage_key`: earliest `workflow_stage_runs.stage_key` where `stage_key LIKE 'src_%'` (ORDER BY started_at ASC LIMIT 1)
* `upload_stage_status`: corresponding `workflow_stage_runs.status` for that same earliest src stage

Then set:

* `upload_stage = {"stage_key": upload_stage_key, "status": upload_stage_status}` when present.

### Constraints

* Do not change existing stage keys or status vocabulary.
* Do not infer/mint a stage from `source_channel` if stage runs are missing. If missing, keep null (don’t guess).
* Keep existing filtering behavior; only fix the computed field shown to UI.

### Acceptance checks

* For a newly uploaded image/PDF:

  * Upload column shows `src_portal` (or `src_ftp` for FTP path) consistently even after OCR/AI completes.
* No changes in sort/pagination behavior.

---

## 4) Fix receipt modal endpoint: never 500 just because `company_id` is null

### Problem to solve

`GET /receipts/<rid>/modal` currently returns HTTP 500 when `company_id` is missing, which blocks preview entirely.

### Implementation location

* `backend/src/api/receipts.py` `get_receipt_modal()`

### Required change (minimal)

Replace the “hard fail” behavior:

* If `company_id` is null/0:

  * Do **not** return 500.
  * Return 200 with `company: {}` (or omit company field) and keep the rest of the payload intact.
  * Log a warning instead of error (this is a valid intermediate state while AI pipeline is incomplete).

### Constraints

* Do not auto-create or auto-match companies here.
* Do not change how companies are fetched when `company_id` is present.
* Do not change frontend; the frontend already safely spreads `payload?.company || {}`.

### Acceptance checks

* Open modal for a file missing company_id:

  * Modal loads (HTTP 200)
  * Image loads if step (1)/(2) is fixed
  * UI shows empty company fields (expected)

---

## 5) Verification steps (must be executed and documented)

### A) Automated sanity

* Run backend tests (existing suite).
* Run lint/format only if repo requires it; do not reformat unrelated files.

### B) Manual test matrix (minimum)

1. Upload **PNG**
2. Upload **JPG**
3. Upload **multi-page PDF** (≥ 2 pages)
4. Upload **single-page PDF** (still must split and then parent preview should show first page)

For each:

* Confirm `/ai/api/receipts/<rid>/image?size=preview` returns 200.
* Confirm `/ai/api/receipts/<rid>/modal` returns 200.
* Confirm `/ai/api/receipts` shows non-empty Upload column.
* Confirm `ai_status` transitions remain within SoT allowed values.

### C) DB checks (read-only)

For the uploaded file IDs:

* Verify `unified_files.ocr_raw` is populated after OCR stages.
* Verify `unified_files.ai_status` is one of the SoT states.
* Verify workflow stages include a `src_*` stage run row.

### D) Storage checks (container)

For each uploaded file_id:

* Image uploads: `/data/storage/<file_id>/page-0001.<ext>` exists.
* PDF uploads:

  * `/data/storage/<parent_id>/page-0001.png` exists
  * `/data/storage/<page_id>/page-0001.png` exists for each page

### E) Document results

Update the analysis log entry (or add a new short one) referencing:

* Which test files were used (names only)
* Observed statuses and endpoints
* Confirmation that behavior matches SoT requirements

---

## 6) Delivery checklist (what the agent must produce)

1. A PR/commit that changes **only** these files (unless tests require more):

   * `backend/src/api/ingest.py`
   * `backend/src/services/tasks/ocr_tasks.py`
   * `backend/src/api/receipts.py`
   * (Optional) minimal test additions if the repo already has a matching pattern.
2. Short verification notes added to:

   * `docs/analyses/workflow_analyze_codex_20251212.md` (append-only) **or** a new analysis note under `docs/analyses/` with today’s date.
3. A “SoT compliance” statement in the PR description:

   * Which SoT files were followed
   * Confirmation that no new statuses/stages were introduced

---
