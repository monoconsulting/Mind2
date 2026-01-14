# docs/source_of_truth/60_INTEGRATIONS.md

# Mind – Integrations (Source of Truth)

> This file describes all external systems and services that Mind integrates with.

## 1. Overview

Mind interacts with several categories of external systems:

- **Input sources** – FTP, email/IMAP, manual upload.
- **OCR / Transcription** – OCR services, Whisper/OpenAI or local alternatives.
- **AI services** – OpenAI and/or local LLMs via API.
- **Card/Banking systems** – Corporate card exports (e.g. FirstCard).
- **Accounting systems** – Target systems for export files.
- **Monitoring/Logging** – External log aggregators or APM (if any).

## 2. AI / LLM Integrations

- **OpenAI API** (or equivalent):
  - Used for classification, extraction, accounting proposals, and enrichment.
  - Configured via environment variables (e.g. `OPENAI_API_KEY`, model names).
  - Prompts and roles are documented in AI-specific docs and should be referenced from here.

- **Local LLMs / Ollama** (if configured):
  - Provide on-prem or cost-optimized inference.
  - Accessed via HTTP endpoints with defined contracts.

## 3. OCR / Transcription

- **OCR Service**:
  - Responsible for PDF/image text extraction.
  - Configuration: endpoints, API keys, rate limits.

- **Whisper / Audio-Video Transcription**:
  - Used when Mind processes meeting recordings or audio receipts.
  - Configuration via environment variables and backend integration modules.

## 4. Card / Bank Exports

- **Corporate Card Providers (e.g. FirstCard)**:
  - Input: CSV/Excel/other statement formats.
  - Mapping between external fields and internal `Card Transactions` documented here and in `40_DATA_MODEL.md`.
  - Any provider-specific quirks (encoding, date formats, currency handling) must be listed.

## 5. Accounting Systems

- **Export Targets**:
  - Exports may produce files in specific formats (e.g. SIE, CSV, XML) or call APIs.
  - Each supported accounting system must have a subsection:
    - Name
    - Version/variant
    - Export format
    - Known limitations.

## 6. Email / FTP

- **Email/IMAP Integration**:
  - Mailboxes used for receipt forwarding.
  - Rules for accepted attachments and formats.

- **FTP / SFTP Integration**:
  - Folders watched for new files.
  - Rules for archiving/moving processed files.

## 7. Configuration and Secrets

- All integration endpoints, keys and secrets are configured via environment variables or config files and **must not** be hard-coded.
- This file references variable names, not actual values.

## 8. Monitoring and Logging

> TODO: Add any external log/monitoring integrations (e.g. external APM or log shipping) once confirmed.