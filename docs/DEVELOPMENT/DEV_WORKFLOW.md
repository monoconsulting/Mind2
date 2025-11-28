# Developer Workflow Guide

Version: 2025-11-28  
Purpose: Day-to-day steps for implementing changes while respecting Mind2 guardrails.

## Daily Loop
1) **Branch correctly** – follow `docs/GIT_START.md` (base `dev`, clean tree).  
2) **Assign task** – ensure Task-Master entry exists (see `docs/TASK_MASTER_AGENT_INSTRUCTIONS.md`).  
3) **Sync** – `git pull origin dev`; verify `git status` clean.  
4) **Start stack** – `mind_docker_compose_up.bat` (do not alter ports).  
5) **Develop** – edit code in `backend/src/` or `main-system/app-frontend/src/`. Keep UTF-8.  
6) **Trace workflow** – use queries/logs below to verify behaviour.  
7) **Test** – Playwright per `docs/SYSTEM_DOCS/TEST_RULES.md`; do not edit tests to pass.  
8) **Review** – re-read instructions, run `git diff`, ensure no config/port changes.  
9) **Finish** – follow `docs/GIT_END.md` when user approves.

## Tracing a Receipt (WF1)
- Upload via UI (Process page) or `POST /ai/api/ingest/upload`.
- Find workflow run: `SELECT id FROM workflow_runs WHERE file_id='<uuid>' ORDER BY id DESC LIMIT 1;`
- Inspect stages: `SELECT stage_key,status,started_at,message FROM workflow_stage_runs WHERE workflow_run_id=<id> ORDER BY id;`
- AI logs: `SELECT ai_stage_name,status,provider,model_name FROM ai_processing_history WHERE file_id='<uuid>';`

## Tracing a FirstCard Statement (WF3)
- Upload via CompanyCard page or resume endpoint.
- Workflow log: same as above with `workflow_key='WF3_FIRSTCARD_INVOICE'`.
- Check invoice status: `SELECT processing_status,status,metadata_json FROM invoice_documents WHERE unified_file_id='<uuid>'\G`
- Lines/match status: `SELECT match_status,unified_file_id FROM invoice_lines WHERE creditcard_main_id=<main_id>;`
- Auto-match results logged under stage keys `auto_match`, `ai5`, `m_found`, `m_link`, `m_unmatched`.

## Logs to tail
- API container: `docker logs -f mind2-ai-api-1`
- Celery default: `docker logs -f mind2-celery-worker-1`
- Celery wf1/wf2: `docker logs -f mind2-celery-worker-wf1-1`, `mind2-celery-worker-wf2-1`
- Dev frontend: `docker logs -f mind2-mind-web-main-frontend-dev-1`

## Testing Checklist
- Determine if relevant Playwright spec exists under `web/tests`; report “Test available”/“Test not available”.
- Reproduce bug with failing test (Chromium headless); keep video 1900x120 and snapshot 1900x1200; store report in `web/test-reports/`.
- Fix responsible layer only; rerun same test until pass; do not modify `playwright.config.ts`.
- For backend changes, add/execute `pytest` where applicable (respect existing patterns).

## Do / Don’t
- **Do**: keep documentation in `docs/` updated; log all workflow changes via helpers in `workflow_base.py`.  
- **Don’t**: use mock data, switch ports, edit `.env` or `docker-compose.yml` without approval, or bypass UTF-8 rules.

## Handy references
- Status model: `docs/SYSTEM_DOCS/STATUS_MODEL.md`
- Workflow maps: `docs/WORKFLOWS/*`
- Architecture: `docs/ARCHITECTURE/BACKEND_ARCH.md`
