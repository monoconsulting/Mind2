# ManualMatch Workflow (UI-driven reconciliation)

Version: 2025-11-28  
Scope: How the ManualMatch page interacts with backend data produced by WF3.

## Flow Diagram
```mermaid
flowchart TD
  User --> LIST[GET /reconciliation/firstcard/statements]
  LIST --> DETAIL[GET /reconciliation/firstcard/statements/{id}]
  DETAIL --> LINES[GET /reconciliation/firstcard/statements/{id}/lines]
  DETAIL --> RECEIPTS[GET /receipts?creditcard_invoice_id=...]
  LINES --> MATCH[POST /reconciliation/firstcard/match]
  MATCH --> UPDATE[invoice_lines.match_status updated via transition_line_status_and_link]
  LINES --> CONFIRM[POST /reconciliation/firstcard/statements/{id}/confirm]
  CONFIRM --> STATUS[invoice_documents.status -> matched/partially_matched/completed]
```

## UI Behaviour (current)
- Component: `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`
- Features: pagination controls, toasts via `showError/showSuccess`, renders subset of FC lines + candidate receipts.
- Depends on data produced by WF3 (`invoice_documents`, `invoice_lines`, `creditcard_invoices_main`).

## Backend Touch Points
| Endpoint | Purpose | Code |
| --- | --- | --- |
| `GET /reconciliation/firstcard/statements` | List FC statements. | `backend/src/api/reconciliation_firstcard/routes/statements.py` |
| `GET /reconciliation/firstcard/statements/{id}` | Statement header/detail. | same |
| `GET /reconciliation/firstcard/statements/{id}/lines` | Lines for UI table (includes match_status). | `routes/lines.py` |
| `GET /receipts` (filtered) | Candidate receipts for matching. | `backend/src/api/receipts.py` |
| `POST /reconciliation/firstcard/match` | Link receipt ↔ invoice_line; updates `invoice_lines.match_status` + `unified_files.credit_card_match`. | `routes/match.py` |
| `POST /reconciliation/firstcard/statements/{id}/confirm` | Confirm statement after matching; transitions invoice statuses. | `routes/statements.py` |

## Statuses Involved
- `invoice_lines.match_status`: `pending|auto|manual|confirmed|unmatched|ignored` (state machine in `services/invoice_status.py`).
- `invoice_documents.processing_status` and `.status`: should be `ready_for_matching` / `matching` before UI actions; confirmation moves to `matching_completed` / `completed`.

## Observability
- Workflow context from `workflow_stage_runs` for the statement’s workflow_run_id.
- Matching actions may log to `ai_processing_history` when AI5 is invoked upstream; ManualMatch itself does not call AI.

## Tips for debugging
- Verify `invoice_lines` have `creditcard_main_id` and `unified_file_id` set by WF3.
- Check latest `workflow_stage_runs` for `auto_match`/`m_link` events before troubleshooting UI match failures.
