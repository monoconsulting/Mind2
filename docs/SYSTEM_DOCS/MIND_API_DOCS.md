# API Documentation

For endpoint schemas and request/response examples, see OpenAPI contracts in `specs/001-mind-system-receipt/contracts/`.

## Receipt Management
- `GET /ai/api/receipts` - list receipts
- `GET /ai/api/receipts/{id}` - get receipt details
- `POST /ai/api/reconciliation/firstcard/import` - import statement
- `GET /ai/api/export/sie` - export SIE for date range

## AI Processing Endpoints

### Document Classification (AI1)
- `POST /ai/api/ai/classify/document` - Classify document type (receipt/invoice/other)
  - Request: `{file_id, ocr_text?, image_path?}`
  - Response: `{file_id, document_type, confidence, reasoning?}`

### Expense Classification (AI2)
- `POST /ai/api/ai/classify/expense` - Classify expense type (personal/corporate)
  - Request: `{file_id, ocr_text?, document_type}`
  - Response: `{file_id, expense_type, confidence, card_identifier?}`

### Data Extraction (AI3)
- `POST /ai/api/ai/extract` - Extract structured data from receipt/invoice
  - Request: `{file_id, ocr_text, document_type, expense_type}`
  - Response: `{file_id, unified_file, receipt_items[], company, confidence}`
  - Updates: `unified_files`, `receipt_items`, `companies` tables

### Accounting Classification (AI4)
- `POST /ai/api/ai/classify/accounting` - Assign accounting entries per BAS-2025
  - Request: `{file_id, document_type, expense_type, amounts, vendor_name, receipt_items[]}`
  - Response: `{file_id, proposals[], confidence, based_on_bas2025}`
  - Creates: `ai_accounting_proposals` records

### Credit Card Matching (AI5)
- `POST /ai/api/ai/match/creditcard` - Match receipts with credit card transactions
  - Request: `{file_id, purchase_date, amount, merchant_name?}`
  - Response: `{file_id, matched, credit_card_invoice_item_id?, confidence, match_details?}`
  - Updates: `unified_files.credit_card_match` flag

### Batch Processing
- `POST /ai/api/ai/process/batch` - Process multiple files through AI pipeline
  - Request: `{file_ids[], processing_steps[], stop_on_error}`
  - Response: `{total_files, processed, failed, results[]}`

### Status Monitoring
- `GET /ai/api/ai/status/{file_id}` - Get AI processing status for a file
  - Response: `{file_id, ai_status, ai_confidence, document_type, expense_type, credit_card_matched, has_accounting_proposals, last_updated}`

## System & Monitoring
- `GET /ai/api/system/metrics` - Prometheus metrics (text/plain)
- `GET /ai/api/system/status` - Service health and component status

## Authentication
Auth: JWT Bearer (see `backend/src/api/middleware.py`).
All AI processing endpoints require authentication.
