# Debugging Playbook

Version: 2025-11-28  
Scope: Practical steps to investigate failures in Mind2 without altering infrastructure.

## Checklist (quick)
1) Identify file/workflow: get `file_id` (UUID) or `workflow_run_id`.
2) Check latest stage: query `workflow_stage_runs` (see below).
3) Check container logs (API + relevant Celery queue).
4) Inspect AI logs: `ai_processing_history`.
5) Verify status machines: `invoice_documents.processing_status/status`, `invoice_lines.match_status`.
6) Reproduce with Playwright (headless, per TEST_RULES) if UI-related.

## Useful Commands
- Tail API logs: `docker logs -f mind2-ai-api-1`
- Tail Celery queues:  
  - default: `docker logs -f mind2-celery-worker-1`  
  - wf1: `docker logs -f mind2-celery-worker-wf1-1`  
  - wf2: `docker logs -f mind2-celery-worker-wf2-1`
- DB shell: `docker exec -it mind2-mysql-1 mysql -uroot -proot mind2_dev`
- Redis ping: `docker exec -it mind2-redis-1 redis-cli ping`

## SQL Snippets
- Latest stage for a workflow:
```sql
SELECT stage_key, status, message, started_at, finished_at
FROM workflow_stage_runs
WHERE workflow_run_id=<id>
ORDER BY started_at DESC
LIMIT 10;
```
- AI failures:
```sql
SELECT created_at, job_type, ai_stage_name, status, error_message
FROM ai_processing_history
WHERE status='error'
ORDER BY id DESC
LIMIT 20;
```
- Invoice status snapshot:
```sql
SELECT processing_status, status, metadata_json
FROM invoice_documents
WHERE unified_file_id='<file_uuid>';
```

## Attaching a debugger
- Containers are built with Python; you can add temporary `breakpoint()` in a dev branch and restart `ai-api` container if needed. Remove before commit.
- For frontend, use browser devtools on http://localhost:5169 (dev server).

## Common Failure Patterns
- **Stage mismatch**: `ensure_workflow` raises if task run on wrong workflow_key. Check `workflow_runs.workflow_key` and dispatch path.
- **Illegal status transition**: `transition_*` returns 0 rows → warning in logs; indicates race or unexpected current state.
- **Duplicate upload**: `DuplicateFileError` thrown by `create_unified_file` when content_hash collides.

## Playwright Diagnostics
- Base URL defaults to 8008 (`playwright.config.ts`); dev config uses 5169 (`playwright.dev.config.ts`).
- Store artifacts in `web/test-reports/`; keep video 1900x120 and snapshot 1900x1200 per `docs/SYSTEM_DOCS/TEST_RULES.md`.
- Never edit `playwright.config.ts`; tag tests instead.

## Encoding & Locale
- Ensure terminal uses UTF-8 (`chcp 65001` in PowerShell).  
- If you see � in logs/DB, stop and fix per `docs/SWEDISH_ENCODING_RULES.md`.

## When to escalate
- Conflicting documentation vs code (e.g., FC coordinator columns) — note in worklog and surface to reviewers.
- Missing data that requires schema change — do not patch schema without approval.
