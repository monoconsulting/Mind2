# AGENT_AUDIT_INDEX
Generated: 2025-12-21 18:38:53

## File inventory (top 30 extensions)
Skipped 1 file(s) due to access errors (see generation log).

| Extension | Files | Total bytes | Latest mtime |
|---|---:|---:|---|
| .js | 39974 | 606860268 | 2025-12-20 21:36:18 |
| .ts | 13124 | 67597306 | 2025-12-21 13:45:49 |
| .py | 11895 | 138711098 | 2025-12-21 14:07:12 |
| .pyc | 11796 | 162996743 | 2025-12-21 13:50:05 |
| <no_ext> | 10684 | 659878802 | 2025-12-21 18:26:58 |
| .map | 7511 | 180737671 | 2025-09-24 22:45:13 |
| .json | 5855 | 21587633 | 2025-12-21 16:17:32 |
| .md | 3917 | 28729262 | 2025-12-21 14:13:36 |
| .flow | 2379 | 4880225 | 2025-09-22 03:23:46 |
| .h | 2246 | 20006545 | 2025-11-09 10:58:37 |
| .css | 993 | 7577157 | 2025-12-20 21:36:18 |
| .mjs | 631 | 170383419 | 2025-10-20 20:43:42 |
| .pyi | 525 | 4792296 | 2025-11-09 10:58:34 |
| .woff | 525 | 9755084 | 2025-09-22 17:12:06 |
| .woff2 | 525 | 7439188 | 2025-09-22 17:12:06 |
| .png | 403 | 225951238 | 2025-12-21 16:13:32 |
| .txt | 345 | 4665072 | 2025-11-09 10:58:49 |
| .yaml | 341 | 440118 | 2025-11-09 10:58:37 |
| .cjs | 319 | 7809625 | 2025-09-22 17:12:06 |
| .yml | 302 | 212264 | 2025-12-16 16:22:57 |
| .cts | 296 | 907449 | 2025-09-22 17:12:06 |
| .mts | 241 | 466085 | 2025-09-22 17:12:06 |
| .ps1 | 231 | 219744 | 2025-12-14 07:19:37 |
| .tsx | 226 | 1220256 | 2025-09-19 16:44:30 |
| .cmd | 187 | 60636 | 2025-10-20 20:43:42 |
| .html | 171 | 13809435 | 2025-12-21 14:10:04 |
| .pyd | 166 | 288919999 | 2025-11-09 10:58:09 |
| .php | 127 | 950434 | 2025-09-19 20:15:05 |
| .svg | 125 | 556807 | 2025-12-20 21:36:18 |
| .zip | 125 | 1612628906 | 2025-12-21 16:56:20 |

## Top-level architecture map (scope: import + OCR + AI1–AI4 + accounting)
- Upload import endpoint: `backend/src/api/ingest.py:56-216` (function `upload_files`).
- FTP trigger endpoint: `backend/src/api/fetcher.py:15-37` (function `trigger_fetch_ftp`).
- FTP ingestion/persistence: `backend/src/services/fetch_ftp.py:113-535` (functions `_insert_unified_file`, `_dispatch_and_complete`, `fetch_from_local_inbox`, `fetch_from_ftp`).
- Workflow run creation: `backend/src/services/workflow_runs.py:16-100` (functions `get_active_workflow_run`, `create_workflow_run`).
- Workflow dispatch: `backend/src/services/tasks/workflow_tasks.py:78-160` (function `dispatch_workflow`).
- WF1 OCR stage: `backend/src/services/tasks/ocr_tasks.py:51-127` (function `wf1_run_ocr`).
- WF2 OCR stages: `backend/src/services/tasks/ocr_tasks.py:131-704` (functions `wf2_prepare_pdf_pages`, `wf2_run_page_ocr`, `wf2_merge_ocr_results`, `wf2_run_invoice_analysis`).
- WF1 AI pipeline (AI1–AI4): `backend/src/services/tasks/ai_pipeline_tasks.py:59-575` (function `_run_ai_pipeline`).
- AI stage executors + persistence: `backend/src/api/ai_processing.py:379-867` (functions `_persist_extraction_result`, `_persist_accounting_proposals`, `classify_document_internal`, `classify_expense_internal`, `extract_data_internal`, `classify_accounting_internal`).
- AI4 LLM execution + parsing: `backend/src/services/ai_service.py:254-1227` (functions `parse_accounting_proposals`, `run_ai4_accounting_classification`).
- Accounting inputs loader + receipt_items + proposal persistence: `backend/src/services/tasks/file_management_tasks.py:60-650` (functions `_update_file_fields`, `_load_accounting_inputs`, `_load_receipt_items`, `_save_accounting_entries`).
- Workflow/stage logging: `backend/src/services/tasks/workflow_base.py:129-319` (functions `mark_stage`, `begin_import_stage`, `complete_import_stage`, `log_import_event`).
- AI history logging wrapper: `backend/src/services/tasks/history.py:6-34` (function `_history`).
- Receipt log/processing endpoints (frontend data): `backend/src/api/receipts.py:1405-2518` (functions `get_receipt`, `get_receipt_modal`, `get_receipt_accounting_proposal`, `get_receipt_log`, `get_workflow_status`).

## Symbol index (scope-critical)
### Flask routes (import)
- Upload: `backend/src/api/ingest.py:56-216` (`upload_files`).
- Resume: `backend/src/api/ingest.py:251-429` (`_resume_processing_internal`, `resume_processing`).
- FTP trigger: `backend/src/api/fetcher.py:15-37` (`trigger_fetch_ftp`).

### Celery tasks (workflow)
- WF1 OCR: `backend/src/services/tasks/ocr_tasks.py:51-127` (`wf1_run_ocr`).
- WF2 prepare pages: `backend/src/services/tasks/ocr_tasks.py:131-421` (`wf2_prepare_pdf_pages`).
- WF2 page OCR: `backend/src/services/tasks/ocr_tasks.py:425-500` (`wf2_run_page_ocr`).
- WF2 merge OCR: `backend/src/services/tasks/ocr_tasks.py:504-632` (`wf2_merge_ocr_results`).
- WF2 invoice analysis: `backend/src/services/tasks/ocr_tasks.py:636-704` (`wf2_run_invoice_analysis`).
- WF1 AI pipeline: `backend/src/services/tasks/ai_pipeline_tasks.py:59-575` (`_run_ai_pipeline`).
- WF1 finalize: `backend/src/services/tasks/workflow_tasks.py:219-317` (`wf1_finalize`).
- WF2 finalize: `backend/src/services/tasks/workflow_tasks.py:321-390` (`wf2_finalize`).
- WF3 FirstCard invoice: `backend/src/services/tasks/workflow_tasks.py:394-1006` (`wf3_firstcard_invoice`).

### Persistence + DB write helpers
- Unified file creation: `backend/src/services/db/files.py:194-301` (`create_unified_file`).
- Workflow run creation: `backend/src/services/workflow_runs.py:57-100` (`create_workflow_run`).
- AI3 persistence: `backend/src/api/ai_processing.py:379-600` (`_persist_extraction_result`).
- Receipt items replace: `backend/src/api/ai_processing.py:317-377` (`_replace_receipt_items`).
- AI4 proposals persistence: `backend/src/api/ai_processing.py:603-644` (`_persist_accounting_proposals`).
- Accounting proposal persistence (WF1 helper): `backend/src/services/tasks/file_management_tasks.py:625-650` (`_save_accounting_entries`).

### AI stage executors
- AI1 classification: `backend/src/api/ai_processing.py:801-823` (`classify_document_internal`).
- AI2 classification: `backend/src/api/ai_processing.py:826-848` (`classify_expense_internal`).
- AI3 extraction: `backend/src/api/ai_processing.py:851-859` (`extract_data_internal`).
- AI4 classification: `backend/src/api/ai_processing.py:862-867` (`classify_accounting_internal`).

### AI4 parsing/validation entrypoints
- Proposal parsing + per-entry validation: `backend/src/services/ai_service.py:190-384` (`_build_accounting_proposal`, `parse_accounting_proposals`).
- Proposal cross-entry validation: `backend/src/services/ai_service.py:393-442` (`_validate_accounting_proposals`).
- AI4 call + response handling: `backend/src/services/ai_service.py:1127-1227` (`run_ai4_accounting_classification`).
- Accounting inputs gate: `backend/src/services/tasks/file_management_tasks.py:395-583` (`_load_accounting_inputs`).

### SQL migrations (schema + view)
- `database/migrations/0007_add_ai_accounting_proposals.sql:1-14`
- `database/migrations/0010_expand_ai_schema.sql:1-157`
- `database/migrations/0047_create_view_v_receipt_missing_status.sql:1-260`

## Minimal call graph (upload → dispatch → OCR → AI → persist → AI4)
- Upload handler creates unified_files + workflow_run, logs stages, dispatches workflow: `backend/src/api/ingest.py:56-216` (`upload_files`) → `backend/src/services/db/files.py:194-301` (`create_unified_file`) → `backend/src/services/workflow_runs.py:57-100` (`create_workflow_run`) → `backend/src/services/tasks/workflow_tasks.py:78-160` (`dispatch_workflow`).
- WF1 OCR: `backend/src/services/tasks/workflow_tasks.py:78-160` (`dispatch_workflow`) → `backend/src/services/tasks/ocr_tasks.py:51-127` (`wf1_run_ocr`) → `_update_file_fields` (`backend/src/services/tasks/file_management_tasks.py:60-82`).
- WF1 AI pipeline: `backend/src/services/tasks/ai_pipeline_tasks.py:59-575` (`_run_ai_pipeline`) → AI1/AI2/AI3/AI4 internal executors (`backend/src/api/ai_processing.py:801-867`) → persistence (`backend/src/api/ai_processing.py:379-644`).
- AI4 proposals: `backend/src/api/ai_processing.py:862-867` (`classify_accounting_internal`) → `backend/src/services/ai_service.py:1127-1227` (`run_ai4_accounting_classification`) → `backend/src/services/ai_service.py:254-384` (`parse_accounting_proposals`) → `backend/src/api/ai_processing.py:603-644` (`_persist_accounting_proposals`).
