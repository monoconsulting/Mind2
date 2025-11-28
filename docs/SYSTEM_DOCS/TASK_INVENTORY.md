# TASK INVENTORY

Updated: 2025-11-28  
Scope: Task entry points under `backend/src/services/tasks/` classified per PHASE G (active/legacy/unused/uncertain). No behaviour changes were made.

| Module path | Task / entry point | Classification | Description | Notes |
| --- | --- | --- | --- | --- |
| backend/src/services/tasks/workflow_tasks.py | `dispatch_workflow` | active | Routes `workflow_run` records to WF1/WF2/WF3 Celery chains. | Called from ingest/upload/resume flows (`api/ingest.py`, FC coordinator) and FTP ingestion. |
| backend/src/services/tasks/ocr_tasks.py | `wf1_run_ocr` | active | WF1 receipt OCR stage; updates workflow stage status. | Triggered by `dispatch_workflow` when `workflow_key=WF1_RECEIPT`. |
| backend/src/services/tasks/workflow_tasks.py | `wf1_run_ai_pipeline` | active | WF1 AI1–AI4 pipeline executor. | Runs after `wf1_run_ocr`; marks workflow stages only. |
| backend/src/services/tasks/workflow_tasks.py | `wf1_finalize` | active | WF1 finalizer that sets workflow_run status. | Follows AI pipeline stage. |
| backend/src/services/tasks/ocr_tasks.py | `wf2_prepare_pdf_pages` | active | WF2 PDF splitter; creates page files and schedules OCR. | Kicks off WF2 chain for PDF invoices/statements. |
| backend/src/services/tasks/ocr_tasks.py | `wf2_run_page_ocr` | active | WF2 per-page OCR task. | Fan-out task created by `wf2_prepare_pdf_pages`. |
| backend/src/services/tasks/ocr_tasks.py | `wf2_merge_ocr_results` | active | WF2 fan-in to merge page OCR and continue flow. | Invoked as chord callback; dispatches invoice analysis. |
| backend/src/services/tasks/ocr_tasks.py | `wf2_run_invoice_analysis` | active | WF2 invoice analysis stage to persist invoice lines. | Triggers `wf2_finalize` on success. |
| backend/src/services/tasks/workflow_tasks.py | `wf2_finalize` | active | WF2 finalizer updating workflow_run status. | Runs after WF2 analysis. |
| backend/src/services/tasks/workflow_tasks.py | `wf3_firstcard_invoice` | active | WF3 FirstCard invoice orchestration (OCR, AI6, AI5 match). | Dispatched for `workflow_key=WF3_FIRSTCARD_INVOICE`. |
| backend/src/services/tasks/legacy.py | `process_ocr` | legacy | Legacy OCR/router for receipts/invoices. | Still callable from `api/fetcher.py` and legacy scripts; bypasses workflow_runs. |
| backend/src/services/tasks/legacy.py | `process_ai_pipeline` | legacy | Legacy receipt AI pipeline (AI1–AI4) used by `process_ocr`. | Retained for backward compatibility; not used in new workflow chains. |
| backend/src/services/tasks/legacy.py | `process_classification` | legacy | Legacy document classification stage. | Only reachable via legacy flow; no current production callers observed. |
| backend/src/services/tasks/legacy.py | `process_validation` | legacy | Legacy receipt validation stage. | Triggered only from `process_classification` in legacy pipeline. |
| backend/src/services/tasks/legacy.py | `process_accounting_proposal` | legacy | Legacy accounting proposal generation for receipts. | Part of legacy flow; not used by workflow_runs. |
| backend/src/services/tasks/legacy.py | `process_invoice_ai_extraction` | legacy | Legacy invoice OCR aggregation step. | Enqueued from legacy invoice path; superseded by WF2/WF3. |
| backend/src/services/tasks/legacy.py | `process_matching` | uncertain | Legacy credit-card matching stub. | No production callers found; referenced in tests only. Left active pending confirmation. |
| backend/src/services/tasks/legacy.py | `hello` | unused | Debug/utility Celery task that prints greeting. | No references outside tests; safe to retire. |

Classification key:
- **active**: used in current workflow_run/Celery chains.
- **legacy**: kept for backward compatibility or legacy endpoints/scripts.
- **unused**: no known callers; safe to retire.
- **uncertain**: insufficient evidence to classify confidently.
