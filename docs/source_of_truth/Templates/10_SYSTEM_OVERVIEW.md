# docs/source_of_truth/10_SYSTEM_OVERVIEW.md

# Mind – System Overview (Source of Truth)

## 1. Purpose and Goals

Mind is a system for ingesting, processing and preparing bookkeeping data based on:

- Receipts (uploaded via UI or collected from email/FTP)
- Invoices and other financial documents
- Credit card statements/FirstCard-like exports

Key goals:

- Reduce manual work for entrepreneurs and accountants.
- Provide transparent, auditable processing of documents.
- Automate classification, data extraction and accounting proposal generation with AI.
- Safely match receipts to card transactions and prepare export files to the accounting system.

## 2. Primary User Roles

- **Business Owner / End User**  
  Uploads receipts, reviews suggested accounting, adds missing information.

- **Accountant / Bookkeeper**  
  Reviews and approves accounting proposals, handles edge cases, exports data to external accounting systems.

- **System Operator / Admin**  
  Monitors pipelines, handles configuration, investigates errors.

- **Developer / Maintainer**  
  Extends features, maintains integrations and pipelines.

## 3. High-Level Architecture

Mind is structured around the following main components (names follow the repository layout):

- **Frontend/Web UI**  
  A web interface where users can:
  - View and upload documents
  - Track processing statuses
  - Review AI proposals and matches

- **Backend API**  
  Handles:
  - REST/HTTP endpoints for the UI and integrations
  - Orchestration of document processing
  - Database access and status updates

- **Workers / Pipelines**  
  Background processes that run:
  - File import (FTP/email/watch folders)
  - OCR and audio/video transcription
  - AI classification and extraction (AI1–AI7 or similar chain)
  - Matching receipts ↔ card transactions
  - Export to accounting system.

- **Database (MySQL)**  
  - Central relational database containing:
    - Companies, projects, users
    - Unified file storage (metadata for all imported artifacts)
    - Receipts, invoices, card transactions
    - AI outputs (classification, extracted fields, accounting proposals)
    - Processing and match statuses

- **External Services**  
  - OCR/Whisper transcription
  - AI APIs (OpenAI / local models via Ollama or similar)
  - External banking/credit card sources
  - External accounting/export formats.

## 4. Core Use Cases

1. **Import of raw documents**
   - Files are fetched from FTP/email or uploaded via UI.
   - Files are normalized into a unified file model in the database.

2. **OCR / Transcription and Extraction**
   - PDFs/images/videos are transformed into machine-readable text.
   - AI services extract structured fields (date, amount, VAT, merchant, etc.).

3. **Classification and Accounting Proposals**
   - AI determines document type (receipt, invoice, credit card statement, etc.).
   - AI generates accounting proposals based on Swedish rules (BAS 2025, VAT).

4. **Matching Against Credit Card Transactions**
   - Receipts are matched to card transactions using amount, date, merchant and metadata.
   - Status fields indicate match confidence and workflow state.

5. **Review and Export**
   - Users review and adjust.
   - Data is exported in formats suitable for the target accounting system.

## 5. Relationship to Other Docs

This overview is the canonical summary of what Mind is and what it does. For more details:

- Domain concepts → `20_DOMAIN_MODEL_AND_GLOSSARY.md`
- Status fields and workflows → `30_STATUS_MODEL.md`
- Database schema → `40_DATA_MODEL.md`
- Pipelines and AI flows → `50_PIPELINES_AND_JOBS.md`
- Integrations → `60_INTEGRATIONS.md`