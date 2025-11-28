# Full Data Flow (Upload → AI → Match → Finalize)

Version: 2025-11-28  
Scope: End-to-end operational path through WF1 (receipts), WF2 (PDF split), WF3 (FirstCard). Describes entrypoints, stage logs, DB touch points.

## Bird’s-eye Flow
```mermaid
flowchart TD
  U[File arrives\n(Portal/FTP/FC upload)] --> CUF[create_unified_file()\nservices/db/files.py]
  CUF --> WFR[workflow_runs row]
  WFR --> DISP[dispatch_workflow\nservices/tasks/workflow_tasks.py]
  DISP -->|WF1_RECEIPT| WF1_OCR[wf1_run_ocr\nr_ocr + stage 'ocr']
  WF1_OCR --> WF1_AI[wf1_run_ai_pipeline\nAI1-4 detect_type/r_ai3/r_ai4]
  WF1_AI --> WF1_FIN[wf1_finalize + finalize_ok/KLAR]
  DISP -->|WF2_PDF_SPLIT| WF2_SPLIT[wf2_prepare_pdf_pages\ncreate page files]
  WF2_SPLIT --> WF2_PAGE[wf2_run_page_ocr*] --> WF2_MERGE[wf2_merge_ocr_results]
  WF2_MERGE --> WF2_ANALYZE[wf2_run_invoice_analysis] --> WF2_FIN[wf2_finalize]
  DISP -->|WF3_FIRSTCARD_INVOICE| WF3_ORCH[wf3_firstcard_invoice\nFirstCardWorkflowCoordinator]
  WF3_ORCH --> FC_OCR[fc_ocr + ocr_merge] --> FC_PARSE[AI6 parse & persist]
  FC_PARSE --> FC_READY[fc_ready + status transitions] --> FC_MATCH[auto_match + ai5]
  FC_MATCH --> FC_FINAL[finalize_ok + KLAR]
  subgraph Logs & Status
    WSR[workflow_stage_runs]
    AIH[ai_processing_history]
    INV[invoice_documents / invoice_lines]
  end
  WF1_FIN & WF2_FIN & FC_FINAL --> WSR
  WF1_AI & FC_PARSE --> AIH
  FC_PARSE & FC_MATCH --> INV
```

## Key Steps with Sources
| Step | What happens | Stage keys / status | Code |
| --- | --- | --- | --- |
| Ingestion | Portal upload (`/ingest/upload`), FTP fetch (`services/fetch_ftp.py`), FC upload (`/reconciliation/firstcard/upload-invoice`). Dedup by SHA256; creates `unified_files` + `workflow_runs`. | `src_portal`, `src_ftp`, `src_fc`, `ingest_store`, `ingest_wf1` | `backend/src/api/ingest.py`, `services/db/files.py`, `services/tasks/workflow_base.py` |
| Dispatch | `dispatch_workflow` selects WF1/WF2/WF3 by `workflow_key` and enqueues Celery chain. | `dispatch` | `backend/src/services/tasks/workflow_tasks.py` |
| WF1 OCR | `wf1_run_ocr` pulls original file, runs PaddleOCR, stores `ocr_raw`, logs `r_ocr` + stage `ocr`. | `r_ocr`, `ocr` | `backend/src/services/tasks/ocr_tasks.py` |
| WF1 AI1–AI4 | `_run_ai_pipeline`: AI1 classify (`detect_type`), AI2 expense, AI3 data extraction (`r_ai3`), AI4 accounting (`r_ai4`), persist + queue match (`r_persist`, `r_queue_match`). | stage keys from `begin_import_stage` + `mark_stage` | `backend/src/services/tasks/ai_pipeline_tasks.py`, `services/ai_service.py` |
| WF1 Finalize | `wf1_finalize` evaluates AI pipeline result, updates `workflow_runs.status`, logs `finalize` + `finalize_ok`/`finalize_fail` + `KLAR`. | `finalize`, `finalize_ok`, `finalize_fail`, `KLAR` | `backend/src/services/tasks/workflow_tasks.py`, `workflow_base.py` |
| WF2 Split & OCR | `wf2_prepare_pdf_pages` -> per-page `create_unified_file` (workflow_key inherits?), fan-out `wf2_run_page_ocr`, merge text in `wf2_merge_ocr_results`. | `prepare_pages`, `page_ocr`, `merge_ocr` | `backend/src/services/tasks/ocr_tasks.py` |
| WF2 Invoice Analysis | `wf2_run_invoice_analysis` builds invoice_lines from merged OCR; writes `invoice_documents`/`invoice_lines`; marks stage `invoice_analysis`. | `invoice_analysis`, `finalize` | `backend/src/services/tasks/ocr_tasks.py`, `services/tasks/workflow_tasks.py` |
| WF3 OCR & Merge | `wf3_firstcard_invoice` starts `firstcard_invoice` + `fc_ocr`, persists merged OCR to `creditcard_invoices_main`, updates processing status to `ocr_pending` → `ocr_done`. | `firstcard_invoice`, `fc_ocr`, `ocr_merge` | `backend/src/services/tasks/workflow_tasks.py`, `services/workflow_coordinator.py` |
| WF3 AI6 Parse | AI6 via `AIService` extracts header + lines, persisted to `creditcard_invoice_items` + `invoice_lines`; updates invoice metadata and processing/document statuses. | `fc_parse`, `fc_ready` | `backend/src/services/tasks/workflow_tasks.py`, `services/ai_service.py` |
| WF3 Match | `auto_match_invoice_lines` + AI5 matching; logs `auto_match`, `ai5`, `m_found`, `m_link`, `m_unmatched`; transitions `invoice_documents.processing_status` to `ready_for_matching` → `matching_completed` (on success). | `auto_match`, `ai5`, `m_found`, `m_link`, `m_unmatched` | `backend/src/services/tasks/workflow_tasks.py`, `services/tasks/creditcard_tasks.py` |
| WF3 Finalize | Logs `finalize_ok` + `KLAR`; sets `workflow_runs.status`. | `finalize_ok`, `KLAR` | `backend/src/services/tasks/workflow_tasks.py` |

## Data Touch Points
- **unified_files**: created once per upload (and per derived page in WF2). Fields set: `workflow_type` (WF1_RECEIPT/WF2_PDF_SPLIT/WF3_FIRSTCARD_INVOICE), `ai_status` via `set_ai_status`.
- **workflow_runs / workflow_stage_runs**: stage history for every workflow; helpers live in `services/tasks/workflow_base.py`.
- **ai_processing_history**: populated by `_history` (legacy) and `log_ai_call` for AI1–AI6, matching, FTP steps.
- **invoice_documents / invoice_lines**: WF2/WF3 persistence + state transitions in `services/invoice_status.py`.
- **creditcard_invoices_main / creditcard_invoice_items**: FC-specific raw storage created during WF3.

## Status Crosswalk (where updates happen)
| Status field | Writer | Values (enum) | Notes |
| --- | --- | --- | --- |
| `workflow_runs.status` | `mark_stage`, `wf*_finalize` | queued, running, succeeded, failed, canceled | Mirrors latest stage outcome. |
| `workflow_stage_runs.status` | `mark_stage` / `begin_import_stage` / `complete_import_stage` | queued, running, succeeded, failed, skipped | DB columns: `stage_key`, `started_at`, `finished_at`. |
| `unified_files.ai_status` | `set_ai_status`, `begin_import_stage` (source stages), `complete_import_stage` (`finalize_ok`) | uploaded, processing, ocr_done, ocr_failed, manual_review, completed, failed | Enum in `services/status_constants.py`. |
| `invoice_documents.processing_status` | `transition_processing_status` | uploaded → ocr_pending → ocr_done → ai_processing → ready_for_matching → matching_completed → completed/failed | Guarded in `services/invoice_status.py`. |
| `invoice_documents.status` | `transition_document_status` | imported → matching → matched/partially_matched → completed/failed | Guarded in `services/invoice_status.py`. |

## Notes
- WF2 page-derived `create_unified_file` uses parent workflow information; ensure `workflow_type` propagation stays consistent with dispatch expectations.
