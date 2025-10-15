# Error Report 2025-10-15

**Investigation Date**: 2025-10-15
**System**: Mind2 Document Processing System
**Containers Analyzed**: celery-worker, mysql, ai-api, redis, mind-web-main-frontend-dev, mind-web-main-frontend

---

## Executive Summary

**CRITICAL**: All AI processing pipelines (AI1-AI6) are failing due to incorrect API routing. OpenAI models are being routed through Ollama API endpoint, causing 404 errors and complete AI processing failure.

**Impact**:
- Receipt processing completely blocked after OCR stage
- Credit card invoice parsing failing
- No automatic accounting proposals being generated
- System cannot process any uploaded documents beyond OCR

**Status**: 🔴 PRODUCTION BLOCKING

---

## Critical Errors

### 1. ❌ CRITICAL: AI Model Routing Misconfiguration

**Severity**: 🔴 CRITICAL - BLOCKING ALL AI PROCESSING
**Location**: `backend/src/services/ai_service.py` - Provider selection logic
**Container**: mind2-celery-worker-1

**Problem**:
The system is configured to use OpenAI models (gpt-5, gpt-5-mini) but ALL API calls are being routed through the Ollama API endpoint at `http://host.docker.internal:11435/api/generate`.

**Evidence**:
```
[2025-10-15 04:43:28,247: ERROR/ForkPoolWorker-1] Provider call for document_analysis failed
(provider=OpenAI, model=gpt-5-mini): Ollama API call failed:
404 Client Error: Not Found for url: http://host.docker.internal:11435/api/generate

[2025-10-15 04:43:28,663: ERROR/ForkPoolWorker-1] Provider call for expense_classification failed
(provider=OpenAI, model=gpt-5-mini): Ollama API call failed:
404 Client Error: Not Found for url: http://host.docker.internal:11435/api/generate

[2025-10-15 04:43:28,857: ERROR/ForkPoolWorker-1] Provider call for data_extraction failed
(provider=OpenAI, model=gpt-5): Ollama API call failed:
404 Client Error: Not Found for url: http://host.docker.internal:11435/api/generate
```

**Database Configuration**:
```sql
-- AI Prompts are configured to use OpenAI models:
AI1 (document_analysis)     → model_id=4 (gpt-5-mini) → llm_id=1 (OpenAI)
AI2 (expense_classification) → model_id=4 (gpt-5-mini) → llm_id=1 (OpenAI)
AI3 (data_extraction)        → model_id=5 (gpt-5)      → llm_id=1 (OpenAI)
AI4 (accounting)             → model_id=4 (gpt-5-mini) → llm_id=1 (OpenAI)
AI5 (credit_card_matching)   → model_id=5 (gpt-5)      → llm_id=1 (OpenAI)
AI6 (credit_card_parsing)    → model_id=5 (gpt-5)      → llm_id=1 (OpenAI)
```

**Environment Variables**:
```env
AI_PROVIDER=ollama                                    # ← CONFLICT!
OLLAMA_HOST=http://host.docker.internal:11435        # ← Used for all calls
OPENAI_API_KEY=sk-proj-...                           # ← Available but not used
```

**Root Cause Analysis**:
1. `.env` has `AI_PROVIDER=ollama` which forces ALL calls through Ollama
2. Database has models configured with `llm_id=1` (OpenAI provider)
3. The code is checking `AI_PROVIDER` env var BEFORE checking the database model configuration
4. This causes OpenAI model requests to be sent to Ollama endpoint
5. Ollama returns 404 because it doesn't have endpoints for gpt-5/gpt-5-mini

**Impact**:
- 100% of AI processing tasks failing
- All uploaded receipts stuck at "ocr_complete" status
- Credit card invoices cannot be parsed
- No accounting proposals generated

**Frequency**: Every AI task (continuous failure since last configuration change)

---

### 2. ⚠️ MAJOR: Ollama Container Unhealthy

**Severity**: ⚠️ MAJOR
**Location**: ollama-gpu container
**Container**: ollama-gpu

**Problem**:
```
ollama-gpu: Up 25 hours (unhealthy)
```

The Ollama container is running but marked as unhealthy by Docker health checks.

**Root Cause**:
- Health check is failing (likely on port 11434 vs 11435 mismatch)
- Container is configured to listen on 11434 internally
- Environment points to 11435: `OLLAMA_HOST=http://host.docker.internal:11435`

**Impact**:
- Contributes to routing errors above
- Cannot use Ollama for local model processing even if desired

---

### 3. ⚠️ MINOR: Frontend Proxy Connection Errors (Historical)

**Severity**: ⚠️ MINOR (appears resolved)
**Location**: mind2-mind-web-main-frontend-dev-1
**Container**: mind-web-main-frontend-dev

**Problem**:
```
12:38:36 PM [vite] http proxy error: /receipts/...
Error: connect ECONNREFUSED 172.23.0.3:5000
```

**Status**: Appears to be historical errors from earlier today (12:38 PM). No recent errors in logs.

**Root Cause**: Transient - likely occurred during container restart or network reconfiguration.

**Impact**: None currently - system appears to have recovered

---

### 4. ℹ️ INFO: MySQL sha256_password Deprecation Warnings

**Severity**: ℹ️ INFORMATIONAL
**Location**: mind2-mysql-1
**Container**: mysql

**Problem**:
```
[MY-013360] [Server] Plugin sha256_password reported: 'sha256_password' is deprecated
and will be removed in a future release. Please use caching_sha2_password instead
```

**Root Cause**: MySQL 8.4.6 deprecating sha256_password authentication plugin

**Impact**:
- No functional impact currently
- Will need migration before MySQL 9.0 upgrade

**Recommendation**: Plan migration to caching_sha2_password in future maintenance window

---

### 5. ℹ️ INFO: Celery Running as Root

**Severity**: ℹ️ INFORMATIONAL (dev environment)
**Location**: mind2-celery-worker-1
**Container**: celery-worker

**Problem**:
```
SecurityWarning: You're running the worker with superuser privileges:
this is absolutely not recommended!
Please specify a different user using the --uid option.
```

**Root Cause**: Celery worker running as root inside Docker container

**Impact**:
- Security concern for production
- No functional impact in development

**Recommendation**: Add `--uid` flag in production deployment

---

## Working Systems

✅ **MySQL**: Running normally, no functional errors
✅ **Redis**: Working correctly, background persistence active
✅ **Nginx**: No errors, serving requests properly
✅ **AI-API**: Processing FTP fetches and uploads successfully
✅ **Frontend (Production)**: Serving static files correctly
✅ **Frontend (Dev)**: Vite dev server running with hot-reload on port 5169
✅ **OCR Processing**: PaddleOCR working correctly, processing images successfully

---

## Previous Fixes (from 25-10-15_Worklog.md)

The following issues were identified and fixed earlier today:

✅ **OPENAI_API_KEY Configuration** - Fixed (lines 42, 77 in .env)
✅ **docker-compose.yml environment variables** - Fixed (added OPENAI_API_KEY to services)
✅ **Illegal state transitions in process_invoice_document** - Fixed (duplicate processing prevention)
✅ **OpenAI API timeout too short** - Fixed (increased to 600s with retry logic)
✅ **Currency column in database** - Already fixed via migration 0036

---

## Impact Analysis

### Affected Workflows

🔴 **BLOCKED**:
- Normal receipt processing (AI1-AI4 pipeline)
- Credit card invoice parsing (AI6)
- Expense classification (AI2)
- Accounting proposal generation (AI4)
- Credit card matching (AI5)

✅ **WORKING**:
- File upload
- OCR text extraction
- FTP file fetching
- Database operations
- Frontend UI

### User Impact

**Current State**: Users can upload files and see OCR text extracted, but:
- No automatic classification
- No expense type detection
- No data extraction from receipts
- No accounting proposals
- No credit card invoice processing

**Business Impact**:
- Manual processing required for ALL documents
- 100% productivity loss on AI automation
- Backlog of unprocessed receipts building up

---

## Next Steps

See accompanying solution plan: `ERROR_SOLUTION_PLAN_2025-10-15.md`
