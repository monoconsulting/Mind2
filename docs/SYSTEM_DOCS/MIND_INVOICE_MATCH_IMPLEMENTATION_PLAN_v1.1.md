# Credit Card Invoice Matching - Implementation Plan

**Version:** 1.1
**Date:** 2025-10-04
**Status:** Approved for Implementation

---

## Executive Summary

This document provides a comprehensive implementation plan for adding credit card invoice upload and matching functionality to the MIND system. The feature will allow users to upload multi-page credit card invoices (PDF or images) through the "Kortmatchning" (Card Matching) menu, process them through OCR, extract transaction data via AI, and automatically match transactions to existing receipts in the system. This version (1.1) integrates previously identified improvements directly into the plan to ensure a robust, maintainable, and secure implementation.

---

## 1. Current State Analysis

(This section remains unchanged from v1.0)

### 1.1 Existing Infrastructure
- **PDF Processing Pipeline:** `backend/src/services/pdf_conversion.py` (`pdf_to_png_pages()`)
- **Credit Card Reconciliation:** `backend/src/api/reconciliation_firstcard.py`
- **Upload Infrastructure:** `backend/src/api/ingest.py`
- **Database Schema:** `invoice_documents`, `invoice_lines`, `unified_files`

### 1.2 Current Frontend
- **CompanyCard Page:** `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`
- **Upload Pattern:** `UploadModal` component in `main-system/app-frontend/src/ui/pages/Process.jsx`

---

## 2. Technical Requirements

(This section remains unchanged from v1.0)

### 2.1 High-Level Flow
The overall data flow remains the same, from user upload to final matching, involving OCR, AI extraction, and database updates.

### 2.2 Data Flow Diagram
The diagram from v1.0 is still accurate.

---

## 3. Database Schema Changes

### 3.1 New and Enhanced Fields
The following enhancements will be made to the database schema.

**unified_files:**
```sql
ALTER TABLE unified_files
ADD COLUMN IF NOT EXISTS invoice_match_status VARCHAR(32) NULL COMMENT 'Status for invoice matching: pending, matched, unmatched, reviewed',
ADD COLUMN IF NOT EXISTS matched_invoice_id VARCHAR(36) NULL COMMENT 'Reference to invoice_documents.id if matched to invoice line';
```

**invoice_documents:**
```sql
ALTER TABLE invoice_documents
ADD COLUMN IF NOT EXISTS source_file_id VARCHAR(36) NULL COMMENT 'Reference to unified_files.id for uploaded PDF/image',
ADD COLUMN IF NOT EXISTS processing_status VARCHAR(32) DEFAULT 'uploaded' COMMENT 'uploaded, ocr_pending, ocr_done, ai_processing, ready_for_matching, matching_completed, completed, failed';
```

**invoice_lines:**
```sql
ALTER TABLE invoice_lines
ADD COLUMN IF NOT EXISTS extraction_confidence FLOAT NULL COMMENT 'AI confidence for extracted data (0-1)',
ADD COLUMN IF NOT EXISTS ocr_source_text TEXT NULL COMMENT 'Original OCR text that was parsed';
```

### 3.2 Migration Script
A new migration script will be created. It will be assigned the **next available sequence number** in the `database/migrations/` directory to prevent conflicts. For example: `0026_invoice_matching_enhancements.sql`.

The script will include the `ALTER TABLE` statements above, along with necessary indexes for performance:
```sql
CREATE INDEX IF NOT EXISTS idx_unified_invoice_match ON unified_files(invoice_match_status);
CREATE INDEX IF NOT EXISTS idx_invoice_docs_processing ON invoice_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_invoice_docs_source ON invoice_documents(source_file_id);
```

---

## 4. Backend Implementation

### 4.1 New API Endpoints
The following endpoints will be implemented or enhanced in `backend/src/api/reconciliation_firstcard.py`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai/api/reconciliation/firstcard/upload-invoice` | Upload PDF/image invoice. |
| GET | `/ai/api/reconciliation/firstcard/invoices/{id}/status` | Get processing status with detailed progress. |
| GET | `/ai/api/reconciliation/firstcard/invoices/{id}/lines` | Get extracted lines with matches. |

### 4.2 Upload Handler Implementation (`upload-invoice`)
The implementation of the upload endpoint will **prioritize code reuse and maintainability**.

- **Centralized Logic:** Instead of duplicating file handling logic, the endpoint will use **shared helper functions from `backend/src/api/ingest.py`** and `backend/src/services/storage.py`. This ensures that hash-based duplicate checks, file type detection, and storage operations are consistent across the application.
- **Efficient File Writes:** To prevent redundant I/O operations, the process will be optimized. The `pdf_to_png_pages` function will write page images to their final destination. The upload handler will then receive the paths to these generated files and create the database records (`unified_files`) without reading and re-writing the image data.
- **Orchestration:** The endpoint's primary responsibility is to orchestrate the process:
    1.  Invoke shared helpers to validate and store the uploaded file.
    2.  If it's a PDF, call `pdf_to_png_pages` for conversion.
    3.  Create the parent `invoice` and child `invoice_page` records in `unified_files`.
    4.  Create the initial `invoice_documents` record with `processing_status='ocr_pending'`.
    5.  Trigger the OCR processing task(s).

### 4.3 OCR and AI Task Chain (`tasks.py`)

#### 4.3.1 OCR Task Enhancement (`process_ocr`)
The existing `process_ocr` task will be enhanced to act as a router.
- **Branching Logic:** It will inspect the `file_type` of the processed file.
    - If `file_type` is `receipt` (or similar), it will proceed with the existing receipt-to-AI pipeline.
    - If `file_type` is `invoice_page`, it will **not** trigger the receipt pipeline. Instead, it will update its status and check if all other pages for the same invoice are complete.
- **Completion Hook:** When the last page of an invoice has been processed, this task will trigger the new, dedicated `process_invoice_ai_extraction` task for the parent invoice ID.

#### 4.3.2 Multi-Page Orchestration
For multi-page PDFs, the system will use **Celery's coordination primitives (e.g., groups or chords)**. This allows all pages of an invoice to be sent for OCR processing in parallel, significantly reducing the total wall-clock time for large documents. The Celery workflow will be designed to automatically trigger the final aggregation step (`process_invoice_ai_extraction`) once all parallel OCR tasks have successfully completed.

#### 4.3.3 AI Extraction Task (`process_invoice_ai_extraction`)
This new Celery task will:
1.  Aggregate all `ocr_raw` text from the child `invoice_page` records.
2.  Call the AI service (`invoice_ai.py`) to extract structured data.
3.  Populate the `invoice_lines` table with the extracted transactions.
4.  Update the `invoice_documents` record with period dates and set `processing_status='ready_for_matching'`.
5.  Trigger the `process_invoice_matching` task.

#### 4.3.4 Processing Status Lifecycle

The helper module `backend/src/services/invoice_status.py` codifies the state
machine for invoice reconciliation. The transitions are enforced in the Celery
tasks and Flask endpoints via atomic `UPDATE ... WHERE current_state` queries.

| Column | States | Notes |
|--------|--------|-------|
| `invoice_documents.processing_status` | `uploaded → ocr_pending → ocr_done → ai_processing → ready_for_matching → matching_completed → completed` (with `failed` reachable from any step) | Manual JSON imports are allowed to skip directly from `uploaded` to `ready_for_matching`. |
| `invoice_documents.status` | `imported → matching → matched/partially_matched → completed` (`failed` available from any intermediate step) | Business-facing flag used by the dashboard. |
| `invoice_lines.match_status` | `pending → auto/manual → confirmed` or `pending → unmatched/ignored` | Transitions are logged in `invoice_line_history`. |

Illegal transitions increment the Prometheus counter
`mind_invoice_state_assertions_total` so that operations can alert on race
conditions or unexpected task ordering.

### 4.4 AI Service for Invoice Extraction (`invoice_ai.py`)
A new service will be created at `backend/src/services/invoice_ai.py`. It will contain the logic for prompting a large language model (e.g., GPT-4o-mini) to parse the raw OCR text and return structured JSON. It will also include a **fallback mechanism using regular expressions** to ensure basic functionality even if the AI service is unavailable or fails.

### 4.5 Unified Matching Task (`process_invoice_matching`)
The enhanced matching logic (combining exact date/amount matches with fuzzy merchant name similarity) will be **consolidated into the primary, existing matching service**.
- **Code Consolidation:** The new algorithm will be integrated into the logic that powers the existing `/ai/api/reconciliation/firstcard/match` endpoint. This avoids having two separate matching implementations.
- **Expanded Scope:** The service will be updated to handle `invoice_type='credit_card_invoice'` in addition to legacy statement types.
- **Status Updates:** This task is responsible for the final status updates, setting `invoice_lines.match_status` and `unified_files.invoice_match_status`, and finally updating the parent `invoice_documents.status` to `completed` or `partially_matched`.

---

## 5. Frontend Implementation

(This section remains largely unchanged from v1.0, as the component structure is sound. The implementation will connect to the refined backend endpoints.)

- **`CompanyCard.jsx`:** Will be enhanced with an "Upload Invoice" button that opens the new modal.
- **`InvoiceUploadModal.jsx`:** A new component for file upload, which will poll the `/invoices/{id}/status` endpoint to show detailed, real-time progress to the user (OCR progress, AI status, match counts).
- **`InvoiceLinesModal.jsx`:** A new component to display the extracted and matched transaction lines for a selected invoice.

---

## 6. Testing Strategy

All testing will adhere to the project's established conventions as defined in `docs/TEST_RULES.md` and `web/TEST_AGENT_INSTRUCTIONS.md`.

- **Unit Tests:** New tests for the regex fallback, merchant similarity, and state transition logic.
- **Integration Tests:** Backend tests covering the entire upload-to-match flow. Test fixtures will be stored under `web/test/` and reports under `web/test-results/`.
- **E2E Tests:** New Playwright tests will be created in the correct location: `web/tests/e2e-invoice-upload.spec.ts`. These tests will cover the full user journey from login, upload, and progress polling, to verifying the result.

---

## 7. Deployment & Migration

(This section remains unchanged from v1.0, with the understanding that the migration script will have the correct, sequential name.)

---

## 8. Future Enhancements

(This section remains unchanged from v1.0)

---

## 9. Risk Analysis & Mitigation

(This section remains unchanged from v1.0)

---

## 10. Success Criteria

(This section remains unchanged from v1.0)

---

## 11. Appendix

(This section remains unchanged from v1.0, with file paths updated to reflect the correct test locations.)

---

## 12. Parallel Implementation Guide for Agents

To maximize efficiency, the work has been broken down into tasks that can be parallelized. The following guide outlines task dependencies, enabling multiple agents to work on different branches simultaneously.

**Prerequisite for All Phases:**
- The `MIND_INVOICE_MATCH_IMPLEMENTATION_PLAN_v1.1.md` (this document) should be reviewed by all participating agents.

---

### **Phase 1: Backend Foundations (Sprint 1.1)**

| Task ID | Task Description | Can be Parallelized? | Dependencies & Notes |
|---|---|---|---|
| **1.1.3** | **Align DB Schema & Migration** | **No** | **BLOCKER.** This must be completed first. The final SQL migration script must be defined and agreed upon before any other backend task can be completed. |
| **1.1.1** | **Implement API Endpoints** | **Yes** | Depends on **1.1.3**. Can be developed in a separate branch once the DB schema is finalized. Can run in parallel with 1.1.2. |
| **1.1.2** | **Define Status Lifecycle** | **Yes** | Depends on **1.1.3**. This involves creating helper functions for state transitions. Can be developed in parallel with 1.1.1. |

**Workflow:**
1.  Agent A: Complete **Task 1.1.3**. Create a branch `feature/invoice-db-migration`. Merge to main when done.
2.  Once merged, Agent B can start **Task 1.1.1** on a new branch `feature/invoice-api-endpoints`, and Agent C can start **Task 1.1.2** on `feature/invoice-status-logic`.

---

### **Phase 2: Processing Pipeline (Sprint 2.1)**

| Task ID | Task Description | Can be Parallelized? | Dependencies & Notes |
|---|---|---|---|
| **2.1.1** | **Branch OCR Pipeline** | **No** | Depends on Phase 1. These tasks are tightly coupled and modify the core Celery workflow. It's safest for a single agent to handle this entire phase to ensure integrity. |
| **2.1.2** | **Optimize OCR Orchestration** | **No** | See above. Part of the same core logic change. |
| **2.1.3** | **Avoid Duplicate File Writes** | **No** | See above. Directly related to the orchestration logic. |

**Workflow:**
1.  Agent A (or a new agent): After Phase 1 is merged, create a branch `feature/invoice-processing-pipeline` and implement all three tasks sequentially.

---

### **Phase 3: Matching & Data Surfacing (Sprint 3.1)**

| Task ID | Task Description | Can be Parallelized? | Dependencies & Notes |
|---|---|---|---|
| **3.1.1** | **Merge Enhanced Matching** | **Yes** | Depends on Phase 1. Can be worked on as soon as the DB schema is ready. Can run in parallel with Phase 2 and 4. |
| **3.1.2** | **Deliver Performant Status Polling** | **Yes** | Depends on Phase 1. Involves optimizing SQL queries for the status endpoint. Can run in parallel with other tasks. |

**Workflow:**
1.  Agent B can work on **Task 3.1.1** in a branch `feature/invoice-unified-matching`.
2.  Agent C can work on **Task 3.1.2** in a branch `feature/invoice-status-performance`.

---

### **Phase 4: Frontend Experience (Sprint 4.1)**

| Task ID | Task Description | Can be Parallelized? | Dependencies & Notes |
|---|---|---|---|
| **4.1.1** | **Integrate Upload Modal & Polling** | **Yes** | Depends on the API contract from **Task 1.1.1**. Can start as soon as the API endpoints are defined (even if not fully implemented) by using a mock server. Can run in parallel with all backend work (Phase 2 & 3). |

**Workflow:**
1.  Agent D can start on the frontend work in a branch `feature/invoice-frontend-ux` as soon as the API specification is clear.

---

### **Phase 5: Quality & Documentation (Sprint 5.1)**

| Task ID | Task Description | Can be Parallelized? | Dependencies & Notes |
|---|---|---|---|
| **5.1.1** | **Restructure Test Suites** | **Yes** | Administrative task. Can be done at any time by any agent. |
| **5.1.2** | **Expand Automated Coverage** | **Partially** | Writing test *cases* can be done in parallel with development. *Executing* the tests requires the features to be merged. |
| **5.1.3** | **Operational Readiness Checks** | **Yes** | Can be done in parallel. Involves updating dashboards and writing documentation. |

**Summary of Parallel Execution:**
- **Path A (DB -> API -> Frontend):** Agent A (DB) -> Agent B (API) -> Agent D (Frontend)
- **Path B (Core Processing):** Agent A (DB) -> Agent C (Processing Pipeline)
- **Path C (Matching & Optimization):** Agent A (DB) -> Agent E (Matching/Polling)

This allows for significant parallel workstreams after the initial database migration is defined.
