# QuickStart – Mind2 Developer Onboarding

Version: 2025-11-28  
Goal: Get a new engineer productive in ~1 hour without changing ports or configs.

## Prerequisites
- Windows 11 (repo scripts are `.bat`/PowerShell friendly).
- Docker Desktop + WSL2 backend enabled.
- Node 18+ and npm.
- Python 3.11 (for backend tooling/tests).
- Access to required secrets: `OPENAI_API_KEY`, DB creds (see `.env.example`). **Do not commit `.env`.**
- Git with LF normalization left as-is (respect `.editorconfig`).

## One-time setup
1) Clone repo and read mandatory instructions: `.prompts/start.prompt.md`, `CLAUDE.md`, `AGENTS.md`, `docs/SWEDISH_ENCODING_RULES.md`.  
2) Create feature branch using `docs/GIT_START.md` steps (base: `dev`).  
3) Copy env template if needed: `cp .env.example .env` (fill real values only; never placeholders).  
4) Install Playwright deps (once): `npm install` (root) then `npx playwright install-deps` if prompted.

## Start the stack (recommended path)
```bat
mind_docker_compose_up.bat
```
- Starts backend API + Celery + MySQL + Redis.
- Serves production frontend on **8008** and hot-reload dev frontend on **5169** (do not change ports).
- Storage mounts: `./storage` → `/data/storage`, `./inbox` → `/data/inbox`.

## Develop
- Frontend (dev): open http://localhost:5169 (auto-started by compose). Code in `main-system/app-frontend/src/`.
- Backend: code in `backend/src/`; API base URL via nginx: http://localhost:8008/ai/api/.
- Workflow dispatch happens automatically on upload; see `docs/WORKFLOWS/WORKFLOW_SUMMARY.md` for stage names.

## Run tests (follow TEST_RULES)
- Playwright (prod baseURL=8008): `npm run test:e2e:report -- web/tests/<file>.spec.ts`
- Playwright (dev baseURL=5169): `npx playwright test --config=playwright.dev.config.ts --headed`
- Requirements: Chromium headless only; video 1900x120, snapshot 1900x1200; save reports to `web/test-reports/`.
- Never modify `playwright.config.ts`; extend existing specs instead of creating new area files.

## Common tasks
- Rebuild frontend prod: `mind_rebuild_frontend.bat`
- Rebuild backend/workers: `mind_docker_compose_build_ai-api_celery-worker.bat`
- Start local Vite without Docker (optional): `mind_frontend_dev.bat`

## Debug quick links
- Workflow history: `SELECT * FROM v_workflow_stages WHERE workflow_run_id=<id>;`
- AI logs: `SELECT * FROM ai_processing_history WHERE file_id='<uuid>' ORDER BY id DESC;`
- Status enums: `docs/SYSTEM_DOCS/STATUS_MODEL.md`

## Guardrails
- No mock data, no SQLite, no port changes, no `playwright.config.ts` edits.
- Keep UTF-8 intact (see `docs/SWEDISH_ENCODING_RULES.md`); avoid introducing BOM.
