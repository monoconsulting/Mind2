# FirstCard Workflow (WF3_FIRSTCARD_INVOICE)

Version: 2025-11-28  
Scope: Detailed orchestration for FirstCard statements (OCR → AI6 parse → AI5/auto-match → finalize). Reflects `wf3_firstcard_invoice` + `FirstCardWorkflowCoordinator`.

## Entry Points
- `POST /ai/api/reconciliation/firstcard/upload-invoice` (`backend/src/api/reconciliation_firstcard.py`)
- Resume: `/reconciliation/firstcard/statements/{id}/resume`
- Restart: `/reconciliation/firstcard/statements/{id}/restart`
- FTP/manual ingest can also set `workflow_type=WF3_FIRSTCARD_INVOICE`.

## Success Path
```mermaid
flowchart TD
  U[FC upload/resume] --> WFR[workflow_run WF3_FIRSTCARD_INVOICE]
  WFR --> FC_CREATE[firstcard_invoice stage\ncoordinator]
  FC_CREATE --> FC_OCR[fc_ocr + ocr_merge\npersist merged OCR to creditcard_invoices_main]
  FC_OCR --> FC_PARSE[fc_parse (AI6)\npersist header + lines]
  FC_PARSE --> FC_READY[fc_ready\nprocessing_status=ready_for_matching\ninvoice_documents.status=matching]
  FC_READY --> MATCH[auto_match_invoice_lines + ai5]
  MATCH --> FOUND[m_found/m_link/m_unmatched]
  FOUND --> FIN[finalize_ok + KLAR]
  FIN --> WSR[workflow_stage_runs]
```

## Error Path Highlights
```mermaid
flowchart TD
  FC_OCR -->|OCR error| FAIL_OCR[set processing_status=failed\nInvoiceDocumentStatus=failed]
  FC_PARSE -->|AI6 parse error| FAIL_PARSE[processing_status=failed → finalize_fail]
  MATCH -->|AI5/auto-match error| FAIL_MATCH[complete_fc_import_stage(auto_match/ai5, success=false)]
```

## Stage Keys (as logged)
- Import boundary: `src_fc` (upload), `fc_create`, `firstcard_invoice`.
- OCR: `fc_ocr`, `ocr_merge`.
- Parsing: `fc_parse` (AI6), `fc_is_fc` (decision), `fc_ready`.
- Matching: `auto_match`, `ai5`, `m_found`, `m_link`, `m_unmatched`.
- Finalization: `finalize_ok`, `KLAR`.

Writers: `FirstCardWorkflowCoordinator` and `wf3_firstcard_invoice` in `backend/src/services/tasks/workflow_tasks.py`.

## Status Transitions
- `invoice_documents.processing_status`: `uploaded → ocr_pending → ocr_done → ai_processing → ready_for_matching → matching_completed → completed/failed` (enforced by `services/invoice_status.py`).
- `invoice_documents.status`: `imported → matching → matched/partially_matched → completed/failed`.
- `workflow_runs.status`: set to `running/succeeded/failed` by `mark_stage` + `wf3_firstcard_invoice` final steps.

## DB Updates
- `creditcard_invoices_main` / `_items`: persisted in AI6 parse section.
- `invoice_lines`: created from AI6 payload for downstream ManualMatch.
- `workflow_stage_runs`: all stages above.
- `ai_processing_history`: AI6 + AI5 logs via `log_ai_call`.

## References
- `backend/src/services/workflow_coordinator.py`
- `backend/src/services/tasks/workflow_tasks.py` (WF3 body)
- `backend/src/services/tasks/creditcard_tasks.py` (matching helpers)
- Status enums: `backend/src/services/status_constants.py`
