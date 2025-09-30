# AI Operations Runbook

## Purpose
This runbook documents how to operate the OCR-to-accounting AI pipeline now that
Celery executes stages AI1–AI5 in sequence. Use it when bootstrapping new
environments, monitoring production, or responding to incidents involving the AI
processing flow.

## End-to-end workflow
1. **OCR ingestion** – `process_ocr` stores the raw OCR text and enqueues
   `process_ai_pipeline` for further processing. The task marks the receipt as
   `ocr_done` and records the OCR confidence.
2. **AI1 Document classification** – Updates `unified_files.file_type` and sets
   `ai_status = 'ai1_completed'` after logging history.
3. **AI2 Expense classification** – Sets `expense_type` and advances
   `ai_status = 'ai2_completed'` while retaining the highest confidence score.
4. **AI3 Data extraction** – Writes structured data, receipt items, and vendor
   rows via `persist_extraction_result`, then marks `ai_status = 'ai3_completed'`.
5. **AI4 Accounting classification** – Generates BAS-2025 proposals with
   `persist_accounting_proposals` and moves the file to `ai_status = 'ai4_completed'`.
6. **AI5 Credit-card matching** – Attempts to match invoice items and, when
   successful, persists the relation through `persist_credit_card_match` before
   setting `ai_status = 'ai5_completed'` or logging an actionable warning if
   prerequisites (e.g., purchase date) are missing.【F:backend/src/services/tasks.py†L1-L236】【F:backend/src/services/tasks.py†L236-L366】

## Required environment variables
The AI services use the shared database connection helper, so ensure the
following variables are present for both the API and the Celery worker
containers:

| Variable | Description |
| -------- | ----------- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` | MySQL connectivity used by `get_connection` and `db_cursor`. |
| `JWT_SECRET_KEY` | Needed by the API endpoints that guard AI routes. |
| `STORAGE_DIR` | File-system root for OCR payloads consumed by `process_ocr`. |
| `AI_PROCESSING_ENABLED` | Feature flag checked by orchestration scripts. |
| `ENABLE_REAL_OCR` | Controls whether `process_ocr` calls the real OCR provider. |
| `PROMETHEUS_PUSHGATEWAY` *(optional)* | Enables metric emission from Celery if configured in `observability.metrics`. |

See `MIND_ENV_VARS.md` for defaults and staging overrides.【F:docs/SYSTEM_DOCS/MIND_ENV_VARS.md†L1-L41】

## Monitoring & telemetry
- **Celery metrics** – Every AI task is wrapped in `@track_task`, exposing
  duration and success counters through the observability subsystem. Scrape these
  metrics via Prometheus or view them in Grafana dashboards.
- **History table** – The helper `_history` records each stage in
  `ai_processing_history`. Alert on repeated `error` entries or missing records
  for newly uploaded receipts.【F:backend/src/services/tasks.py†L21-L111】
- **AI status timeline** – Inspect `unified_files.ai_status` to confirm stage
  progression. Values should transition from `processing` → `ai1_completed` → … →
  `ai5_completed`. Deviations indicate a stage failure or manual override.

## Operational playbooks
- **Reprocessing a receipt** – Call `process_ai_pipeline.delay(<file_id>)` with a
  subset of steps if you only need to rerun later stages, e.g. `steps=["AI3",
  "AI4", "AI5"]`. The helper `_execute_ai_pipeline` is idempotent with respect to
  database writes, replacing receipt items, accounting proposals, and credit-card
  matches atomically.【F:backend/src/services/tasks.py†L142-L366】
- **Handling AI5 misses** – When `process_ai_pipeline` reports a missing purchase
  date, patch the receipt with the correct timestamp and rerun `steps=["AI5"]` to
  create the match record.
- **Database validation** – Use the SQL migrations under
  `database/migrations/0010_expand_ai_schema.sql` to guarantee that staging and
  production include all AI-specific tables. Re-run migrations safely thanks to
  the `IF NOT EXISTS` guards.【F:database/migrations/0010_expand_ai_schema.sql†L1-L120】

## Incident response checklist
1. Confirm the Celery worker is running and subscribed to the AI queue.
2. Check `ai_processing_history` for the affected receipt ID to determine the
   last successful stage.
3. Review logs emitted by `AIService` and `_execute_ai_pipeline` for the stage
   that failed; they include contextual information about missing OCR data or
   configuration.
4. If external providers are involved, ensure prompts and model configuration are
   present in `ai_system_prompts` and `ai_llm_model`. The service gracefully
   falls back to rule-based logic but still records warnings in the logs.
5. After remediation, rerun `process_ai_pipeline` for the affected file and
   verify that `unified_files.ai_status` reaches `ai5_completed`.
