# docs/source_of_truth/20_DOMAIN_MODEL_AND_GLOSSARY.md

# Mind – Domain Model and Glossary (Source of Truth)

> This file defines all domain concepts used in Mind and how they relate. If a business term appears in code or UI but is not described here, it must be added.

## 1. Overview

Mind is an AI-powered document processing system for Swedish accounting. The domain model centers on financial documents (receipts, invoices, credit card statements) being processed through AI pipelines to produce accounting proposals.

## 2. Core Domain Concepts

### 2.1 Company

A legal entity (Swedish: företag) that owns documents and accounting data.

**Database Table:** `companies`
**Key Fields:**
- `id` – Primary key
- `name` – Company name
- `orgnr` – Swedish organization number (organisationsnummer)
- `address`, `address2`, `zip`, `city`, `country` – Address fields
- `phone`, `www`, `email` – Contact information

**Relationships:**
- Company 1–N Unified Files
- Company 1–N Receipts
- Company 1–N Credit Card Statements

### 2.2 Unified File

The central entity representing any document imported into Mind.

**Database Table:** `unified_files`
**Key Fields:**
- `id` – UUID primary key
- `company_id` – FK to companies
- `file_type` – Document type (e.g., `image/jpeg`, `application/pdf`)
- `workflow_type` – Processing workflow (`receipt`, `creditcard_invoice`)
- `original_filename` – Original file name
- `file_path` – Storage location
- `ocr_raw` – Extracted OCR text
- `ai_status` – Processing status
- `purchase_datetime` – Date of transaction
- `gross_amount`, `net_amount`, `vat_amount` – Financial amounts

**Note:** `merchant_name` does NOT exist in this table. Use `companies.name` via `company_id` JOIN.

### 2.3 Receipt

A financial document proving a transaction (Swedish: kvitto).

**Represented by:** `unified_files` with appropriate `workflow_type`
**Related Tables:**
- `receipt_items` – Line items on the receipt
- `ai_accounting_proposals` – Suggested accounting entries

**Key Fields (in unified_files):**
- `purchase_datetime` – When the purchase occurred
- `gross_amount` – Total including VAT
- `net_amount` – Total excluding VAT
- `vat_amount` – VAT amount
- `currency` – Currency code (SEK, EUR, etc.)

### 2.4 Receipt Item

A single line item on a receipt.

**Database Table:** `receipt_items`
**Key Fields:**
- `id` – Primary key
- `main_id` – FK to unified_files.id
- `name` – Item description
- `quantity` – Number of items
- `unit_price` – Price per unit
- `vat_rate` – VAT percentage (6%, 12%, 25%)
- `article_id` – Product/article identifier

### 2.5 Credit Card Statement (FirstCard Invoice)

A monthly statement from a credit card provider listing all transactions.

**Database Tables:**
- `creditcard_invoices_main` – Statement header
- `creditcard_invoices_lines` – Individual transactions
- `invoice_documents` – Document metadata
- `invoice_lines` – Line items for matching

**Key Concepts:**
- A statement contains multiple transaction lines
- Each line can be matched to a receipt
- Matching status tracked per line

### 2.6 Credit Card Transaction Line

A single transaction on a credit card statement.

**Database Table:** `creditcard_invoices_lines`
**Key Fields:**
- `id` – Primary key
- `main_id` – FK to creditcard_invoices_main
- `transaction_date` – Date of transaction
- `amount` – Transaction amount
- `merchant_name` – Where the transaction occurred
- `receipt_id` – Linked receipt (if matched)

### 2.7 Accounting Proposal

AI-generated suggestion for booking a financial transaction.

**Database Table:** `ai_accounting_proposals`
**Key Fields:**
- `id` – Primary key
- `receipt_id` – FK to unified_files.id
- `item_id` – FK to receipt_items.id (if item-level)
- `account_code` – BAS 2025 account number
- `debit` – Debit amount
- `credit` – Credit amount
- `vat_code` – VAT classification
- `confidence_score` – AI confidence (0-1)

### 2.8 Workflow Run

A single execution of a processing workflow for a document.

**Database Table:** `workflow_runs`
**Key Fields:**
- `id` – Primary key
- `workflow_key` – Workflow type (WF1_RECEIPT, WF2_PDF_SPLIT, WF3_FIRSTCARD_INVOICE)
- `file_id` – FK to unified_files.id
- `current_stage` – Current processing stage
- `status` – Execution status (queued, running, succeeded, failed, canceled)

### 2.9 Workflow Stage Run

A single stage within a workflow execution.

**Database Table:** `workflow_stage_runs`
**Key Fields:**
- `id` – Primary key
- `workflow_run_id` – FK to workflow_runs.id
- `stage_key` – Stage identifier (e.g., `r_ocr`, `r_ai3`, `fc_parse`)
- `status` – Stage status (queued, running, succeeded, failed, skipped)
- `started_at`, `finished_at` – Timing
- `message` – Status message

## 3. Workflow Types

### 3.1 WF1_RECEIPT

Standard receipt processing workflow.

**Stages:**
1. `src_portal` / `src_ftp` – Document source
2. `ingest_store` – Store file
3. `ingest_wf1` – Create workflow
4. `detect_type` – AI1: Document classification
5. `r_ocr` – OCR extraction
6. `r_ai3` – AI3: Data extraction
7. `r_ai4` – AI4: Accounting classification
8. `r_persist` – Save data
9. `r_queue_match` – Queue for matching
10. `finalize_ok` / `finalize_fail` – Complete

### 3.2 WF3_FIRSTCARD_INVOICE

Credit card statement processing workflow.

**Stages:**
1. `src_fc` – Upload statement
2. `fc_create` – Create invoice document
3. `fc_ocr` – OCR extraction
4. `fc_parse` – AI6: Parse statement
5. `fc_ready` – Ready for matching
6. `ai5` – Credit card matching
7. `m_found` / `m_link` / `m_unmatched` – Match results
8. `finalize_ok` – Complete

### 3.3 WF2_PDF_SPLIT

Multi-page PDF processing workflow.

**Stages:**
1. `dispatch` – Start workflow
2. `prepare_pages` – Split PDF into pages
3. `page_ocr` – OCR each page
4. `merge_ocr` – Combine results
5. `invoice_analysis` – Analyze content
6. `finalize` – Complete

## 4. Status Concepts

### 4.1 AI Status (`unified_files.ai_status`)

Overall processing state for a document:
- `uploaded` – Awaiting processing
- `processing` – Currently being processed
- `ocr_done` – OCR completed
- `ocr_failed` – OCR failed
- `manual_review` – Requires human review
- `completed` – Processing finished
- `failed` – Processing failed

### 4.2 Workflow Status (`workflow_runs.status`)

Execution state for a workflow:
- `queued` – Waiting to start
- `running` – Currently executing
- `succeeded` – Completed successfully
- `failed` – Execution failed
- `canceled` – Manually canceled

### 4.3 Match Status

State of receipt-to-transaction matching:
- `pending` – Not yet matched
- `auto` – Automatically matched
- `manual` – Manually matched
- `confirmed` – Match confirmed
- `unmatched` – No match found
- `ignored` – Intentionally skipped

## 5. Glossary

| Term | Swedish | Definition |
|------|---------|------------|
| Receipt | Kvitto | Proof of purchase transaction |
| Invoice | Faktura | Bill for goods/services |
| Credit Card Statement | Kreditkortsfaktura | Monthly card transaction summary |
| FirstCard | FirstCard | Specific credit card provider |
| OCR | OCR | Optical Character Recognition |
| BAS | BAS | Swedish chart of accounts standard |
| VAT | Moms | Value Added Tax (6%, 12%, 25%) |
| Org Number | Organisationsnummer | Swedish company registration number |
| Workflow | Arbetsflöde | Automated processing pipeline |
| Manual Review | Manuell granskning | Human review required |
| Matching | Matchning | Linking receipts to transactions |

## 6. Entity Relationship Diagram

```
┌─────────────┐      ┌─────────────────┐      ┌──────────────────┐
│  companies  │──1:N─│  unified_files  │──1:N─│  receipt_items   │
└─────────────┘      └─────────────────┘      └──────────────────┘
                            │
                           1:N
                            │
                     ┌──────┴──────┐
                     │             │
              ┌──────┴─────┐  ┌────┴────────────┐
              │workflow_runs│  │ai_accounting_   │
              └──────┬─────┘  │proposals         │
                    1:N       └──────────────────┘
                     │
          ┌──────────┴──────────┐
          │workflow_stage_runs  │
          └─────────────────────┘

┌─────────────────────────┐      ┌─────────────────────────┐
│creditcard_invoices_main │──1:N─│creditcard_invoices_lines│
└─────────────────────────┘      └─────────────────────────┘
              │
             1:1
              │
     ┌────────┴────────┐      ┌──────────────┐
     │invoice_documents│──1:N─│invoice_lines │
     └─────────────────┘      └──────────────┘
```

## 7. Governance

- New domain concepts must be added here before or together with implementation.
- Deprecated concepts should be marked with a note and migration path.
- All code and UI must use terminology consistent with this glossary.
