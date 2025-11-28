# Mind2 System Overview

Version: 2025-11-28  
Scope: High-level description of Mind2 architecture, workflows, data model, and observability sources. No code changes.

## Components at a Glance
| Layer | What it does | Key files |
| --- | --- | --- |
| API Gateway | Flask blueprints expose `/ai/api/*` for ingest, FirstCard, receipts, export. | `backend/src/api/ingest.py`, `backend/src/api/reconciliation_firstcard.py`, `backend/src/api/receipts.py` |
| Workflow Engine | `workflow_runs` + `workflow_stage_runs` tables plus Celery tasks dispatch WF1/WF2/WF3. | `backend/src/services/workflow_runs.py`, `backend/src/services/tasks/workflow_tasks.py`, `backend/src/services/tasks/workflow_base.py` |
| Task Executors | Celery workers on queues `default`, `wf1`, `wf2`; orchestrate OCR, AI1–AI6, matching, finalization. | `backend/src/services/tasks/ocr_tasks.py`, `backend/src/services/tasks/ai_pipeline_tasks.py`, `backend/src/services/tasks/workflow_tasks.py` |
| AI Layer | Orchestrates provider calls, validates responses, and logs to `ai_processing_history`. | `backend/src/services/ai_service.py`, `backend/src/services/ai/providers/*`, `backend/src/services/ai_logging.py` |
| Data Layer | DB helpers for files, invoices, status transitions, and metadata. | `backend/src/services/db/files.py`, `backend/src/services/invoice_status.py`, migrations `database/migrations/0042_create_workflow_tracking.sql` |
| Frontend | React/Vite (hot reload on 5169) + Playwright tests. | `main-system/app-frontend/src/*`, `playwright.dev.config.ts` |
| Storage & Infra | File storage under `/data/storage`, Redis broker, MySQL 8, Nginx reverse proxy. | `docker-compose.yml`, `.env.example`, `services/storage.py` |

## Core Workflows (summary)
- **WF1_RECEIPT** – Image/PDF receipts uploaded via `/ingest/upload` -> workflow run -> OCR (`wf1_run_ocr`) -> AI1–AI4 pipeline -> finalize. Dispatch: `dispatch_workflow()` in `workflow_tasks.py`.
- **WF2_PDF_SPLIT** – Multi-page invoices/FC PDFs -> PDF split to per-page files -> page OCR -> merge -> invoice analysis -> finalize.
- **WF3_FIRSTCARD_INVOICE** – FC statements uploaded via `/reconciliation/firstcard/upload-invoice` or FTP -> `FirstCardWorkflowCoordinator` creates workflow run -> OCR merge -> AI6 parse -> AI5/auto-match -> finalize.
- **ManualMatch** – UI-driven reconciliation uses invoice_documents + invoice_lines populated by WF3, surfaced via `api/reconciliation_firstcard/routes/*`.

## Data Model (minimum needed for orientation)
| Table | Purpose | Important columns |
| --- | --- | --- |
| `unified_files` | Canonical file record; created by `create_unified_file()`; carries `workflow_type`, `ai_status`, `content_hash`, `original_filename`. | `id`, `workflow_type`, `ai_status`, `content_hash`, `original_file_id`, `other_data` |
| `workflow_runs` | Tracks each dispatched pipeline instance. | `id`, `workflow_key` (WF1/WF2/WF3), `file_id`, `current_stage`, `status` |
| `workflow_stage_runs` | Per-stage history written by `mark_stage` / `begin_import_stage`. | `workflow_run_id`, `stage_key`, `status`, `started_at`, `finished_at`, `message` |
| `ai_processing_history` | Per-AI-call log written by `log_ai_call`. | `file_id`, `job_type`, `ai_stage_name`, `status`, `provider`, `model_name`, `processing_time_ms` |
| `invoice_documents` / `invoice_lines` | Normalized invoice + line items; status machines enforced by `invoice_status.py`. | `processing_status`, `status`, `match_status`, `metadata_json` |
| `creditcard_invoices_main` / `creditcard_invoice_items` | FirstCard header + extracted lines from AI6. | Statement metadata, parsed lines |

## Observability Sources
- **Workflow history:** `workflow_stage_runs` (stage_key + status + timestamps) with helper views `v_workflow_overview`, `v_workflow_stages` from `0042_create_workflow_tracking.sql`.
- **AI logs:** `ai_processing_history` via `services/ai_logging.log_ai_call` (used in AI pipeline, FTP ingestion, workflow tasks).
- **Status transitions:** `services/invoice_status.py` guards allowed transitions; metrics emitted via `observability.metrics.record_invoice_state_assertion`.
- **Import events:** `begin_import_stage` / `complete_import_stage` log boundary markers (e.g., `src_portal_start`, `fc_ocr_end`) and set `ai_status`.

## High-Level Flow (Mermaid)
```mermaid
flowchart LR
  U[Upload/FTP/API] --> CUF[create_unified_file()\nservices/db/files.py]
  CUF --> WFR[workflow_runs row]
  WFR -->|dispatch_workflow| CEL[Celery queue (wf1/wf2/wf3)]
  CEL -->|WF1| OCR1[wf1_run_ocr] --> AI1[wf1_run_ai_pipeline (AI1-4)] --> FIN1[wf1_finalize]
  CEL -->|WF2| SPLIT[wf2_prepare_pdf_pages] --> POCR[wf2_run_page_ocr*] --> MERGE[wf2_merge_ocr_results] --> ANALYZE[wf2_run_invoice_analysis] --> FIN2[wf2_finalize]
  CEL -->|WF3| FC_OCR[wf3_firstcard_invoice: fc_ocr/ocr_merge] --> FC_PARSE[AI6 parse & persist] --> MATCH[auto_match/ai5] --> KLAR[finalize_ok + KLAR]
  FIN1 & FIN2 & KLAR --> WSR[workflow_stage_runs log]
```

## Source of Truth Pointers
- Workflow dispatch & stages: `backend/src/services/tasks/workflow_tasks.py`, `workflow_base.py`.
- FirstCard orchestration: `backend/src/services/workflow_coordinator.py` (note: uses `stage_name`/`start_time` fields; DB uses `stage_key`/`started_at`).
- Status enums: `backend/src/services/status_constants.py`.
- State machines: `backend/src/services/invoice_status.py`.
- Ingestion entrypoint: `backend/src/api/ingest.py` (web upload, resume), `services/fetch_ftp.py` (FTP).
- AI pipeline orchestrators: `backend/src/services/ai_service.py`, `tasks/ai_pipeline_tasks.py`, `services/ai_logging.py`.

## Notes
- Legacy `services/tasks/legacy.py` tasks remain; classified as legacy/uncertain in `docs/SYSTEM_DOCS/TASK_INVENTORY.md`. New docs describe active WF1–WF3 only.
