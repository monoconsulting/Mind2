# DB Migrations Runbook

There are two ways to apply DB migrations:

1) Auto on startup (default):
- `DB_AUTO_MIGRATE=1` (default) triggers best-effort migrations in API startup.
- API retries for up to ~60s until DB is reachable.

2) Manual endpoint:
- POST http://localhost:8008/ai/api/system/apply-migrations
- Returns `{ ok: true, applied: ["0001...sql", ...] }` on success.

Files:
- SQL in `database/migrations/*.sql` mounted into containers.
- Runner code in `backend/src/services/db/migrations.py` (comment stripping, idempotent, optional demo seed).

Troubleshooting:
- If `1146 ... doesn't exist`, run the manual endpoint.
- If syntax errors, check SQL compatibility with MySQL 8 (avoid ADD COLUMN IF NOT EXISTS).
