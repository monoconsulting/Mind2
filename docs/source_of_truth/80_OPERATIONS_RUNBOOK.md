# docs/source_of_truth/80_OPERATIONS_RUNBOOK.md

# Mind – Operations Runbook (Source of Truth)

> This runbook is for operators and developers responsible for keeping Mind healthy in daily operations.
>
> Version: 2025-12-04
> Source: `docs/OPS/*.md`, `docs/DEVELOPMENT/*.md`, `CLAUDE.md`

## 1. Environments

### 1.1 Development

| Component | URL | Notes |
|-----------|-----|-------|
| Frontend (Dev) | http://localhost:5169 | Vite dev server with hot-reload |
| Frontend (Prod) | http://localhost:8008 | Production build via nginx |
| API (via nginx) | http://localhost:8008/ai/api/ | All API calls |
| phpMyAdmin | http://localhost:8087 | DB admin UI |

### 1.2 Port Assignments (IMMUTABLE)

| Port | Service | Notes |
|------|---------|-------|
| 8008 | Production frontend + API | Via nginx proxy |
| 5169 | Development frontend | Vite hot-reload |
| 5000 | Backend API | Internal only, not exposed |
| 3310 | MySQL | External access |
| 6380 | Redis | External access |
| 8087 | phpMyAdmin | DB admin |
| 9091 | Prometheus | Monitoring profile |
| 3003 | Grafana | Monitoring profile |

## 2. Starting and Stopping the System

### 2.1 Start All Services

```bat
mind_docker_compose_up.bat
```

This starts:
- MySQL, Redis, phpMyAdmin
- Backend API + Celery workers
- Production frontend (port 8008)
- Development frontend (port 5169)

### 2.2 Stop All Services

```bat
docker-compose down
```

### 2.3 Rebuild from Scratch

```bat
mind_docker_build_nocache.bat
```

### 2.4 Rebuild Specific Components

**Frontend only:**
```bat
mind_rebuild_frontend.bat
```

**Backend + Workers:**
```bat
mind_docker_compose_build_ai-api_celery-worker.bat
```

## 3. Health Checks

### 3.1 API Health

```bash
curl http://localhost:8008/ai/api/health
```

Expected: `{"status": "healthy"}`

### 3.2 System Status

```bash
curl http://localhost:8008/ai/api/system/status
```

Checks: API, Database, Redis, Celery

### 3.3 Database Connectivity

```bash
curl http://localhost:8008/ai/api/system/db-ping
```

### 3.4 Celery Worker Status

```bash
curl http://localhost:8008/ai/api/system/celery-ping
```

### 3.5 Smoke Test

1. Open http://localhost:8008
2. Upload a small receipt image
3. Verify it reaches `KLAR` or `completed` status
4. Check workflow stages in UI

## 4. Logs and Debugging

### 4.1 View Container Logs

**Backend API:**
```bash
docker logs mind2-ai-api-1
```

**Celery Workers:**
```bash
docker logs mind2-celery-worker-1
docker logs mind2-celery-worker-wf1-1
docker logs mind2-celery-worker-wf2-1
```

**Frontend (Dev):**
```bash
docker logs mind2-mind-web-main-frontend-dev-1
```

### 4.2 Follow Logs in Real-Time

```bash
docker logs -f mind2-ai-api-1
```

### 4.3 Database Queries for Debugging

**Check file status:**
```sql
SELECT id, filename, workflow_type, ai_status, created_at
FROM unified_files
ORDER BY created_at DESC LIMIT 10;
```

**Check workflow stages:**
```sql
SELECT wsr.stage_key, wsr.status, wsr.message, wsr.started_at
FROM workflow_runs wr
JOIN workflow_stage_runs wsr ON wsr.workflow_run_id = wr.id
WHERE wr.file_id = 'YOUR_FILE_ID'
ORDER BY wsr.started_at DESC;
```

**Check AI processing history:**
```sql
SELECT ai_stage_name, status, confidence, error_message, created_at
FROM ai_processing_history
WHERE file_id = 'YOUR_FILE_ID'
ORDER BY created_at DESC;
```

**Find stuck files:**
```sql
SELECT id, filename, ai_status, created_at
FROM unified_files
WHERE ai_status = 'processing'
AND created_at < DATE_SUB(NOW(), INTERVAL 1 HOUR);
```

### 4.4 Direct Database Access

**phpMyAdmin:**
- URL: http://localhost:8087
- User: root
- Password: root
- Database: mind2_dev

**MySQL CLI:**
```bash
docker exec -it mind2-mysql-1 mysql -u root -proot mind2_dev
```

## 5. Common Incidents

### 5.1 OCR Failures Spike

**Symptoms:** Files stuck at `r_ocr` stage

**Actions:**
1. Check celery-worker-wf1 logs for errors
2. Verify PaddleOCR is responsive
3. Check disk space for temp files
4. Resume failed files via API

### 5.2 AI Errors or Timeouts

**Symptoms:** Files stuck at AI stages, `ai_status = failed`

**Actions:**
1. Check OpenAI API status
2. Verify `OPENAI_API_KEY` is valid
3. Check rate limits in logs
4. Review error messages in `ai_processing_history`

### 5.3 Files Stuck in Processing

**Symptoms:** `ai_status = processing` for extended time

**Actions:**
1. Check workflow_stage_runs for current stage
2. Check Celery worker logs
3. Use resume endpoint to continue processing

**Resume command:**
```bash
curl -X POST http://localhost:8008/ai/api/ingest/process/{file_id}/resume
```

### 5.4 Database Connection Issues

**Symptoms:** API returns 500 errors, DB connection errors in logs

**Actions:**
1. Check MySQL container is running: `docker ps`
2. Check MySQL logs: `docker logs mind2-mysql-1`
3. Verify connection: `docker exec mind2-mysql-1 mysqladmin -u root -proot ping`
4. Restart if needed: `docker-compose restart mysql`

### 5.5 Frontend Not Loading

**Symptoms:** Blank page or 502 errors

**Actions:**
1. Check nginx logs: `docker logs mind2-nginx-1`
2. Check frontend container: `docker logs mind2-mind-web-main-frontend-dev-1`
3. Rebuild frontend: `mind_rebuild_frontend.bat`

## 6. Backups and Restore

### 6.1 Database Backup

```bash
docker exec mind2-mysql-1 mysqldump -u root -proot mind2_dev > backup_$(date +%Y%m%d).sql
```

### 6.2 Database Restore

```bash
docker exec -i mind2-mysql-1 mysql -u root -proot mind2_dev < backup.sql
```

### 6.3 File Storage Backup

Backup the storage directory configured in `STORAGE_DIR` environment variable.

## 7. Deployment and Rollback

### 7.1 Deploy New Version

1. Pull latest code: `git pull origin dev`
2. Rebuild containers: `mind_docker_build_nocache.bat`
3. Start services: `mind_docker_compose_up.bat`
4. Run tests: `npx playwright test --headed`
5. Verify health checks

### 7.2 Rollback

1. Stop services: `docker-compose down`
2. Checkout previous version: `git checkout <commit>`
3. Rebuild: `mind_docker_build_nocache.bat`
4. Start: `mind_docker_compose_up.bat`

## 8. Testing

### 8.1 Production Testing (Port 8008)

```bash
# Full test suite
npx playwright test --headed

# Single test file
npx playwright test web/tests/[filename].spec.ts --headed

# Tagged tests
npx playwright test -g @receipts --headed
```

### 8.2 Development Testing (Port 5169)

```bash
npx playwright test --config=playwright.dev.config.ts --headed
```

### 8.3 Test Reports

- HTML report: `web/test-results/html/index.html`
- Videos: `web/test-results/media/video/`
- Screenshots: `web/test-results/media/snapshots/`

## 9. Monitoring

### 9.1 Prometheus Metrics

Access: http://localhost:9091 (monitoring profile)

### 9.2 Grafana Dashboards

Access: http://localhost:3003 (monitoring profile)

### 9.3 Key Metrics to Monitor

- Celery queue lengths
- AI processing success/failure rates
- OCR processing times
- Database connection pool usage

## 10. Environment Variables

Key variables configured in `.env`:

| Variable | Description |
|----------|-------------|
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASS` | Database password |
| `OPENAI_API_KEY` | OpenAI API key |
| `JWT_SECRET_KEY` | JWT signing key |
| `STORAGE_DIR` | File storage path |
| `ENABLE_REAL_OCR` | Toggle OCR (set to 1) |
| `OCR_LANG` | OCR language (default: sv) |

## 11. Encoding Rules

**All text must use UTF-8 encoding.**

- Database charset: `utf8mb4_0900_ai_ci`
- File encoding: UTF-8
- API responses: UTF-8
- Required for Swedish characters

Reference: `docs/SWEDISH_ENCODING_RULES.md`

## 12. Security

### 12.1 API Authentication

All endpoints (except health) require JWT token:
```
Authorization: Bearer <token>
```

### 12.2 Secrets Management

- Never commit secrets to git
- Use environment variables
- Reference: `docs/SYSTEM_DOCS/SECRETS_RUNBOOK.md`

## 13. Emergency Contacts

- **System Owner:** TBD
- **On-Call:** TBD

## 14. Governance

- Runbook changes require review
- All incidents should be documented
- Post-incident reviews for critical issues
