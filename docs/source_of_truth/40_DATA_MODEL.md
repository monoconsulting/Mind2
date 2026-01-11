# docs/source_of_truth/40_DATA_MODEL.md

# Mind – Data Model (Source of Truth)

> This file describes the canonical database schema used by Mind. For full migration history, see the `database/migrations` directory. This document focuses on the **current target model**, not each historical step.
>
> The database schema is not considered valid or “live” unless it is fully reflected in this document.
>  Any new table/column/index or change in type/meaning **must** be added here in the same pull request.

## 1. Overview

Mind uses a relational database (MySQL) as its primary data store.

Key areas:

- **Core business entities** – Companies, Projects, Users.
- **Document ingestion** – Unified Files, raw document metadata.
- **Accounting artifacts** – Receipts, Receipt Items, Invoices, Card Transactions.
- **AI artifacts** – AI processing logs, extracted fields, accounting proposals.
- **Status and workflow** – Status fields as defined in `30_STATUS_MODEL.md`.

## 2. Tables (High-Level)

> NOTE: This is an initial high-level structure. Detailed column-level definitions will be added and kept in sync with `database/migrations` and actual schema.

### 2.1 Company Table

- Stores each customer company.
- Key columns: id, organisation_number, name, contact info, settings.

### 2.2 Project Table

- Linked to Company.
- Key columns: id, company_id, name, description, status.

### 2.3 Unified Files Table

- Represents all imported files.
- Key columns (indicative): id, company_id, project_id, source_channel, original_filename, stored_path, mime_type, created_at, processing_status.

### 2.4 Receipts and Receipt Items Tables

- **Receipts** – one row per receipt.
- **Receipt Items** – zero or more items per receipt.

Key columns include:

- Receipts: id, unified_file_id, company_id, project_id, date, total_amount, currency, vat_total, document_status, processing_status, match_status, ai_proposal_id.
- Receipt Items: id, receipt_id, description, quantity, unit_price, vat_rate, account_suggestion.

### 2.5 Invoices Table

- One row per supplier invoice.
- Key columns: id, unified_file_id, company_id, project_id, supplier_name, invoice_number, invoice_date, due_date, total_amount, vat_total, processing_status, document_status.

### 2.6 Card Transactions Table

- Imported from card statement exports.
- Key columns: id, company_id, card_holder, transaction_date, posting_date, amount, currency, merchant_name, external_reference, match_status.

### 2.7 Accounting Proposals Table

- Stores AI-generated booking suggestions.
- Key columns: id, company_id, project_id, source_entity_type, source_entity_id, json_payload, status, created_at.

### 2.8 AI Logs / AI Steps Tables

- Tables recording input/output for AI1–AI7 and similar.
- Key columns: id, step_name, entity_type, entity_id, request_payload, response_payload, status, error_code, error_message, created_at.

## 3. Relationships

- Company 1–N Project
- Company 1–N Unified File
- Company 1–N Receipt / Invoice / Card Transaction
- Unified File 1–1 or 1–N Receipt / Invoice (depending on how many documents per file)
- Receipt 1–N Receipt Items
- Receipt 0–1 Accounting Proposal
- Invoice 0–1 Accounting Proposal
- Receipt 0–1 Card Transaction (match)

## 4. Indexing and Performance

> TODO: Extract actual index definitions from the current schema and document them here, especially:
>
> - Status and date fields used for batch selection
> - Foreign key constraints
> - Text search / full-text/JSON fields used for queries

## 5. Alignment with Migrations

- This document should match the latest schema after migrating all `database/migrations` files.
- Any new table or structural change must be reflected here.