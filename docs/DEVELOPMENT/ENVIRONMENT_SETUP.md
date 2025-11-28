# Environment Setup

Version: 2025-11-28  
Scope: How to configure Mind2 locally without altering fixed ports or configs.

## Files
- `.env.example` – template with required keys.  
- `.env` – **private**, not checked in. Fill with real values only (no placeholders).  
- `docker-compose.yml` consumes these vars for ai-api, Celery, MySQL, Redis, FTP.

## Required variables (minimum)
| Key | Used by | Notes |
| --- | --- | --- |
| `DB_NAME`, `DB_USER`, `DB_PASS`, `DB_HOST`, `DB_PORT` | Flask API + Celery | MySQL 8 (docker service `mysql`, port 3306 internal, 3310 exposed). |
| `REDIS_HOST`, `REDIS_PORT` | Celery broker | Defaults to `redis:6379` in compose. |
| `JWT_SECRET_KEY` | API auth middleware | Required for `/ai/api/*`. |
| `OPENAI_API_KEY` | AI providers (AI1–AI6, AI5) | Needed in workers (`celery-worker`, `celery-worker-wf1/wf2`). |
| `STORAGE_DIR` | File storage path | Mounted to `/data/storage` inside containers. |
| `FTP_HOST`, `FTP_PORT`, `FTP_USER`, `FTP_PASS`, `FTP_REMOTE_DIR`, `FTP_LOCAL_MOVE_DIR`, `FTP_ALLOWED_EXT`, `FTP_DELETE_AFTER`, `FTP_TLS`, `FTP_PASSIVE` | FTP ingestion (`services/ftp_service.py`, `fetch_ftp.py`). |
| `ENABLE_REAL_OCR`, `OCR_LANG`, `OCR_USE_ANGLE_CLS`, `OCR_SHOW_LOG` | OCR behaviour in Celery workers. |
| `ALLOWED_ORIGINS` | CORS | Used by Flask API. |
| `ADMIN_PASSWORD` | Admin auth for API | Consumed by `ai-api` container. |

## Optional / dev helpers
- `DB_AUTO_MIGRATE=1` to let API apply migrations on start (see `docker-compose.yml`).
- `VITE_REFRESH_INTERVAL_SECONDS` for frontend polling (main-system/app-frontend).
- `FTP_LOCAL_DIR` for local inbox (defaults `/data/inbox`).

## Setup Steps
1) Copy template: `cp .env.example .env` (fill real secrets).  
2) Ensure Docker Desktop running.  
3) Run `mind_docker_compose_up.bat` (pulls vars from `.env`).  
4) Verify containers healthy: `docker compose ps` (expect ai-api, celery workers, mysql, redis, nginx, mind-web-main-frontend-dev).  
5) Confirm ports: 8008 (prod UI/API), 5169 (dev UI), 3310 (MySQL), 6380 (Redis), 8087 (phpMyAdmin).

## Storage & Paths
- Host `./storage` → `/data/storage` (original + derived files).
- Host `./inbox` → `/data/inbox` (FTP local drop).
- Uploaded files tracked in `unified_files` table; hashes prevent duplicates.

## Safety
- Never commit `.env` or secrets.  
- Do not change port mappings without explicit approval.  
- Keep encoding UTF-8 (see `docs/SWEDISH_ENCODING_RULES.md`).  
- Respect `AGENTS.md` prohibitions (no mock data, no SQLite, no `playwright.config.ts` edits).
