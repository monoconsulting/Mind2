# Mind Workflow Redesign

This document outlines the redesigned workflow architecture for asynchronous processing, implemented to ensure robust separation between different ingestion channels and provide clear observability.

## Core Principles

1.  **Workflow-First:** Every file upload immediately creates a `workflow_runs` record, which acts as the single source of truth for that file's processing journey.
2.  **Explicit Dispatch:** A central `dispatch_workflow` function routes the `workflow_run` to the correct Celery task chain based on its `workflow_key`.
3.  **Granular & Chained Tasks:** Large, monolithic tasks are broken down into smaller, single-responsibility tasks connected via Celery `chains` and `chords`.
4.  **Safety Guards:** Every workflow task is protected by an `ensure_workflow` guard to prevent cross-execution between different workflow types.
5.  **Detailed Logging:** Every step in a workflow is recorded as a `workflow_stage_runs` record, providing a clear, auditable trail of the process.

---

## Workflow 1: `WF1_RECEIPT` (Image-Based Receipt)

This workflow handles the standard processing of single-image receipts.

The process runs in the following order:

1.  **API: File Ingestion (`/ingest/upload`)**
    *   An image file is received by the `upload_files` function.
    *   A `unified_files` record is created for the image.
    *   A `workflow_runs` record is created with `workflow_key = 'WF1_RECEIPT'`.
    *   The `dispatch_workflow()` function is called with the new `workflow_run_id`.

2.  **Dispatcher (`dispatch_workflow`)**
    *   The dispatcher receives the `workflow_run_id`.
    *   It identifies the `workflow_key` as `'WF1_RECEIPT'`.
    *   A Celery `chain` is created and started asynchronously: `wf1_run_ocr` -> `wf1_run_ai_pipeline` -> `wf1_finalize`.

3.  **Celery Task 1: `wf1_run_ocr`**
    *   **Guard:** Verifies it's running for a `WF1_*` workflow.
    *   **Logging:** Sets the `'ocr'` stage status to `'running'`.
    *   **Work:** Executes the OCR process on the image file.
    *   **Logging:** Updates the `'ocr'` stage status to `'succeeded'` or `'failed'`.
    *   **Output:** Passes the `workflow_run_id` to the next task.

4.  **Celery Task 2: `wf1_run_ai_pipeline`**
    *   **Guard & Check:** Verifies it's a `WF1_*` workflow and that the previous `'ocr'` stage succeeded.
    *   **Logging:** Sets the `'ai_pipeline'` stage to `'running'`.
    *   **Work:** Executes the full AI pipeline (AI1-AI4) for receipt analysis.
    *   **Logging:** Updates the `'ai_pipeline'` stage to `'succeeded'` or `'failed'`.
    *   **Output:** Passes the `workflow_run_id` to the final task.

5.  **Celery Task 3: `wf1_finalize`**
    *   **Guard & Check:** Verifies it's a `WF1_*` workflow and that the `'ai_pipeline'` stage succeeded.
    *   **Work:** Sets the final, overall status of the `workflow_runs` record to `'succeeded'` or `'failed'`.
    *   **Logging:** Records its own `'finalize'` stage status.
    *   **End:** The workflow is complete.

---

## Workflow 2: `WF2_PDF_SPLIT` (PDF-Based Invoice)

This workflow is more advanced, designed to handle multi-page PDF documents by splitting them and processing the pages in parallel.

The process runs in the following order:

1.  **API: File Ingestion (`/ingest/upload`)**
    *   A PDF file is received.
    *   A single `unified_files` record is created for the entire PDF document.
    *   A `workflow_runs` record is created with `workflow_key = 'WF2_PDF_SPLIT'`.
    *   `dispatch_workflow()` is called.

2.  **Dispatcher (`dispatch_workflow`)**
    *   Identifies the workflow as `'WF2_PDF_SPLIT'`.
    *   Starts **only the first task** in the workflow: `wf2_prepare_pdf_pages`. The rest of the flow is orchestrated from within the tasks themselves.

3.  **Celery Task 1: `wf2_prepare_pdf_pages`**
    *   **Guard:** Verifies `WF2_*` workflow.
    *   **Logging:** Sets `'prepare_pages'` stage to `'running'`.
    *   **Work:** Splits the source PDF into a series of PNG images. For each page, a new `unified_files` record (type `pdf_page`) is created and linked to the original PDF.
    *   **Logging:** Sets `'prepare_pages'` stage to `'succeeded'`.
    *   **Orchestration:** Creates and executes a **Celery Chord**. This consists of:
        *   A **group** of `wf2_run_page_ocr` tasks that run **in parallel** (one for each page).
        *   A **callback** task, `wf2_merge_ocr_results`, which is configured to run only after all parallel OCR tasks are complete.

4.  **Celery Task 2 (Parallel Group): `wf2_run_page_ocr`**
    *   This task executes concurrently for every page of the PDF.
    *   **Logging:** Each task logs its progress against a dynamic stage key (e.g., `ocr_page_1`, `ocr_page_2`).
    *   **Work:** Runs OCR on its assigned page image.
    *   **Output:** Returns the extracted text for its page.

5.  **Celery Task 3 (Chord Callback): `wf2_merge_ocr_results`**
    *   This task runs only after **all** parallel `wf2_run_page_ocr` tasks have finished.
    *   **Logging:** Sets `'merge_ocr'` stage to `'running'`.
    *   **Work:** Collects the text results from all the page tasks and combines them into a single text block. This combined text is saved to the database record of the original PDF.
    *   **Logging:** Sets `'merge_ocr'` stage to `'succeeded'`.
    *   **Orchestration:** Triggers the next task in the sequence: `wf2_run_invoice_analysis`.

6.  **Celery Task 4: `wf2_run_invoice_analysis`**
    *   **Guard:** Verifies `WF2_*` workflow.
    *   **Logging:** Sets `'invoice_analysis'` stage to `'running'`.
    *   **Work:** Fetches the combined OCR text and executes the invoice-specific AI analysis (parsing lines, etc.).
    *   **Logging:** Updates stage to `'succeeded'` or `'failed'`.
    *   **Orchestration:** Triggers the final task: `wf2_finalize`.

7.  **Celery Task 5: `wf2_finalize`**
    *   **Work:** Sets the final status (`'succeeded'` or `'failed'`) for the entire PDF workflow in the `workflow_runs` table.
    *   **End:** The workflow is complete.

---

## Workflow 3: `WF3_FIRSTCARD_INVOICE` (Credit Card Invoice)

This workflow is a specialized version of `WF2` designed to handle First Card credit card statements. It relies on the `workflow_type` field to correctly route the document for specialized AI processing and data persistence.

1.  **API: File Ingestion & Routing**
    *   A file (typically a PDF) is uploaded from a specific UI context (e.g., the "Kortmatchning" page).
    *   The backend creates a `unified_files` record and sets its `workflow_type` to `'creditcard_invoice'`.
    *   A `workflow_runs` record is created. The `workflow_key` might be `WF2_PDF_SPLIT` (if it's a PDF) or a dedicated `WF3_FIRSTCARD_INVOICE`. The `workflow_type` is the critical piece for downstream logic.
    *   The workflow proceeds similarly to `WF2`, with page splitting and parallel OCR if it's a multi-page PDF.

2.  **Celery Task: `wf3_run_ai6_analysis_and_persist`**
    *   This task runs after all OCR text has been merged.
    *   **Guard:** Verifies the `workflow_type` is `'creditcard_invoice'`.
    *   **Logging:** Sets a stage like `'ai6_analysis'` to `'running'`.
    *   **Work:** This is a multi-step process for parsing the invoice and populating the database:
        1.  **AI Analysis (AI6):** The combined OCR text is sent to a specialized AI model (AI6), which is trained to understand the structure of First Card statements. The AI returns a structured JSON object containing:
            *   **`header`**: Main invoice details (invoice number, total amount, etc.).
            *   **`lines`**: A list of all individual transaction rows.
        2.  **Populate `creditcard_invoices_main`:** The `header` data is used to perform an "upsert" operation. The system checks if an invoice with that `invoice_number` already exists. If so, it's updated; otherwise, a new row is inserted. The ID of this row (`main_id`) is retained.
        3.  **Populate `creditcard_invoice_items`:** The `lines` data and the `main_id` are used to populate the transaction items. To prevent duplicates and ensure data integrity, the system first **deletes** all existing items for that `main_id` before performing a bulk **insert** of the new transaction lines from the AI's response.
    *   **Logging:** The stage is updated to `'succeeded'` or `'failed'`.
    *   **Orchestration:** Triggers the finalization task.

3.  **Celery Task: `wf3_finalize`**
    *   **Work:** Sets the final status (`'succeeded'` or `'failed'`) for the entire workflow in the `workflow_runs` table.
    *   **End:** The workflow is complete.