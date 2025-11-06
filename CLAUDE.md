# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

```
Version: 3.0
Datum: 2025-11-05
```

## System Overview

Mind2 is an AI-powered document processing system for Swedish accounting, specializing in receipt OCR, credit card reconciliation, and automated accounting classification. The system uses Flask backend with Celery workers, React frontend, and OpenAI for AI processing.

### Architecture Components

**Backend Stack:**
- Flask REST API (port 5000 internal)
- Celery task queue with 3 specialized workers (default, wf1, wf2)
- MySQL 8 database (port 3310)
- Redis 7 for Celery message broker (port 6380)
- PaddleOCR for text extraction
- OpenAI API for AI classification and data extraction

**Frontend Stack:**
- React 18 with Vite 5.4
- React Router for navigation
- Tailwind CSS for styling
- Production: Docker + Nginx (port 8008)
- Development: Vite dev server with hot-reload (port 5169)

**Infrastructure:**
- Nginx reverse proxy (routes /ai/api/ → Flask backend)
- Docker Compose with profiles (main, monitoring)
- Prometheus + Grafana for monitoring (optional profile)

## Critical Rules

**⚠️ ABSOLUTE PROHIBITIONS:**
- **NO MOCK DATA** - Never hardcode or invent data. All data must come from real sources (DB, OCR, API)
- **NO SQLITE** - System only uses MySQL. SQLite will break everything
- **NO PORT CHANGES** - Ports are fixed (see Port Assignments below). Ask before changing
- **NO taskkill** - Never kill ports. This can damage other services
- **NO EDITING playwright.config.ts** - Only playwright.dev.config.ts may be edited for development
- **NO merchant_name COLUMN** - This column does NOT exist in unified_files (see Database Schema)

**Document Orientation:**
- All receipts, PDFs, invoices must be in portrait mode
- If landscape, must be converted to portrait
- This functionality cannot be removed

## Database Schema - Critical Information

### ⚠️ MERCHANT_NAME DOES NOT EXIST

The `merchant_name` column does NOT exist in `unified_files` table!

**WRONG:** `SELECT merchant_name FROM unified_files`
**CORRECT:** `SELECT c.name FROM unified_files u LEFT JOIN companies c ON c.id = u.company_id`

### Key Tables

**unified_files** (main document table):
- Primary key: `id`
- Company reference: `company_id` (FK → companies.id)
- Workflow routing: `workflow_type` VARCHAR(32) DEFAULT 'receipt'
  - `'receipt'` - Standard receipt workflow (AI1→AI4)
  - `'creditcard_invoice'` - FirstCard credit card statement workflow (AI5→AI6)
  - **CRITICAL:** `workflow_type` has priority over `file_type` for routing
- Financial: `purchase_datetime`, `gross_amount`, `net_amount`, `vat_amount`
- Processing: `file_hash`, `ocr_status`, `ai_status`, etc.
- ❌ DOES NOT HAVE: `merchant_name` (use companies.name via JOIN!)

**companies:**
- Primary key: `id`
- Fields: `name`, `orgnr`, `address`, `address2`, `zip`, `city`, `country`, `phone`, `www`, `email`

**receipt_items:**
- Primary key: `id`
- Foreign key: `main_id` (FK → unified_files.id)
- Line items: `article_id`, `name`, `quantity`, `unit_price`, `vat_rate`, etc.

**ai_accounting_proposals:**
- Primary key: `id`
- Foreign keys: `receipt_id` (FK → unified_files.id), `item_id` (FK → receipt_items.id)
- Accounting: `account_code`, `debit`, `credit`, `vat_code`, `confidence_score`

**creditcard_invoices_main:**
- Credit card statement headers
- Fields: `card_name`, `invoice_date`, `due_date`, `amount_to_pay`

**creditcard_invoices_lines:**
- Individual transactions on credit card statements
- Links to receipts for matching

## Workflow System

The system processes documents through different AI workflows based on `workflow_type`:

**Receipt Workflow (workflow_type='receipt'):**
1. PDF Conversion → PNG pages
2. OCR (PaddleOCR) → text extraction
3. AI1 (Document Classification) → identify document type
4. AI2 (Data Extraction) → extract merchant, date, amounts
5. AI3 (Expense Classification) → categorize expense type
6. AI4 (Accounting Classification) → suggest account codes
7. Validation → check data completeness
8. Ready for user review/approval

**Credit Card Statement Workflow (workflow_type='creditcard_invoice'):**
1. PDF Conversion → PNG pages
2. OCR (PaddleOCR) → text extraction
3. AI5 (Credit Card Extraction) → extract header + line items
4. AI6 (Matching) → match transactions to existing receipts
5. Ready for manual verification

**Celery Queues:**
- `default` - General background tasks
- `wf1` - Receipt workflow (AI1-AI4)
- `wf2` - Credit card workflow (AI5-AI6)

## Development Commands

### Docker Operations

**Build from scratch (no cache):**
```bat
mind_docker_build_nocache.bat
```

**Start all services:**
```bat
mind_docker_compose_up.bat
```
This starts:
- MySQL, Redis, phpMyAdmin
- Backend API + Celery workers
- Production frontend (port 8008)
- **Development frontend with hot-reload (port 5169)** ← AUTOMATIC

**Rebuild only frontend:**
```bat
mind_rebuild_frontend.bat
```

**Rebuild only backend + workers:**
```bat
mind_docker_compose_build_ai-api_celery-worker.bat
```

### Testing Commands

**Production Testing (port 8008):**
```bat
# Full test suite
npx playwright test --headed

# Single test file
npx playwright test web/tests/[filename].spec.ts --headed

# Tagged tests
npx playwright test -g @receipts --headed
```

**Development Testing with Hot-Reload (port 5169):**
```bat
# Recommended: Use Docker dev server (starts automatically)
npx playwright test --config=playwright.dev.config.ts --headed

# Or: Start local dev server first
mind_frontend_dev.bat
npx playwright test --config=playwright.dev.config.ts --headed
```

**Test Reports:**
- HTML report: `web/test-results/html/index.html`
- Videos: `web/test-results/media/video/`
- Screenshots: `web/test-results/media/snapshots/`
- Traces: `web/test-results/_artifacts/`

### Frontend Development

**Two Development Modes:**

1. **Docker Dev Mode (Recommended)** - Starts automatically:
   - Runs in container with Vite dev server
   - URL: http://localhost:5169
   - Hot-reload enabled
   - No manual start needed (launches with `mind_docker_compose_up.bat`)
   - Proxies API directly to ai-api:5000

2. **Local Dev Mode** - Manual start:
   - Runs on host machine via npm
   - Start: `mind_frontend_dev.bat`
   - URL: http://localhost:5169
   - Hot-reload enabled
   - Proxies API to localhost:8008 (via nginx)

**Development Workflow:**
1. Start services: `mind_docker_compose_up.bat`
2. Frontend automatically available at http://localhost:5169
3. Edit code in `main-system/app-frontend/src/`
4. Changes appear instantly (no rebuild)
5. Test: `npx playwright test --config=playwright.dev.config.ts --headed`

**Pre-commit verification:**
- Rebuild production: `mind_docker_build_nocache.bat`
- Test production: `npx playwright test --headed`

### Database Access

**phpMyAdmin:**
- URL: http://localhost:8087
- User: root
- Password: root
- Database: mind2_dev

**MySQL Direct:**
```bash
docker exec -it mind2-mysql-1 mysql -u root -proot mind2_dev
```

## Port Assignments (IMMUTABLE)

- **8008** - Production frontend + API (via nginx)
- **5169** - Development frontend with hot-reload (Vite)
- **5000** - Backend API (internal, not exposed)
- **3310** - MySQL (external access)
- **6380** - Redis (external access)
- **8087** - phpMyAdmin
- **9091** - Prometheus (monitoring profile)
- **3003** - Grafana (monitoring profile)

## Project Structure

```
Mind2/
├── backend/
│   ├── src/
│   │   ├── api/                    # Flask blueprints (REST endpoints)
│   │   │   ├── receipts.py         # Receipt CRUD + monthly summary
│   │   │   ├── reconciliation_firstcard.py  # Credit card reconciliation
│   │   │   ├── ai_processing.py    # AI classification endpoints
│   │   │   ├── export.py           # SIE export
│   │   │   └── ingest.py           # File upload
│   │   ├── models/                 # Pydantic data models
│   │   ├── services/               # Business logic
│   │   │   ├── tasks.py            # Celery task definitions
│   │   │   ├── ocr.py              # PaddleOCR integration
│   │   │   ├── ai_service.py       # OpenAI API client
│   │   │   ├── workflow_runs.py    # Workflow orchestration
│   │   │   └── db/                 # Database layer
│   │   └── observability/          # Logging + metrics
│   ├── Dockerfile                  # Production backend image
│   └── requirements.txt            # Python dependencies
├── main-system/
│   └── app-frontend/
│       ├── src/
│       │   ├── ui/
│       │   │   ├── api.js          # API client (uses relative paths)
│       │   │   ├── pages/          # React page components
│       │   │   └── components/     # Reusable UI components
│       │   └── main.jsx            # React entry point
│       ├── Dockerfile              # Production frontend build
│       ├── Dockerfile.dev          # Development with hot-reload
│       ├── vite.config.js          # Vite configuration
│       └── package.json
├── web/
│   └── tests/                      # Playwright E2E tests
│       ├── *.spec.ts               # Test files
│       └── test-results/           # Test output
├── database/
│   └── migrations/                 # SQL migration scripts
├── nginx/
│   └── nginx.conf                  # Reverse proxy configuration
├── docker-compose.yml              # Service orchestration
├── playwright.config.ts            # Production test config
├── playwright.dev.config.ts        # Development test config
└── docs/
    ├── TEST_RULES.md               # Testing standards
    └── SYSTEM_DOCS/
        └── MIND_TASK_IMPLEMENTATION_REVIEW.md  # Architecture details
```

## Testing Requirements (Per TEST_RULES.md)

**Before Starting:**
- Check if test exists in `/web/tests`
- Report: "Test available" or "Test not available"
- If test exists, fix the responsible layer
- Never modify test to make it pass

**Test Execution:**
- Prove problem with one failing test
- Fix only responsible layer
- Prove fix with same passing test
- Verify database updates
- Report each step

**Test Quality:**
- Success = 100% pass rate
- Tests must verify actual functionality (not just button visibility)
- Must confirm database changes
- Video 3440x1440, snapshot 3440x1440
- Save reports to `web/test-reports/` with working links

**Rules:**
- Do NOT change `playwright.config.ts`
- Do NOT create new spec files if area exists (expand existing)
- Do NOT skip reporting steps
- Link PR to test report HTML

## API Structure

**Base URL:** `/ai/api/`

**Key Endpoints:**
- `POST /ingest/upload` - Upload new document
- `GET /receipts` - List all receipts
- `GET /receipts/{id}` - Get single receipt with full details
- `PUT /receipts/{id}` - Update receipt
- `GET /receipts/monthly-summary` - Aggregated statistics
- `POST /reconciliation/firstcard/import` - Import credit card statement
- `POST /reconciliation/firstcard/match` - Auto-match transactions
- `GET /reconciliation/firstcard/statements` - List statements
- `GET /export/sie` - Export to SIE format (Swedish accounting standard)

## Environment Variables

Key variables in `.env` (see `.env.example`):
- `DB_NAME`, `DB_USER`, `DB_PASS` - MySQL credentials
- `OPENAI_API_KEY` - Required for AI processing
- `JWT_SECRET_KEY` - Authentication
- `STORAGE_DIR` - File storage path
- `ENABLE_REAL_OCR` - Toggle OCR (set to 1)
- `OCR_LANG` - Language for OCR (default: sv)
- `VITE_REFRESH_INTERVAL_SECONDS` - Frontend polling interval

## Common Development Patterns

**Reading Company Name (CORRECT):**
```python
# In Python/SQL
SELECT c.name as company_name
FROM unified_files u
LEFT JOIN companies c ON c.id = u.company_id
WHERE u.id = %s
```

**Routing by Workflow Type:**
```python
# In tasks.py
if file_data.get('workflow_type') == 'creditcard_invoice':
    # Route to AI5/AI6 (FirstCard workflow)
    celery_app.send_task('process_credit_card_statement', ...)
else:
    # Route to AI1-AI4 (Receipt workflow)
    celery_app.send_task('process_receipt', ...)
```

**Frontend API Calls:**
```javascript
// In React components (src/ui/api.js)
// Always use relative paths - nginx handles routing
const response = await fetch('/ai/api/receipts', {
  method: 'GET',
  headers: { 'Content-Type': 'application/json' }
});
```

## Debugging Tips

**Check Celery Worker Logs:**
```bat
docker logs mind2-celery-worker-1
docker logs mind2-celery-worker-wf1-1
docker logs mind2-celery-worker-wf2-1
```

**Check Backend Logs:**
```bat
docker logs mind2-ai-api-1
```

**Check Frontend (Dev):**
```bat
docker logs mind2-mind-web-main-frontend-dev-1
```

**Database Queries:**
```sql
-- Check file status
SELECT id, filename, workflow_type, ocr_status, ai_status
FROM unified_files
ORDER BY created_at DESC LIMIT 10;

-- Check AI processing history
SELECT file_id, ai_stage_name, status, confidence, error_message
FROM ai_processing_history
WHERE file_id = 'XXX'
ORDER BY created_at DESC;
```

## When Reporting Work Complete

1. Verify functionality in appropriate mode:
   - **Development testing:** Use dev server (port 5169) - no rebuild needed
   - **Production testing:** Rebuild with `mind_docker_build_nocache.bat` first

2. Run tests and verify 100% pass rate

3. Check database for expected changes

4. Provide test report link from `web/test-results/html/index.html`

5. Confirm:
   - No mock data added
   - No hardcoded values
   - Database schema followed correctly
   - Ports unchanged
   - Tests not modified to pass

## Additional Documentation

- Full technical plan: `@docs/SYSTEM_DOCS/MIND_TASK_IMPLEMENTATION_REVIEW.md`
- Testing standards: `@docs/TEST_RULES.md`
- Current tasks: `@docs/MIND_TASKS.md`
- Database migrations: `database/migrations/`
