# docs/source_of_truth/50_PIPELINES_AND_JOBS.md

# Mind – Pipelines and Jobs (Source of Truth)

> This file documents all major technical pipelines and scheduled jobs in Mind. It focuses on **what** each pipeline does and **how data flows**, not implementation details.

## 1. Overview of Pipelines

Mind’s processing can be grouped into the following pipelines:

1. **Ingestion Pipeline** – Getting files and data into Mind.
2. **OCR / Transcription Pipeline** – Converting files to machine-readable text.
3. **AI Classification and Extraction Pipeline** – Determining document type and extracting structured data.
4. **Accounting Proposal Pipeline** – Generating proposed bookings.
5. **Matching Pipeline** – Matching receipts with card transactions.
6. **Export Pipeline** – Exporting approved data to external accounting systems.

## 2. Ingestion Pipeline

### 2.1 Triggers

- Scheduled imports from FTP/IMAP.
- Manual uploads via web UI.
- Potential API-based submissions.

### 2.2 Steps (Logical)

1. Detect new files in source (FTP, email attachment, upload).
2. Store file in internal storage.
3. Create `Unified File` record in database.
4. Set initial `processing_status` (e.g. `imported`).
5. Enqueue file for OCR/Transcription depending on file type.

## 3. OCR / Transcription Pipeline

### 3.1 Scope

- Images/PDFs → text via OCR.
- Audio/video → text via Whisper or similar.

### 3.2 Steps

1. Select `Unified Files` requiring OCR/transcription.
2. Send to configured OCR/Whisper service.
3. Store raw text output.
4. Update `processing_status` (e.g. `extracted`) or `ocr_failed` on error.
5. Enqueue for AI classification and extraction.

## 4. AI Classification and Extraction Pipeline

### 4.1 Responsibilities

- Determine document type (receipt, invoice, card statement, other).
- Extract structured fields (dates, amounts, VAT, merchant, etc.).

### 4.2 Steps

1. Take OCR/transcription output as input.
2. Run AI steps (e.g. AI1/AI2) with defined prompts.
3. Parse and validate AI response.
4. Populate Receipts/Invoices + items.
5. Record AI logs and status.
6. Update relevant status fields to reflect progress.

## 5. Accounting Proposal Pipeline

### 5.1 Responsibilities

- Generate complete accounting proposals aligned with Swedish rules (BAS 2025, VAT).

### 5.2 Steps

1. Select receipts/invoices ready for accounting proposal.
2. Run AI step (e.g. AI4) with necessary context (BAS kontoplan, company config, history if applicable).
3. Store proposal in `Accounting Proposals` table.
4. Update status to indicate that proposal is ready for review.

## 6. Matching Pipeline (Receipts ↔ Card Transactions)

### 6.1 Scope

- Match receipts to card transactions based on amount, date, merchant and metadata.

### 6.2 Steps

1. Import card transactions from provider exports.
2. For each transaction, find candidate receipts.
3. Use rules/AI to score and select best match.
4. Update `match_status` and relationships.
5. Allow manual overrides from UI.

## 7. Export Pipeline

### 7.1 Responsibilities

- Prepare data for export into accounting systems.

### 7.2 Steps

1. Select all `approved` receipts/invoices/proposals.
2. Transform into target export format.
3. Generate export files.
4. Mark exported entities with `exported` status and reference ID.

## 8. Scheduling and Jobs

> TODO: Document actual cron/scheduler configuration and job names as implemented (e.g. in `backend` or `infra` scripts), including:
>
> - Frequency of FTP/email imports
> - Frequency of matching and export jobs
> - Any maintenance/cleanup jobs