# FirstCard Workflow (WF3_FIRSTCARD_INVOICE)

Version: 2026-01-22
Scope: Detailed orchestration for FirstCard statements (OCR → AI6 parse → AI5/auto-match → finalize). Reflects `wf3_firstcard_invoice` + `FirstCardWorkflowCoordinator`.
Updated: Added box-driven tabular parsing documentation (fc_cards_table_v1, currency handling).

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

## Box-Driven Tabular Parsing (fc_parse Stage)

### Decision Rule
When OCR boxes are available (i.e., `ocr_boxes.json` exists in storage for each page file), the FC statement parsing uses the **box-driven tabular parser** (`backend/src/services/fc_cards_tabular.py`) instead of raw OCR text parsing.

**Parser selection logic:**
1. Check if page files have `ocr_boxes.json` in storage (`/data/storage/<page_file_id>/ocr_boxes.json`)
2. If boxes exist → use `fc_cards_tabular.parse_fc_statement_from_boxes()`
3. If boxes missing → fall back to legacy text-based parsing

### Stage Execution
The `fc_parse` stage (logged in `workflow_stage_runs`) executes the tabular parser:
- **Stage key:** `fc_parse`
- **Success message format:** `"Tabell tolkad: N rader"` or `"Tolkade N rader"`
- **Location in workflow:** After `fc_ocr` and `ocr_merge`, before `fc_ready`

### Artifacts: fc_cards_table_v1 Snapshot
The tabular parser produces an internal structure (`fc_cards_table_v1`) containing:
- `row_count`: Number of transaction rows extracted
- `page_count`: Number of PDF pages processed
- `warnings`: Any parsing warnings (OCR quality issues, ambiguous tokens)
- `rows[]`: Individual transaction data before DB persistence

### Persistence to creditcard_invoice_items
Each row from `fc_cards_table_v1` is persisted to `creditcard_invoice_items` table with:
- `main_id`: FK to `creditcard_invoices_main`
- `line_no`: Sequential row number
- `merchant_name`, `purchase_date`, `amount_sek`: Core transaction data
- `currency_original`, `amount_original`, `exchange_rate`: Foreign currency fields (see below)

## Currency Handling (Foreign Transactions)

### Token Extraction
Foreign currency transactions are identified by tokens in the OCR text:
- **Original amount token:** Format like `"USD 240,00"` → extracts `currency_original=USD`, `amount_original=240.00`
- **Exchange rate token:** Format like `"Valutakurs 11,0297"` → extracts `exchange_rate=11.0297`

### OCR Cleaning
The parser applies OCR error correction:
- `_clean_exchange_rate_token()`: Handles common OCR errors (e.g., `"1l"` → `"11"`)
- `_parse_swe_decimal_lenient()`: Parses Swedish decimal format with 4+ decimal places (required for exchange rates)

### Field Mapping
| Source Token | DB Column | Example |
|--------------|-----------|---------|
| `"USD 240,00"` | `currency_original` | `USD` |
| `"USD 240,00"` | `amount_original` | `240.00` |
| `"Valutakurs 11,0297"` | `exchange_rate` | `11.029700` |
| Statement amount | `amount_sek` | `2647.13` |

### SEK-Only Transactions
For domestic (SEK) transactions:
- `currency_original = 'SEK'`
- `amount_original = NULL` or same as `amount_sek`
- `exchange_rate = 0.000000`

## DB Updates
- `creditcard_invoices_main` / `_items`: persisted in AI6 parse section (via tabular parser when boxes available).
- `invoice_lines`: created from AI6 payload for downstream ManualMatch.
- `workflow_stage_runs`: all stages above.
- `ai_processing_history`: AI6 + AI5 logs via `log_ai_call`.

## References
- `backend/src/services/workflow_coordinator.py`
- `backend/src/services/tasks/workflow_tasks.py` (WF3 body)
- `backend/src/services/tasks/creditcard_tasks.py` (matching helpers)
- `backend/src/services/fc_cards_tabular.py` (box-driven tabular parser)
- Status enums: `backend/src/services/status_constants.py`
