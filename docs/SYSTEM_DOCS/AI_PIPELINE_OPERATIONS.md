# AI Pipeline Operations Runbook

## Overview
This runbook complements the implementation plan by describing how to operate the
AI processing pipeline across environments. The checklist targets the AI1–AI5
stages implemented in the Flask API and Celery worker.

## Required environment variables
| Variable | Description |
| --- | --- |
| `DB_HOST` | MySQL host used by `backend/src/services/db/connection.py` |
| `DB_PORT` | MySQL port (default `3310`) |
| `DB_NAME` | Target schema (defaults to `mono_se_db_9`) |
| `DB_USER` | Database user with DML permissions |
| `DB_PASS` | Password for `DB_USER` |
| `JWT_SECRET` | Secret used by the auth middleware protecting `/ai/*` |
| `JWT_AUDIENCE` | Expected JWT audience value |
| `JWT_ISSUER` | Expected JWT issuer value |
| `STORAGE_DIR` | Base folder for OCR payloads and enrichment hints |
| `CELERY_BROKER_URL` | Broker URI for Celery task dispatch |
| `CELERY_RESULT_BACKEND` | Celery result backend (Redis/MySQL) |
| `AI_PROVIDER` | Optional override for future LLM adapters (`rule-based` fallback) |
| `OPENAI_API_KEY` | Required when `AI_PROVIDER=openai` |
| `AZURE_OPENAI_ENDPOINT` | Required when Azure deployment is active |
| `AZURE_OPENAI_KEY` | Secret for Azure OpenAI deployments |

All variables must be available to both the Flask API container and the Celery
worker so they share database and provider settings.

## Database preparation
1. Load the latest production snapshot (`mono_se_db_9 (3).sql`).
2. Run `python -m services.db.migrations` or the equivalent invoke target to
   ensure all schema migrations under `database/migrations` are applied.
3. Validate `DESCRIBE unified_files` output to confirm the AI-specific columns
   (`ai_status`, `ai_confidence`, `credit_card_match`, etc.) exist.

## API and worker expectations
- **AI1 (Document classification)** updates `unified_files.ai_status` to
  `ai1_completed` and raises `ai_confidence` using the deterministic rules in
  `AIService`.
- **AI2 (Expense classification)** writes the selected expense type and moves the
  record to `ai2_completed`.
- **AI3 (Extraction)** persists structured data, refreshes `receipt_items`, and
  marks the file as `ai3_completed` atomically.
- **AI4 (Accounting proposals)** replaces `ai_accounting_proposals` entries and
  records `ai4_completed`.
- **AI5 (Credit card matching)** stores the relation in
  `creditcard_receipt_matches`, sets `credit_card_match = 1`, and advances the
  status to `ai5_completed`.

Each stage is idempotent; rerunning an endpoint will replace existing data while
preserving the highest `ai_confidence` observed.

## Monitoring and observability
1. Enable the Prometheus exporters under `observability/` to collect Celery task
   durations. The `track_task` decorator is already applied to AI-related tasks.
2. Configure Grafana dashboards to alert when:
   - The queue length for AI tasks exceeds the agreed SLO threshold.
   - `ai_processing_history` records show repeated `manual_review` regressions.
3. Inspect `backend/logs/ai_service.log` (configured via logging) for regex based
   fallbacks or provider failures.

## Smoke test procedure
1. Upload a receipt through the UI or API and trigger OCR processing.
2. Call `GET /ai/status/<file_id>` to confirm stage progression from
   `ai1_completed` through `ai5_completed`.
3. Verify database side effects:
   - `SELECT * FROM receipt_items WHERE main_id = <file_id>`
   - `SELECT * FROM ai_accounting_proposals WHERE receipt_id = <file_id>`
   - `SELECT * FROM creditcard_receipt_matches WHERE receipt_id = <file_id>`

## Incident response
- If any stage raises an exception, the Celery worker reverts the receipt to
  `manual_review`. Investigate using the `ai_processing_history` audit trail.
- Clear stuck jobs by restarting the Celery worker only after verifying the
  broker queue health (do **not** change ports per repository policy).
- Escalate provider outages by switching `AI_PROVIDER` to `rule-based` so the
  deterministic extractors continue operating.
