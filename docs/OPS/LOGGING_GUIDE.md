# Logging Guide

Version: 2025-11-28  
Scope: How logging is structured and how to extend it safely (without code changes here).

## Log Sources
| Source | Purpose | File |
| --- | --- | --- |
| Application logger (`logging`) | Human-readable info/error lines from API + Celery tasks. | Used across `backend/src/services/tasks/*.py`, `services/ai_service.py` |
| Workflow logs | Stage-by-stage history stored in DB. | `backend/src/services/tasks/workflow_base.py` (`mark_stage`, `begin_import_stage`, `complete_import_stage`) |
| AI call logs | Structured inserts into `ai_processing_history`. | `backend/src/services/ai_logging.py` (`log_ai_call`) |
| Observability events | Event-style logging helpers. | `backend/src/observability/events.py` |
| Metrics | Counters for illegal state transitions. | `backend/src/observability/metrics.py` |

## Patterns to Follow
- Use `log_ai_call(file_id, job, status, ai_stage_name, log_text, error_message, confidence, processing_time_ms, provider, model_name)` after each provider call; returns False if DB unavailable (no exception).
- Wrap workflow steps with `begin_import_stage` / `complete_import_stage` to ensure `workflow_stage_runs` gets start/end markers and boundary nodes (`*_start`/`*_end`).
- For status transitions, rely on `transition_*` helpers in `services/invoice_status.py`; they already log assertion failures via `record_invoice_state_assertion`.
- Keep messages short (<200 chars) because `workflow_stage_runs.message` is stored as TEXT but UI truncates.
- Prefer `extra={...}` on logger calls for structured context (workflow_run_id, file_id, stage).

## Where Logs Land
- **Container stdout/stderr**: `docker logs -f mind2-ai-api-1`, `mind2-celery-worker-*`.
- **Database**:
  - `workflow_stage_runs` (stage-level status/timestamps).
  - `ai_processing_history` (AI job logs).
  - `observability` metrics tables if configured (see `observability/metrics.py`).

## Adding New Logs (guidance)
- Use existing helpers; do not invent new stage names without updating `docs/SYSTEM_DOCS/STATUS_MODEL.md`.
- Keep encoding UTF-8 (Swedish characters allowed; see `docs/SWEDISH_ENCODING_RULES.md`).
- Avoid adding PII; redact card numbers, emails, or tokens.
- For AI payloads, prefer summaries; if storing prompts/responses, ensure size is bounded (see `ai_service.py` patterns).


## Quick Reference Snippets
```python
from services.ai_logging import log_ai_call
log_ai_call(file_id, "ai3", "success", ai_stage_name="AI3-DataExtraction",
            log_text="Extracted totals", confidence=0.94, processing_time_ms=5200,
            provider=provider_name, model_name=model)
```

```python
from services.tasks.workflow_base import begin_import_stage, complete_import_stage
begin_import_stage(workflow_run_id, "fc_ocr", message="OCR start")
complete_import_stage(workflow_run_id, "fc_ocr", success=True, message="OCR done")
```
