# docs/source_of_truth/30_STATUS_MODEL.md

# Mind – Status Model (Source of Truth)

> This file defines **all** status fields and allowed values used in Mind. If a status value appears in code or database but is not described here, it must be added or removed.

## 1. Overview

Mind uses multiple status dimensions to track processing and workflow, including (names may correspond to DB columns):

- **Processing status** – technical pipeline progress for a unified file/receipt/invoice.
- **Document status** – business/UX state for a document as seen by users.
- **Match status** – matching state between receipts and card transactions.
- **AI step statuses** – per AI stage (AI1–AI7 and similar) success/error markers.

This section will be incrementally aligned with the actual database schema and code. Until then, existing status docs (e.g. `docs/MIND_STATUS_DEFINITIONS.md`, `docs/MIND_STATUS_TRANSITIONS.md`, `docs/RECEIPT_STATUS_FLOW.md`) are treated as **legacy** and must be reconciled into this file.

## 2. Processing Status

### 2.1 Field

- Working name: `processing_status` (exact column names per table are listed in `40_DATA_MODEL.md`).

### 2.2 Allowed Values (Technical Pipeline)

Illustrative model – must be validated and aligned with actual DB and code during consolidation:

- `imported` – File is stored but not yet processed.
- `queued_for_ocr` – Waiting for OCR/transcription.
- `ocr_in_progress` – OCR/transcription running.
- `ocr_failed` – OCR/transcription failed; requires manual attention or retry.
- `extracted` – Text extracted successfully.
- `ai_classified` – Document type determined.
- `ai_extracted` – Structured data (amounts, dates, merchant, etc.) extracted.
- `ai_proposed` – Accounting proposal created.
- `ready_for_review` – Pipeline done; awaiting human review.
- `exported` – Document included in an export.
- `archived` – Final state, no further processing.

> TODO: Fill in exact values and mapping per entity (Unified File, Receipt, Invoice, Card Transaction) based on current DB and code.

## 3. Document Status

Represents business-level state visible in the UI.

Typical values (to be cross-checked against actual implementation):

- `new` – Newly created/ingested, not yet opened.
- `in_review` – User is working on this document.
- `awaiting_information` – Missing data, user needs to provide details.
- `approved` – Approved for export.
- `rejected` – Rejected or invalid.

> TODO: Confirm actual values and exact column names (e.g., `document_status`, `review_status`) and reconcile with historical docs.

## 4. Match Status

Describes the status of matching between a Receipt and a Card Transaction.

Possible values (to be aligned with DB):

- `unmatched` – No candidate match.
- `candidate_found` – System has proposed one or more potential matches.
- `matched_auto` – System automatically matched with high confidence.
- `matched_manual` – User manually confirmed the match.
- `mismatch` – Match attempt failed or was explicitly rejected.

## 5. AI Step Statuses

Each AI step (AI1–AI7 etc.) should have a clear status flag and, where applicable, an error model.

Examples:

- `ai1_status`: `pending`, `running`, `success`, `error`.
- `ai2_status`: same pattern.

Error details should be stored in a structured way (e.g., error code, message, raw response snippet) to support debugging and analytics.

## 6. State Transition Rules

For each status dimension, state transitions **must** be documented as state diagrams or tables.

> TODO: Import and consolidate existing diagrams from:
>
> - `docs/MIND_PROCESS_IMPORT_STATUS_DIAGRAM.md`
> - `docs/PROCESS_IMPORT_STATUS_DIAGRAM.md`
> - `docs/RECEIPT_STATUS_FLOW.md`
> - `docs/MIND_STATUS_TRANSITIONS.md`

When fully consolidated, this section will contain one diagram per main entity:

- Unified File
- Receipt
- Invoice
- Card Transaction

## 7. Governance

- New status values may not be introduced in code or database without updating this file.
- Deprecated values must be explicitly noted with migration plan.