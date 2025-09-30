# AI Pipeline Operations Guide

This document outlines the configuration required to operate the deterministic
AI1–AI5 processing pipeline in local development and production-like
environments.

## Required environment variables

The backend services expect the following variables to be present before the
pipeline can connect to the database and supporting services:

| Variable | Description |
| --- | --- |
| `DB_HOST` | Hostname of the MySQL instance that stores unified receipts. |
| `DB_PORT` | Port exposed by the database service (default `3306`). |
| `DB_NAME` | Logical database that contains the `unified_files` schema. |
| `DB_USER` | Username with read/write privileges for AI tables. |
| `DB_PASS` | Password for `DB_USER`. |
| `JWT_SECRET` | Shared secret for API authentication middleware. |
| `STORAGE_DIR` | Absolute path to OCR assets used during processing. |
| `ENABLE_REAL_OCR` | When set to `true`, OCR workers will invoke the real OCR engine instead of the stub. |
| `COMPANY_CARD_MERCHANTS` | Comma-separated list of merchant names that indicate company card usage (affects classification fallbacks). |

## Operational checklist

1. **Celery workers** – ensure Celery is running with the `process_ocr` task
   enabled. Each OCR completion now triggers `process_ai_pipeline`, which
   executes AI1 through AI5 sequentially and records stage history.
2. **Database migrations** – the schema must include the tables and columns
   referenced in `docs/SYSTEM_DOCS/MIND_AI_v.1.0.md`. Apply migrations before
   starting workers to avoid persistence failures.
3. **Monitoring** – inspect the `ai_processing_history` table or Prometheus
   metrics to verify stage transitions. Errors automatically revert the file to
   `manual_review` and capture the exception message in worker logs.
4. **Credential storage** – secrets should be injected through your deployment
   platform (Docker secrets, Kubernetes secrets, etc.). Avoid committing
   plaintext credentials to the repository.

## Smoke test procedure

1. Upload a receipt through the UI or API and confirm an OCR job is queued.
2. Wait for the Celery worker to execute `process_ai_pipeline`. Each stage is
   recorded in `ai_processing_history` (`ai1` … `ai5`, `ai_pipeline`).
3. Validate database side-effects:
   - `unified_files` contains the updated `file_type`, `expense_type`, amounts,
     and AI confidence.
   - `receipt_items` is repopulated with AI3 results.
   - `ai_accounting_proposals` contains the AI4 proposals.
   - `creditcard_receipt_matches` is updated when AI5 finds a match.
4. Query `/ai/status/<file_id>` to confirm the pipeline reports completion and
   includes accounting proposal and credit card match flags.

## Runbook for failures

| Symptom | Resolution |
| --- | --- |
| Stage aborts with `PipelineExecutionError` | Inspect OCR text availability and ensure the previous stage populated the required fields (e.g., missing document type before AI2). |
| Database constraint error | Confirm migrations were applied and the service account has permission to modify AI tables. |
| Credit card matching returns no candidates | Verify invoice data exists for the purchase date and the amount tolerance (`±5 SEK`) is adequate. |

Following this guide ensures the deterministic AI pipeline operates reliably
across environments and provides predictable recovery steps when issues arise.
