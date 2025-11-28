# Workflow Summary (WF1 / WF2 / WF3 / ManualMatch)

Version: 2025-11-28  
Goal: Fast orientation per workflow with entrypoints, stages, outputs, and references.

## Snapshot Table
| Workflow | Trigger | Primary stages | Outputs | Key code |
| --- | --- | --- | --- | --- |
| WF1_RECEIPT | `/ingest/upload` (image/pdf), FTP fetch | `dispatch → r_ocr → ocr → ai_pipeline (detect_type, r_ai3, r_ai4, r_persist, r_queue_match) → finalize_ok → KLAR` | `unified_files.ocr_raw`, AI3 data, accounting proposals, `workflow_runs/stage_runs` | `backend/src/api/ingest.py`, `services/tasks/ocr_tasks.py`, `services/tasks/ai_pipeline_tasks.py`, `services/tasks/workflow_tasks.py` |
| WF2_PDF_SPLIT | `/ingest/upload` (PDF) | `dispatch → prepare_pages → page_ocr* → merge_ocr → invoice_analysis → finalize` | Per-page `unified_files`, merged OCR text, `invoice_documents`/`invoice_lines`, stage logs | `services/tasks/ocr_tasks.py`, `services/tasks/workflow_tasks.py` |
| WF3_FIRSTCARD_INVOICE | `/reconciliation/firstcard/upload-invoice`, resume/restart routes | `firstcard_invoice → fc_ocr → ocr_merge → fc_parse (AI6) → fc_ready → auto_match/ai5 → m_found/m_link/m_unmatched → finalize_ok → KLAR` | `creditcard_invoices_main` + `_items`, `invoice_lines`, match state, stage logs | `services/workflow_coordinator.py`, `services/tasks/workflow_tasks.py`, `services/tasks/creditcard_tasks.py`, `services/ai_service.py` |
| ManualMatch | UI in `ManualMatch.jsx` fetching FC data | Fetch statements, invoice detail/lines, receipts; POST match/confirm endpoints | Updates `invoice_lines.match_status`, links receipts, toasts/pagination | `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`, backend routes under `api/reconciliation_firstcard/routes/` |

## WF1 Receipt Diagram
```mermaid
flowchart TD
  U[Upload/FTP] --> WFR[workflow_run WF1_RECEIPT]
  WFR --> OCR[wf1_run_ocr\nstage: r_ocr + ocr]
  OCR --> AI[wf1_run_ai_pipeline\nAI1 detect_type → AI2 expense → AI3 data → AI4 accounting]
  AI --> MATCH[r_queue_match]
  MATCH --> FIN[wf1_finalize\nfinalize_ok/finalize_fail + KLAR]
  FIN --> STAGE[workflow_stage_runs]
  AI --> AIH[ai_processing_history]
```

## WF2 PDF Split Diagram
```mermaid
flowchart TD
  U[Upload PDF] --> WFR2[workflow_run WF2_PDF_SPLIT]
  WFR2 --> SPLIT[wf2_prepare_pdf_pages\ncreate page files + page workflow runs]
  SPLIT --> POCR[wf2_run_page_ocr*]
  POCR --> MERGE[wf2_merge_ocr_results]
  MERGE --> ANALYZE[wf2_run_invoice_analysis\nbuild invoice_documents + invoice_lines]
  ANALYZE --> FIN2[wf2_finalize]
  FIN2 --> STAGE2[workflow_stage_runs]
```

## WF3 FirstCard Diagram
```mermaid
flowchart TD
  U[FC upload/resume/restart] --> FC_WFR[workflow_run WF3_FIRSTCARD_INVOICE]
  FC_WFR --> FC_OCR[fc_ocr + ocr_merge\n_firstcard_invoice stage]
  FC_OCR --> FC_PARSE[AI6 parse → persist creditcard_invoices_main/items + invoice_lines]
  FC_PARSE --> FC_READY[fc_ready\nprocessing_status=ready_for_matching]
  FC_READY --> AUTO[auto_match_invoice_lines + ai5]
  AUTO --> FOUND[m_found/m_link/m_unmatched]
  FOUND --> FC_FIN[finalize_ok + KLAR]
  FC_FIN --> STAGE3[workflow_stage_runs]
  FC_PARSE --> AIH3[ai_processing_history]
```

## ManualMatch Flow (UI)
```mermaid
flowchart TD
  User --> List[GET /reconciliation/firstcard/statements]
  List --> Detail[GET /reconciliation/firstcard/statements/{id}]
  Detail --> Lines[GET /reconciliation/firstcard/statements/{id}/lines]
  Detail --> Receipts[GET /receipts?creditcard_invoice_id=...]
  Lines --> Match[POST /reconciliation/firstcard/match]
  Lines --> Confirm[POST /reconciliation/firstcard/statements/{id}/confirm]
```

## What to check when debugging
- `workflow_runs/current_stage` and latest `workflow_stage_runs` row for the file.
- `ai_processing_history` rows for AI1–AI6 + AI5 matching.
- Invoice statuses via `invoice_documents.processing_status` and `invoice_documents.status` (transition helpers in `services/invoice_status.py`).
- FirstCard metadata in `invoice_documents.metadata_json` (period, summary, line counts).

## References
- Status definitions: `docs/MIND_STATUS_DEFINITIONS.md`, `docs/SYSTEM_DOCS/STATUS_MODEL.md`.
- Task inventory: `docs/SYSTEM_DOCS/TASK_INVENTORY.md`.
- Implementation guides: `docs/features/implementation_guides/MIND_FULL_UPDATE_2025-11-26_PHASE_*.md`.
