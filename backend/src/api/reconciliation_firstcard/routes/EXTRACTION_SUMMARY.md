# Route Extraction Summary - Phase 2

**Date:** 2025-11-09
**Extracted from:** `backend/src/api/reconciliation_firstcard.py`

## Files Created

### 1. `routes/log.py` (297 lines)
**Endpoint extracted:**
- `GET /reconciliation/firstcard/invoices/<invoice_id>/log` (lines 1149-1417)

**Purpose:** Complex log aggregator endpoint providing detailed workflow and AI processing logs.

**Key features:**
- Aggregates data from `unified_files`, `workflow_runs`, `workflow_stage_runs`, and `ai_processing_history`
- Includes mojibake encoding fixes for Swedish characters
- Returns comprehensive workflow execution history

---

### 2. `routes/upload.py` (326 lines)
**Endpoints extracted:**
- `POST /reconciliation/firstcard/upload-invoice` (lines 540-688)
- `POST /reconciliation/firstcard/import` (lines 690-795)

**Purpose:** Handles invoice file uploads and manual JSON imports.

**Key features:**
- PDF/image file upload handling with duplicate detection
- Workflow orchestration via WorkflowCoordinator
- Manual JSON line import for admin flows
- Transaction line insertion with status management

---

### 3. `routes/status.py` (386 lines)
**Endpoints extracted:**
- `GET /reconciliation/firstcard/invoices/<invoice_id>/status` (lines 797-895)
- `GET /reconciliation/firstcard/invoices/<invoice_id>` (lines 897-1147)

**Purpose:** Provides invoice processing status and detailed invoice information.

**Key features:**
- OCR progress tracking with page-level granularity
- Line count aggregation (total/matched/unmatched)
- Credit card item details with receipt matching
- Comprehensive invoice metadata retrieval

---

### 4. `routes/lines.py` (337 lines)
**Endpoints extracted:**
- `GET /reconciliation/firstcard/invoices/<invoice_id>/lines` (lines 1420-1511)
- `GET /reconciliation/firstcard/lines/<int:line_id>/candidates` (lines 1513-1724)

**Purpose:** Invoice line item listing and candidate matching.

**Key features:**
- Paginated line item retrieval (limit/offset support)
- Smart candidate matching algorithm with scoring
- Date/amount proximity search (±7 days, ±200 SEK)
- Match score calculation based on date and amount differences

---

### 5. `routes/matching.py` (295 lines)
**Endpoints extracted:**
- `POST /reconciliation/firstcard/match` (lines 1726-1785)
- `PUT /reconciliation/firstcard/lines/<int:line_id>` (lines 1787-1953)

**Purpose:** Automatic and manual matching of invoice lines to receipts.

**Key features:**
- Automatic batch matching via `auto_match_invoice_lines()`
- Manual line-to-receipt linking with conflict detection
- Match history logging
- State transition validation (pending → auto/manual)
- Metrics recording via `record_invoice_decision()`

---

### 6. `routes/statements.py` (510 lines)
**Endpoints extracted:**
- `GET /reconciliation/firstcard/statements` (lines 1955-2104)
- `DELETE /reconciliation/firstcard/statements/<sid>` (lines 2106-2174)
- `POST /reconciliation/firstcard/statements/<sid>/resume` (lines 2176-2249)
- `POST /reconciliation/firstcard/statements/<sid>/restart` (lines 2251-2346)
- `POST /reconciliation/firstcard/statements/<sid>/confirm` (lines 2348-2383)
- `GET /reconciliation/firstcard/statements/<sid>/lines` (lines 2385-2417)

**Purpose:** Statement listing, deletion, workflow control, and confirmation.

**Key features:**
- List all credit card statements with metadata
- Soft deletion (sets `deleted_at` timestamp)
- Resume stalled workflows (continues from current stage)
- Restart workflows from beginning (new workflow run)
- Statement confirmation (marks as completed)
- Dynamic updated_at column detection

---

### 7. `routes/__init__.py` (29 lines)
**Purpose:** Route module registration and documentation.

**Imports all route modules:**
- log
- upload
- status
- lines
- matching
- statements

---

## Endpoints Summary

**Total endpoints extracted:** 15

### Upload/Import (2)
1. `POST /reconciliation/firstcard/upload-invoice`
2. `POST /reconciliation/firstcard/import`

### Status/Details (3)
3. `GET /reconciliation/firstcard/invoices/<invoice_id>/status`
4. `GET /reconciliation/firstcard/invoices/<invoice_id>`
5. `GET /reconciliation/firstcard/invoices/<invoice_id>/log`

### Lines (2)
6. `GET /reconciliation/firstcard/invoices/<invoice_id>/lines`
7. `GET /reconciliation/firstcard/lines/<int:line_id>/candidates`

### Matching (2)
8. `POST /reconciliation/firstcard/match`
9. `PUT /reconciliation/firstcard/lines/<int:line_id>`

### Statements (6)
10. `GET /reconciliation/firstcard/statements`
11. `DELETE /reconciliation/firstcard/statements/<sid>`
12. `POST /reconciliation/firstcard/statements/<sid>/resume`
13. `POST /reconciliation/firstcard/statements/<sid>/restart`
14. `POST /reconciliation/firstcard/statements/<sid>/confirm`
15. `GET /reconciliation/firstcard/statements/<sid>/lines`

---

## Encoding Compliance

✓ All files include `# -*- coding: utf-8 -*-` header
✓ All files include kontrollrad `# Kontrollrad: ÅÄÖ åäö`
✓ Swedish character encoding fixes preserved in log.py

---

## Import Dependencies

### From utils.db_helpers:
- `load_invoice_document()`
- `count_invoice_lines()`
- `list_invoice_files()`
- `create_invoice_document()`
- `write_invoice_metadata()`
- `find_file_id_by_hash()`
- `find_invoice_id_for_main()`
- `find_invoice_line_id_for_item()`
- `log_line_history()`
- `as_date()`
- `as_decimal()`

### From services.workflow_coordinator:
- `WorkflowCoordinator` class

### From services.tasks:
- `auto_match_invoice_lines()`
- `dispatch_workflow()`
- `log_import_event()`
- `refresh_invoice_match_state()`

### From services.invoice_status:
- Status enums and transition functions

---

## Notes

- All endpoints extracted EXACTLY as they were
- NO logic changes made
- All imports preserved
- All error handling preserved
- Blueprint registration maintained via `@recon_bp` decorators
- Each module is self-contained with necessary imports
