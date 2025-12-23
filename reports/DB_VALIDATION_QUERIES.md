# DB_VALIDATION_QUERIES
Date: 2025-12-21

All queries are **read-only**. Replace `<FILE_ID>` with the receipt/unified_files.id you want to inspect.

## Q1) Workflow runs + stage statuses for a receipt
```sql
SELECT
  wr.id AS workflow_run_id,
  wr.workflow_key,
  wr.status AS workflow_status,
  wr.current_stage,
  wr.created_at,
  wr.updated_at,
  ws.stage_key,
  ws.status AS stage_status,
  ws.started_at,
  ws.finished_at,
  ws.message
FROM workflow_runs wr
LEFT JOIN workflow_stage_runs ws
  ON ws.workflow_run_id = wr.id
WHERE wr.file_id = '<FILE_ID>'
ORDER BY wr.created_at DESC, ws.id ASC;
```
**Tables/columns referenced**:
- `workflow_runs.*` (created in `create_workflow_run`): `backend/src/services/workflow_runs.py:57-100`.
- `workflow_stage_runs.*` (written in `mark_stage`, `begin_import_stage`, `complete_import_stage`): `backend/src/services/tasks/workflow_base.py:129-296`.

## Q2) Extracted receipt fields used by AI4 (inputs)
```sql
SELECT
  uf.id,
  uf.company_id,
  c.name AS vendor_name,
  uf.gross_amount_sek,
  uf.net_amount_sek,
  uf.gross_amount_original,
  uf.net_amount_original,
  uf.currency,
  uf.exchange_rate,
  uf.total_vat_25,
  uf.total_vat_12,
  uf.total_vat_6,
  uf.payment_type,
  uf.receipt_number,
  (
    SELECT COUNT(*)
    FROM receipt_items ri
    WHERE ri.main_id = uf.id
  ) AS receipt_item_count
FROM unified_files uf
LEFT JOIN companies c ON uf.company_id = c.id
WHERE uf.id = '<FILE_ID>';
```
**Tables/columns referenced**:
- AI3 persistence into `unified_files` (payment_type, currency, exchange_rate, gross/net, VAT totals, receipt_number, etc.): `backend/src/api/ai_processing.py:379-600` (`_persist_extraction_result`).
- Company/vendor name stored in `companies` during AI3: `backend/src/api/ai_processing.py:176-314` (`_ensure_company`).
- AI4 deterministic normalization (auto-filling SEK totals + exchange_rate) in `_load_accounting_inputs`: `backend/src/services/tasks/file_management_tasks.py:395-583`.
- Receipt items persisted via `_replace_receipt_items`: `backend/src/api/ai_processing.py:317-377`.

## Q3) AI4 proposals + validation outcome
```sql
SELECT
  wr.id AS workflow_run_id,
  ws.status AS ai4_stage_status,
  ws.message AS ai4_message,
  COUNT(p.id) AS proposal_count,
  SUM(p.debit) AS total_debit,
  SUM(p.credit) AS total_credit
FROM workflow_runs wr
LEFT JOIN workflow_stage_runs ws
  ON ws.workflow_run_id = wr.id
 AND ws.stage_key = 'r_ai4'
LEFT JOIN ai_accounting_proposals p
  ON p.receipt_id = wr.file_id
WHERE wr.file_id = '<FILE_ID>'
GROUP BY wr.id, ws.status, ws.message;
```
**How to interpret**:
- Validation runs inside `run_ai4_accounting_classification`; failures raise `AccountingProposalValidationError` and are logged to the AI4 stage message: `backend/src/services/ai_service.py:1127-1227` + `backend/src/services/tasks/ai_pipeline_tasks.py:395-555`.
- Validated proposals are persisted in `ai_accounting_proposals` via `_persist_accounting_proposals`: `backend/src/api/ai_processing.py:603-644`.
- Stage messages are written by `complete_import_stage`: `backend/src/services/tasks/workflow_base.py:269-296`.
