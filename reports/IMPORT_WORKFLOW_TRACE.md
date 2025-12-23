# IMPORT_WORKFLOW_TRACE
Date: 2025-12-21

## Upload import trace (portal upload → WF2 → WF1)
**Test input**: `testfiles_for_import/pdf_test.pdf` uploaded via `POST /ingest/upload`.

### Evidence-backed flow (code)
1) Upload endpoint reads files, detects type, writes unified_files, and dispatches workflow.
   - Upload handler: `backend/src/api/ingest.py:56-216` (`upload_files`).
   - File type detection: `backend/src/services/file_detection.py:67-92` (`detect_file`).
   - Unified file creation + workflow_run creation: `backend/src/services/db/files.py:194-301` (`create_unified_file`) → `backend/src/services/workflow_runs.py:57-100` (`create_workflow_run`).
   - File storage (original): `backend/src/services/storage.py:66-79` (`save_in_category`, `save_original`).
   - Stage logging: `backend/src/services/tasks/workflow_base.py:247-296` (`begin_import_stage`, `complete_import_stage`).
   - Workflow dispatch: `backend/src/services/tasks/workflow_tasks.py:78-160` (`dispatch_workflow`).

2) For PDFs, WF2 splits into pages, OCRs pages, merges OCR, then creates a WF1 run for receipt processing.
   - WF2 page conversion + page file creation: `backend/src/services/tasks/ocr_tasks.py:131-421` (`wf2_prepare_pdf_pages`).
   - WF2 per-page OCR: `backend/src/services/tasks/ocr_tasks.py:425-500` (`wf2_run_page_ocr`).
   - WF2 merge + forward to WF1: `backend/src/services/tasks/ocr_tasks.py:504-632` (`wf2_merge_ocr_results`).

3) WF1 runs OCR on the parent file, then AI1–AI4 and persistence.
   - WF1 OCR: `backend/src/services/tasks/ocr_tasks.py:51-127` (`wf1_run_ocr`).
   - AI pipeline: `backend/src/services/tasks/ai_pipeline_tasks.py:59-575` (`_run_ai_pipeline`).
   - AI stage executors + persistence: `backend/src/api/ai_processing.py:379-867` (`_persist_extraction_result`, `_persist_accounting_proposals`, `classify_*_internal`).

### Sequence diagram (text)
`Client` → `POST /ingest/upload` (`backend/src/api/ingest.py:56-216`, `upload_files`)
→ `detect_file` (`backend/src/services/file_detection.py:67-92`)
→ `create_unified_file` (`backend/src/services/db/files.py:194-301`)
→ `create_workflow_run` (`backend/src/services/workflow_runs.py:57-100`)
→ `dispatch_workflow` (`backend/src/services/tasks/workflow_tasks.py:78-160`)
→ `wf2_prepare_pdf_pages` (`backend/src/services/tasks/ocr_tasks.py:131-421`)
→ `wf2_run_page_ocr` (`backend/src/services/tasks/ocr_tasks.py:425-500`)
→ `wf2_merge_ocr_results` (creates WF1 run) (`backend/src/services/tasks/ocr_tasks.py:504-632`)
→ `wf1_run_ocr` (`backend/src/services/tasks/ocr_tasks.py:51-127`)
→ `_run_ai_pipeline` (`backend/src/services/tasks/ai_pipeline_tasks.py:59-575`)
→ `extract_data_internal` (`backend/src/api/ai_processing.py:851-859`) + `_persist_extraction_result` (`backend/src/api/ai_processing.py:379-600`)
→ `classify_accounting_internal` (`backend/src/api/ai_processing.py:862-867`) + `_persist_accounting_proposals` (`backend/src/api/ai_processing.py:603-644`).

### Evidence (DB results)
**Unified file created** (by content_hash for `pdf_test.pdf`):
```
SELECT id, workflow_type, content_hash, original_filename, submitted_by, ai_status, created_at
FROM unified_files
WHERE content_hash='2b9932b24105a79f12105686f02568f9eb28d32fabc5a630f754044f13935cd2'
LIMIT 1;

id                                   workflow_type  content_hash                                                     original_filename  submitted_by   ai_status   created_at
27ab6bab-d6a1-41a4-b423-b39c5e515717  receipt        2b9932b24105a79f12105686f02568f9eb28d32fabc5a630f754044f13935cd2  pdf_test.pdf       agent_upload  processing  2025-12-21 17:41:52
```

**Workflow runs created for upload** (WF2 → WF1):
```
SELECT id, workflow_key, status, current_stage, created_at, updated_at
FROM workflow_runs
WHERE file_id='27ab6bab-d6a1-41a4-b423-b39c5e515717'
ORDER BY created_at DESC;

id  workflow_key   status     current_stage  created_at           updated_at
41  WF1_RECEIPT    succeeded  finalize       2025-12-21 17:42:09  2025-12-21 17:43:01
40  WF2_PDF_SPLIT  succeeded  finalize       2025-12-21 17:41:52  2025-12-21 17:42:09
```

**Workflow stages (WF1 run 41)**:
```
SELECT stage_key, status, started_at, finished_at, message
FROM workflow_stage_runs
WHERE workflow_run_id=41
ORDER BY id;

... (AI1/AI2/AI3/AI4 stages succeeded; see run output in terminal logs)
```

**AI3 persistence evidence** (unified_files fields populated):
```
SELECT id, company_id, purchase_datetime, payment_type, expense_type, currency,
       gross_amount_original, net_amount_original, gross_amount_sek, net_amount_sek,
       total_vat_25, total_vat_12, total_vat_6, receipt_number, ai_status
FROM unified_files
WHERE id='27ab6bab-d6a1-41a4-b423-b39c5e515717';

id                                   company_id  purchase_datetime     payment_type  expense_type  currency  gross_amount_original  net_amount_original  gross_amount_sek  net_amount_sek  total_vat_25  total_vat_12  total_vat_6  receipt_number  ai_status
27ab6bab-d6a1-41a4-b423-b39c5e515717  1           2025-07-02 07:13:00  card          corporate     SEK       365.22                292.18             365.22           292.18         73.04         NULL          NULL         NULL            completed
```

**AI4 proposals stored** (note: entries are not balanced; see AI4 validation task):
```
SELECT id, receipt_id, account_code, debit, credit, vat_rate, notes
FROM ai_accounting_proposals
WHERE receipt_id='27ab6bab-d6a1-41a4-b423-b39c5e515717';

id  receipt_id                            account_code  debit   credit  vat_rate  notes
1   27ab6bab-d6a1-41a4-b423-b39c5e515717  4400         292.18  0.00    25.00     Hornbach Byggmarknad AB: momspliktigt inköp i Sverige (netto enligt kvittot).
2   27ab6bab-d6a1-41a4-b423-b39c5e515717  2641          73.04  0.00    25.00     Ingående moms enligt kvittot.
```

## FTP import trace (local inbox → WF1 for images / WF2 for PDFs)
**Test input**: `debug_overlay_sample.jpg` copied into `inbox/` and ingested via `fetch_from_local_inbox()`.

### Evidence-backed flow (code)
1) FTP trigger endpoint (production) calls `fetch_from_ftp()`.
   - Endpoint: `backend/src/api/fetcher.py:15-37` (`trigger_fetch_ftp`).
   - Fetch implementation: `backend/src/services/fetch_ftp.py:424-535` (`fetch_from_ftp`).

2) Local inbox fallback uses `_insert_unified_file` to create `unified_files` + workflow_run and then dispatch.
   - Local inbox fetch: `backend/src/services/fetch_ftp.py:314-421` (`fetch_from_local_inbox`).
   - Insert file row: `backend/src/services/fetch_ftp.py:113-219` (`_insert_unified_file`) → `backend/src/services/db/files.py:194-301` (`create_unified_file`).
   - Workflow dispatch: `backend/src/services/fetch_ftp.py:222-250` (`_dispatch_and_complete`) → `backend/src/services/tasks/workflow_tasks.py:78-160` (`dispatch_workflow`).
   - File storage for FTP path uses `FileStorage.save` (stores in `/data/storage/<id>/...`): `backend/src/services/storage.py:33-36` (`save`).

### Sequence diagram (text)
`Client` → `POST /ingest/fetch-ftp` (`backend/src/api/fetcher.py:15-37`, `trigger_fetch_ftp`)
→ `fetch_from_ftp` (`backend/src/services/fetch_ftp.py:424-535`)
→ `fetch_from_local_inbox` fallback (`backend/src/services/fetch_ftp.py:314-421`) when FTP_HOST missing
→ `_insert_unified_file` (`backend/src/services/fetch_ftp.py:113-219`)
→ `create_unified_file` (`backend/src/services/db/files.py:194-301`)
→ `dispatch_workflow` (`backend/src/services/tasks/workflow_tasks.py:78-160`).

### Evidence (DB results)
**Unified file created via FTP path**:
```
SELECT id, file_type, workflow_type, submitted_by, original_filename, ai_status, created_at
FROM unified_files
WHERE id='7129232b-f97e-405d-9afd-a8d290fbea9d';

id                                   file_type  workflow_type  submitted_by  original_filename         ai_status   created_at
7129232b-f97e-405d-9afd-a8d290fbea9d  receipt    WF1_RECEIPT    ftp           debug_overlay_sample.jpg  processing  2025-12-21 17:46:39
```

**Workflow run created for FTP file**:
```
SELECT id, workflow_key, status, current_stage, created_at, updated_at
FROM workflow_runs
WHERE file_id='7129232b-f97e-405d-9afd-a8d290fbea9d'
ORDER BY created_at DESC;

id   workflow_key  status   current_stage  created_at           updated_at
103  WF1_RECEIPT   running  dispatch       2025-12-21 17:46:40  2025-12-21 17:46:41
```

**Workflow stages recorded** (note: no `src_ftp` or `ingest_store` stages logged here):
```
SELECT workflow_run_id, stage_key, status, started_at, finished_at, message
FROM workflow_stage_runs
WHERE workflow_run_id=103
ORDER BY id;

workflow_run_id  stage_key         status     started_at           finished_at          message
103              ingest_wf1_start  succeeded  2025-12-21 17:46:40  2025-12-21 17:46:40   Skapar WF1 workflow_run
103              ingest_wf1        succeeded  2025-12-21 17:46:40  2025-12-21 17:46:42   WF1 dispatchad
103              dispatch          succeeded  NULL                 NULL                  WF1 dispatched to new wf1.* chain.
103              ingest_wf1_end    succeeded  2025-12-21 17:46:42  2025-12-21 17:46:42   WF1 dispatchad
```

### FTP vs upload divergence (code-backed)
- Upload path detects file type (`detect_file`) and chooses WF1 vs WF2 based on content kind; FTP path now uses `detect_file` when bytes are available but falls back to suffix-only inference if detection fails or bytes are missing, and skips unsupported kinds. `backend/src/api/ingest.py:56-216` (`upload_files`) + `backend/src/services/file_detection.py:67-92` (`detect_file`) vs `backend/src/services/fetch_ftp.py:151-207` (`_insert_unified_file`).
- Upload stores original files in `/data/storage/originals` via `save_original`, while FTP uses `save` into `/data/storage/<id>/`. `backend/src/services/storage.py:33-79` (`save`, `save_original`).
- FTP trigger endpoint no longer enqueues legacy `process_ocr`; workflow dispatch is handled inside `fetch_from_ftp` to avoid double-processing. `backend/src/api/fetcher.py:15-37` (`trigger_fetch_ftp`) + `backend/src/services/fetch_ftp.py:222-250` (`_dispatch_and_complete`).
