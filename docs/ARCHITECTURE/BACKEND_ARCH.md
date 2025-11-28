# Backend Architecture Map

Version: 2025-11-28  
Scope: Module-by-module layout of the backend stack (Flask + Celery + MySQL). Reflects current code on branch `dev`/`TM999-phase-h-implementation`.

## Module Topology
| Area | Responsibilities | Entry files |
| --- | --- | --- |
| API Blueprints | HTTP endpoints for ingest, receipts, FirstCard, export. Auth enforced via `api.middleware.auth_required`. | `backend/src/api/ingest.py`, `backend/src/api/receipts.py`, `backend/src/api/reconciliation_firstcard.py`, `backend/src/api/export.py` |
| Workflow Registry | Create and read `workflow_runs`; prevent duplicate runs. | `backend/src/services/workflow_runs.py` |
| Workflow Stages | Insert/update `workflow_stage_runs`, boundary markers, AI status updates. | `backend/src/services/tasks/workflow_base.py` (`mark_stage`, `begin_import_stage`, `complete_import_stage`) |
| Task Orchestration | Dispatch `workflow_run` records to WF1/WF2/WF3 Celery chains; per-workflow finalizers. | `backend/src/services/tasks/workflow_tasks.py` |
| OCR & File Prep | Receipt OCR, PDF splitting, page OCR merge, invoice analysis. | `backend/src/services/tasks/ocr_tasks.py`, `services/pdf_conversion.py`, `services/ocr.py` |
| AI Pipeline | AI1–AI4 orchestrators, validation, provider routing, accounting proposal building. | `backend/src/services/tasks/ai_pipeline_tasks.py`, `services/ai_service.py`, `services/ai/providers/*` |
| FirstCard Coordinator | Stage creation + status transitions for FC workflow; resume/restart helpers. | `backend/src/services/workflow_coordinator.py`, `backend/src/services/tasks/workflow_tasks.py` (WF3 body) |
| Status State Machines | Legal transitions for invoice processing + line match states; emits metrics on assertion failures. | `backend/src/services/invoice_status.py`, `backend/src/services/status_constants.py` |
| Data Access | CRUD + helpers for unified_files and metadata; dedupe + workflow bootstrap. | `backend/src/services/db/files.py`, `backend/src/services/db/connection.py` |
| Observability | AI call logging (`ai_processing_history`), workflow event logging (`observability/events.py`), metrics (`observability/metrics.py`). | `backend/src/services/ai_logging.py`, `backend/src/services/tasks/history.py` |

## Runtime Topology (Mermaid)
```mermaid
flowchart LR
    subgraph API
      ING[/ingest_bp/] --> DISPATCH[dispatch_workflow]
      FCAPI[/reconciliation_firstcard/] --> FC_COORD[FirstCardWorkflowCoordinator]
    end
    DISPATCH --> CELERY{{Celery broker (Redis)}}
    FC_COORD --> CELERY
    subgraph Workers
      WF1[Queue wf1\nwf1_run_ocr → wf1_run_ai_pipeline → wf1_finalize]
      WF2[Queue wf2\nwf2_prepare_pdf_pages → wf2_run_page_ocr* → wf2_merge_ocr_results → wf2_run_invoice_analysis → wf2_finalize]
      WF3[Queue default\nwf3_firstcard_invoice (fc_ocr → fc_parse → ai5/auto_match → finalize_ok/KLAR)]
    end
    CELERY --> WF1 & WF2 & WF3
    WF1 & WF2 & WF3 --> DB[(MySQL)]
    DB -.->|workflow_runs\nworkflow_stage_runs| OBS[(Observability dashboards)]
```

## Data Stores and Writers
- `workflow_runs`: inserted via `create_workflow_run` (files.py) and updated by `mark_stage`/`wf*_finalize`.
- `workflow_stage_runs`: updated by `mark_stage`, `begin_import_stage`, `complete_import_stage`, and `FirstCardWorkflowCoordinator`.
- `ai_processing_history`: written by `services/ai_logging.log_ai_call` (AI pipeline, FTP ingestion, workflow tasks).
- `invoice_documents` / `invoice_lines`: updated through `invoice_status.transition_*` helpers and WF2/WF3 persistence helpers (`invoice_tasks.py`, `workflow_tasks.py`).

## Queue & Service Layout (docker-compose)
- **ai-api** (Flask) exposes `/ai/api/*`.
- **celery-worker** (default queue), **celery-worker-wf1** (`wf1` queue), **celery-worker-wf2** (`wf2` queue).
- **mysql** (port 3310 external), **redis** (6380), **nginx** (8008), **mind-web-main-frontend-dev** (5169).

## Call Flow Examples
1) **Receipt upload**  
`POST /ingest/upload` → `create_unified_file()` → `workflow_runs` row with `workflow_key=WF1_RECEIPT` → `dispatch_workflow` enqueues `wf1_run_ocr` → `wf1_run_ai_pipeline` (AI1–AI4) → `wf1_finalize`.

2) **FirstCard statement upload**  
`POST /reconciliation/firstcard/upload-invoice` → `create_unified_file()` with `workflow_type=WF3_FIRSTCARD_INVOICE` → `FirstCardWorkflowCoordinator.create_workflow_run_for_fc_document` → `dispatch_fc_workflow` enqueues `wf3_firstcard_invoice` → OCR merge → AI6 parse + persistence → AI5/auto_match → finalize stages.

3) **Resume / restart**  
`/ingest/process/{id}/resume` and `/reconciliation/firstcard/statements/{id}/resume|restart` call coordinator + `dispatch_workflow` to continue existing `workflow_run`.

## Safety & Constraints
- No mock data, no SQLite, no port changes (see `AGENTS.md` + `CLAUDE.md`).
- Do not edit `playwright.config.ts`; dev tests use `playwright.dev.config.ts`.
- Encoding must remain UTF-8 (see `docs/SWEDISH_ENCODING_RULES.md`).

## Pointers for deeper reading
- Status definitions: `docs/MIND_STATUS_DEFINITIONS.md`, transitions in `docs/MIND_STATUS_TRANSITIONS.md`.
- Task inventory: `docs/SYSTEM_DOCS/TASK_INVENTORY.md`.
- Workflow guides (per-phase): `docs/features/implementation_guides/MIND_FULL_UPDATE_2025-11-26_PHASE_*.md`.
