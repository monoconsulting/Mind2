# MIND Environment Variables (v2.0)

Core
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`
- `REDIS_HOST`, `REDIS_PORT`, (`REDIS_DB` optional)
- `JWT_SECRET_KEY` – HS256 signing key (prefer over `JWT_SECRET`)
- `ADMIN_PASSWORD` – dev/staging bootstrap login
- `ALLOWED_ORIGINS` – comma-separated list for CORS
- `LOG_LEVEL` – INFO|DEBUG|WARN|ERROR

AI / Processing
- `AI_PROCESSING_ENABLED` – feature flag
- `ENABLE_REAL_OCR` – use real OCR engine if available

Capture / Storage
- `STORAGE_DIR` – base directory for stored files (mounted volume)
- `FTP_LOCAL_DIR`, `FTP_LOCAL_MOVE_DIR`, `FTP_ALLOWED_EXT`
- `FTP_HOST`, `FTP_PORT`, `FTP_USER`, `FTP_PASS`, `FTP_PASSIVE`, `FTP_REMOTE_DIR`, `FTP_TLS`, `FTP_DELETE_AFTER`

Notes
- See `.env.example` for local defaults.
- For production, inject via orchestrator/secrets manager (see `docs/SECRETS_RUNBOOK.md`).
