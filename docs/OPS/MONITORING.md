# Monitoring & Health Checks

Version: 2025-11-28  
Purpose: How to observe Mind2 pipelines without code changes.

## What to Watch
| Signal | Where | How |
| --- | --- | --- |
| Workflow progression | `workflow_runs`, `workflow_stage_runs` | `SELECT * FROM v_workflow_stages WHERE workflow_run_id=<id>;` |
| AI calls | `ai_processing_history` | `SELECT created_at, job_type, ai_stage_name, status, provider, model_name FROM ai_processing_history WHERE file_id='<uuid>' ORDER BY id DESC;` |
| Invoice states | `invoice_documents`, `invoice_lines` | Check `processing_status`, `status`, `match_status` with guarded transitions in `services/invoice_status.py`. |
| Queue health | Docker logs for Celery workers (`mind2-celery-worker*`) | `docker logs -f mind2-celery-worker-wf1-1` etc. |
| API availability | nginx on 8008, dev frontend 5169 | Browser smoke or `curl http://localhost:8008/ai/api/health` if endpoint exists. |

## Quick SQL Dashboards
- Latest stage per file:
```sql
SELECT wr.id AS workflow_run_id, wr.workflow_key, wr.file_id,
       CONCAT(wsr.stage_key,' ',wsr.status) AS last_stage,
       wsr.started_at, wsr.finished_at
FROM workflow_runs wr
LEFT JOIN workflow_stage_runs wsr ON wsr.workflow_run_id = wr.id
WHERE wsr.id = (
  SELECT id FROM workflow_stage_runs WHERE workflow_run_id = wr.id ORDER BY started_at DESC LIMIT 1
)
ORDER BY wr.id DESC
LIMIT 50;
```
- AI error summary:
```sql
SELECT job_type, ai_stage_name, status, COUNT(*) AS cnt
FROM ai_processing_history
GROUP BY job_type, ai_stage_name, status
ORDER BY cnt DESC;
```
- Invoice state assertions (if metrics hooked): watch `observability.metrics.record_invoice_state_assertion` logs for illegal transitions.

## Files & Tables to Correlate
- **workflow_runs/stage_runs** schema: `database/migrations/0042_create_workflow_tracking.sql`
- **Status enums**: `backend/src/services/status_constants.py`
- **State machine helpers**: `backend/src/services/invoice_status.py`
- **AI logs**: `backend/src/services/ai_logging.py`

## Operational Checks
- Storage free space: ensure `./storage` and `./inbox` not full (host).
- MySQL connectivity: `docker exec -it mind2-mysql-1 mysql -uroot -proot mind2_dev -e "SELECT 1;"`.
- Redis health: `docker exec -it mind2-redis-1 redis-cli ping`.
- Celery queue depth: `docker exec -it mind2-redis-1 redis-cli LLEN celery` (queue names: `celery`, `wf1`, `wf2`).

## Reporting
- Capture report artifacts under `web/test-reports/` for Playwright runs.
- For incidents, record affected workflow_run_id, file_id, stage_key, and failing transition; include queries/log snippets.
