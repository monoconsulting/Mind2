# docs/source_of_truth/55_API_AND_ENDPOINTS.md

# Mind – API and Endpoints (Source of Truth)

> This file documents all API endpoints, their contracts, and authentication requirements. If an endpoint exists in code but is not documented here, it must be added.
>
> Version: 2025-12-14.2

## 1. Overview

Mind exposes a REST API via Flask, proxied through Nginx. All endpoints are prefixed with `/ai/api/` by the Nginx reverse proxy.

**Base URL:** `http://localhost:8008/ai/api/`
**Internal URL:** `http://ai-api:5000/` (Docker network only)

## 2. Authentication

Most endpoints require JWT authentication via the `Authorization` header:
```
Authorization: Bearer <token>
```

Authentication is enforced via `api.middleware.auth_required` decorator.

**Public endpoints (no auth):**
- `GET /health`
- `POST /auth/login`

## 3. System & Health Endpoints

### 3.1 Health Check

```
GET /health
```
Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-04T10:00:00Z"
}
```

### 3.2 System Status

```
GET /system/status
```
Returns detailed status of all components.

**Response:**
```json
{
  "api": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "available"
}
```

### 3.3 Database Statistics

```
GET /system/db-stats
```
Returns database statistics.

### 3.4 Database Ping

```
GET /system/db-ping
```
Checks database connectivity.

### 3.5 Celery Ping

```
GET /system/celery-ping
```
Pings Celery workers.

### 3.6 Prometheus Metrics

```
GET /system/metrics
```
Exposes Prometheus-format metrics.

### 3.7 System Configuration

```
GET /system/config
PUT /system/config  (requires auth)
```
Retrieve or upda### 3.8 Apply Migrations (Manual Trigger)

```
POST /system/apply-migrations
```

Manually triggers the database migration runner.

**Auth:** No (currently unauthenticated in code).  
**Use with care:** This endpoint executes SQL files from `database/migrations/`.

#### Response (200)

```json
{
  "ok": true,
  "mode": "apply",
  "applied": ["0044_create_schema_migrations.sql"],
  "baseline_marked": [],
  "skipped_changed": [],
  "skipped_destructive": [],
  "available": ["0001_...", "..."]
}
```

#### Error Response (500)

```json
{
  "ok": false,
  "error": "..."
}
```

#### Critical Safety Rules (Source of Truth)

- Migrations must be **idempotent** and must never destroy user data on re-run.
- Seeding (including prompts in `ai_system_prompts`) must **not overwrite** any content that has been edited via UI/API.

#### Current Implementation Note (Critical)

As of 2025-12-14, the migration runner **tracks applied migrations** in `schema_migrations` and will only execute migrations that are not yet recorded in the ledger.

For existing databases created before the ledger existed, the runner supports **baseline marking**:
- **Explicit baseline:** set `DB_MIGRATIONS_BASELINE=1` and call this endpoint once.
- **Auto baseline:** allowed only when `schema_migrations` is missing/uninitialized **and** the DB passes the provisioned sanity-check.

If the DB is partially migrated (ledger missing/uninitialized but schema signatures are missing), the runner will **refuse to replay** migrations and return an error with the missing signatures and a hint for the required catch-up migration(s).

See `80_OPERATIONS_RUNBOOK.md` → “Migrations & Prompt Persistence” for the current list of known destructive migrations and operational mitigations.


## 4. Authentication Endpoints (`/auth`)

### 4.1 Login

```
POST /auth/login
```
**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```
**Response:**
```json
{
  "token": "jwt_token_here",
  "expires_in": 3600
}
```

### 4.2 Get Current User

```
GET /auth/me
```
Returns authenticated user profile.

## 5. Ingest Endpoints (`/ingest`)

### 5.1 Upload File

```
POST /ingest/upload
```
Upload a new document for processing.

**Request:** `multipart/form-data`
- `file`: The document file (PDF, image)
- `company_id`: (optional) Company ID

**Response:**
```json
{
  "file_id": "uuid",
  "filename": "receipt.pdf",
  "status": "uploaded",
  "workflow_type": "receipt"
}
```

### 5.2 Fetch from FTP

```
POST /ingest/fetch-ftp
```
Trigger FTP fetch for new files.

### 5.3 Resume Processing

```
POST /ingest/process/{id}/resume
```
Resume processing for a file that was paused or failed.

**Path Parameters:**
- `id`: Unified file ID

## 6. Queue Endpoints (`/queue`)

### 6.1 List Workflow Queue

```
GET /queue/
```

Returns the ordered workflow queue.

**Ordering logic**
- Running first (updated_at desc)
- Queued next (created_at desc)
- Others last (updated_at desc)

**Response**
```json
{
  "items": [
    {
      "id": 123,
      "workflow_key": "WF1_RECEIPT",
      "source_channel": "manual_resume",
      "file_id": "uuid",
      "file_name": "receipt_123.jpg",
      "ai_status": "processing",
      "current_stage": "dispatch",
      "status": "running",
      "latest_stage_key": "r_ai3",
      "latest_stage_status": "running",
      "created_at": "2025-12-04T11:30:00Z",
      "updated_at": "2025-12-04T11:30:05Z"
    }
  ],
  "meta": { "total": 42 }
}
```

> Requires authentication (`Authorization: Bearer <token>`).

## 6. Receipt Endpoints (`/receipts`)

### 6.1 List Receipts

```
GET /receipts
```
Returns paginated list of receipts.

**Query Parameters:**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 50, max: 1000)
- `sort_by`: Sort column (whitelist; default: `created_at`)
- `sort_order`: `asc` | `desc` (default: `desc`)
- `ai_status`: Filter by `unified_files.ai_status` (supports negation, e.g. `!completed`)
- `status`: Alias for `ai_status` (backwards compatibility)
- `workflow_stage_key`: Filter by latest workflow stage key
- `workflow_stage_status`: Filter by latest workflow stage status/state
- `match_status`: e.g. `unmatched`
- `upload_stage`: Upload/source stage key prefix (e.g. `src_portal`, `src_ftp`)
- `search`: Broad search across merchant/company, filename, id and status
- `merchant`: Merchant/company name LIKE filter
- `orgnr`: Organisation number filter
- `tags`: Comma-separated ANY-tag filter
- `from`: Purchase datetime/date lower bound (inclusive)
- `to`: Purchase datetime/date upper bound (inclusive)
- `file_type`: Filter by document type (`receipt`, `invoice`, `other`, ...)
- `expense_type`: Filter by expense type (`personal`, `corporate`)
- `payment_type`: Filter by payment type (`card`, `swish`, `cash`)
- `include_credit`: Include credit card statements (`1/true/yes`), default `1` (Process-vyn skickar explicit `include_credit=0`)

**Response:**
```json
{
  "items": [...],
  "meta": {
    "page": 1,
    "page_size": 50,
    "total": 100,
    "items": 50
  }
}
```

### 6.2 Get Receipt

```
GET /receipts/{id}
```
Returns single receipt with full details.

**Response includes:**
- Receipt metadata
- Receipt items
- Accounting proposals
- Processing history
- Workflow stage status

### 6.3 Update Receipt

```
PUT /receipts/{id}
```
Update receipt fields.

**Request:**
```json
{
  "company_id": "uuid",
  "purchase_datetime": "2025-12-04T10:00:00Z",
  "gross_amount": 100.00,
  "net_amount": 80.00,
  "vat_amount": 20.00
}
```

### 6.4 Monthly Summary

```
GET /receipts/monthly-summary
```
Returns aggregated statistics by month.

### 6.5 Soft Delete

```
DELETE /receipts/{id}
```
Soft-deletes a receipt (sets `deleted_at`).

### 6.6 Bulk Update Receipts

```
PATCH /receipts/bulk
```

Bulk update fields for a set of receipts (limited to the current page selection in UI).

**Request:**
```json
{
  "ids": ["uuid-1", "uuid-2"],
  "set": {
    "file_type": "receipt",
    "expense_type": "personal",
    "payment_type": "swish"
  }
}
```

Rules:
- `ids` must be non-empty (max 1000)
- `set` must contain at least one field
- Fields may be set, but not "cleared" (omit the key to leave unchanged)

**Response:**
```json
{
  "updated_count": 2,
  "not_found_ids": []
}
```

### 6.7 Receipt Log (`/receipts/{id}/log`)

```
GET /receipts/{id}/log?latest=1
```

Returns workflow runs, workflow stage history and AI processing history for the requested receipt. Without `latest=1` the endpoint retains its previous behaviour (all workflow runs and AI history). When `latest=1`:

- Only the single most recent `workflow_runs` entry (excluding `WF2_PDF_SPLIT`) is returned.
- Only the stages for that run are included.
- `ai_processing_history` rows are filtered to `created_at >= latest_workflow_run.created_at`.

AI history entries now expose the new `prompt_text` and `response_text` columns (alongside the existing `log_text`, `error_message`, `confidence`, `provider`, `model`, etc.) so callers can display both the short summary and the raw payloads.

Sample response snippet:

```json
{
  "receipt_id": "<uuid>",
  "workflow_runs": [
    {
      "id": 123,
      "workflow_key": "WF1_RECEIPT",
      ...
    }
  ],
  "ai_history": [
    {
      "id": 42,
      "job_type": "ai3",
      "status": "success",
      "created_at": "2025-12-04T15:00:00Z",
      "ai_stage_name": "AI3-DataExtraction",
      "log_text": "Extracted 3 items; items summary: ...",
      "prompt_text": "{... full AI3 prompt ...}",
      "response_text": "{... raw AI3 response ...}"
    }
  ]
}
```

Frontend components should call this endpoint with `latest=1` so the Process log modal can show only the newest run along with its prompt/response payloads.

## 7. FirstCard/Reconciliation Endpoints (`/reconciliation/firstcard`)

### 7.1 Upload Invoice

```
POST /reconciliation/firstcard/upload-invoice
```
Upload a credit card statement for processing.

**Request:** `multipart/form-data`
- `file`: PDF or Excel statement file

### 7.2 List Statements

```
GET /reconciliation/firstcard/statements
```
Returns list of credit card statements.

### 7.3 Get Statement Details

```
GET /reconciliation/firstcard/statements/{id}
```
Returns statement with header and line items.

### 7.4 Get Statement Lines

```
GET /reconciliation/firstcard/statements/{id}/lines
```
Returns transaction lines for a statement.

### 7.10 Get Invoice Detail (Preview + Lines)

```
GET /reconciliation/firstcard/invoices/{invoice_id}
```

Returns a detailed invoice payload (metadata, line items, and preview pages).

**Response (high-level):**
```json
{
  "invoice": {
    "id": "uuid",
    "status": "imported|matching|matched|partially_matched|completed|failed",
    "processing_status": "uploaded|ocr_pending|ocr_done|ai_processing|ready_for_matching|matching_completed|completed|failed",
    "line_counts": { "total": 0, "matched": 0, "unmatched": 0 },
    "pages": [
      { "file_id": "uuid", "page_number": 1, "status": "ocr_done", "url": "/ai/api/receipts/<file_id>/image?size=original&quality=high" }
    ],
    "metadata": {
      "pages": [
        { "file_id": "uuid", "page_number": 1, "status": "ocr_done", "url": "/ai/api/receipts/<file_id>/image?size=original&quality=high" }
      ]
    }
  },
  "lines": [],
  "items": []
}
```

Notes:
- `invoice.pages[]` and `invoice.metadata.pages[]` are provided for frontend preview rendering.
- Each page uses the receipt image endpoint for high-quality rendering.
- `lines[]` entries include currency fields when available: `currency_original`, `amount_original`, `exchange_rate`, `amount_sek` (plus legacy `amount`).
- `items[]` mirrors `lines[]` for backward compatibility and includes the same currency fields.

### 7.11 Get Invoice OCR/Processing Status

```
GET /reconciliation/firstcard/invoices/{invoice_id}/status
```

Returns processing status plus OCR progress, including per-page preview URLs.

### 7.12 List Invoice Lines

```
GET /reconciliation/firstcard/invoices/{invoice_id}/lines
```

Returns paginated invoice lines for the given FirstCard invoice.

Response items include currency fields when available:
- `currency_original`
- `amount_original`
- `exchange_rate`
- `amount_sek`

### 7.13 Line Match Candidates

```
GET /reconciliation/firstcard/lines/{line_id}/candidates?invoice_id=<invoice_id>
```

Returns the line payload plus up to 50 receipt candidates for matching.
The `line` payload includes `amount_sek`, `amount_original`, and `currency_original`.

### 7.5 Auto-Match

```
POST /reconciliation/firstcard/match
```
Trigger automatic matching of transactions to receipts.

### 7.6 Manual Match

```
POST /reconciliation/firstcard/statements/{id}/match
```
Manually match a transaction to a receipt.

**Request:**
```json
{
  "line_id": 123,
  "receipt_id": "uuid"
}
```

### 7.7 Confirm Statement

```
POST /reconciliation/firstcard/statements/{id}/confirm
```
Confirm all matches for a statement.

### 7.8 Resume Processing

```
POST /reconciliation/firstcard/statements/{id}/resume
```
Resume processing for a paused statement.

### 7.9 Restart Processing

```
POST /reconciliation/firstcard/statements/{id}/restart
```
Restart processing from the beginning.

## 8. AI Processing Endpoints (`/ai-processing`)

### 8.1 Classify Document

```
POST /ai-processing/classify/document
```
AI1: Classify document type.

**Request:**
```json
{
  "file_id": "uuid"
}
```

**Response:**
```json
{
  "document_type": "receipt",
  "confidence": 0.95
}
```

### 8.2 Classify Expense

```
POST /ai-processing/classify/expense
```
AI2: Classify expense type (personal/corporate).

### 8.3 Extract Data

```
POST /ai-processing/extract
```
AI3: Extract structured data from document.

### 8.4 Classify Accounting

```
POST /ai-processing/classify/accounting
```
AI4: Assign accounting entries per BAS 2025.

### 8.5 Match Credit Card

```
POST /ai-processing/match/creditcard
```
AI5: Match receipts to credit card transactions.

### 8.6 Batch Process

```
POST /ai-processing/process/batch
```
Process multiple files through AI pipeline.

### 8.7 Get Processing Status

```
GET /ai-processing/status/{file_id}
```
Get AI processing status for a file.

## 9. Export Endpoints (`/export`)

### 9.1 Export SIE

```
GET /export/sie
```
Export data in SIE format (Swedish accounting standard).

**Query Parameters:**
- `company_id`: Company to export
- `from_date`: Start date
- `to_date`: End date

## 10. Company Endpoints (`/companies`)

### 10.1 List Companies

```
GET /companies
```
Returns list of companies.

### 10.2 Get Company

```
GET /companies/{id}
```
Returns company details.

### 10.3 Create Company

```
POST /companies
```
Create new company.

### 10.4 Update Company

```
PUT /companies/{id}
```
Update company details.

## 11. AI Config Endpoints (`/ai-config`)

All endpoints below require authentication.

### 11.1 Get Providers (+ Models)

```
GET /ai-config/providers
```

Returns providers and their configured models.

**Response (200)**

```json
{
  "providers": [
    {
      "id": 1,
      "provider_name": "OpenAI",
      "own_name": "Primary",
      "api_key": "********",
      "endpoint_url": "https://api.openai.com",
      "enabled": true,
      "created_at": "2025-12-14T09:00:00",
      "models": [
        {
          "id": 10,
          "model_name": "gpt-4o-mini",
          "display_name": "GPT-4o mini",
          "is_active": true,
          "created_at": "2025-12-14T09:00:00"
        }
      ]
    }
  ]
}
```

### 11.2 Create Provider (Optional Models)

```
POST /ai-config/providers
```

**Request Body**

```json
{
  "provider_name": "OpenAI",
  "own_name": "Primary",
  "api_key": "...",
  "endpoint_url": "https://api.openai.com",
  "enabled": true,
  "models": [
    {"model_name": "gpt-4o-mini", "display_name": "GPT-4o mini", "is_active": true}
  ]
}
```

### 11.3 Update Provider

```
PUT /ai-config/providers/{provider_id}
```

### 11.4 Delete Provider

```
DELETE /ai-config/providers/{provider_id}
```

### 11.5 Add Model to Provider

```
POST /ai-config/providers/{provider_id}/models
```

**Request Body**

```json
{
  "model_name": "gpt-4o-mini",
  "display_name": "GPT-4o mini",
  "is_active": true
}
```

### 11.6 Delete Model

```
DELETE /ai-config/models/{model_id}
```

### 11.7 Get Prompts

```
GET /ai-config/prompts
```

Returns all prompt rows from `ai_system_prompts` joined with the selected provider/model (if configured).

**Important behavior:** If any known prompt keys are missing, the API inserts defaults for the missing keys (it does not delete existing ones).

### 11.8 Update Prompt

```
PUT /ai-config/prompts/{prompt_id}
```

Updates `ai_system_prompts` (title, description, prompt_content, selected_model_id).

**Request Body**

```json
{
  "title": "AI3 - Data Extraction",
  "description": "Extract receipt header + items",
  "prompt_content": "...",
  "selected_model_id": 10
}
```

### 11.9 Test Provider Connection

```
POST /ai-config/providers/{provider_id}/test
```

Tests connectivity for the provider (e.g., OpenAI model listing). Returns `success=true|false`.

### 11.10 Prompt Persistence – Critical Note

Prompt edits made via `/ai-config/prompts/{prompt_id}` are stored in the database. They must not be overwritten by migrations or by repeated “migration replays”.

See:
- `70_AI_PROMPTS_AND_ROLES.md` → “Prompt Lifecycle”
- `80_OPERATIONS_RUNBOOK.md` → “Migrations & Prompt Persistence”
## 12. Tags Endpoints (`/tags`)

### 12.1 List Tags

```
GET /tags
```
Returns available tags.

### 12.2 Tag File

```
POST /tags/{file_id}
```
Add tag to file.

### 12.3 Remove Tag

```
DELETE /tags/{file_id}/{tag}
```
Remove tag from file.

## 13. Error Responses

All endpoints return standard error format:

```json
{
  "error": "error_code",
  "message": "Human-readable message",
  "details": {}
}
```

**Common Status Codes:**
- `400 Bad Request` – Invalid input
- `401 Unauthorized` – Missing or invalid token
- `403 Forbidden` – Insufficient permissions
- `404 Not Found` – Resource not found
- `500 Internal Server Error` – Server error

## 14. Rate Limiting

Rate limits are applied per endpoint. Current limits defined in `api/limits.py`.

## 15. Pagination

Paginated endpoints support:
- `page`: Page number (1-indexed)
- `per_page`: Items per page (max: 100)

Response includes:
- `items`: Array of results
- `total`: Total count
- `page`: Current page
- `per_page`: Items per page
- `pages`: Total pages

## 16. Governance

- New endpoints must be added here before or together with implementation.
- Deprecated endpoints should be marked and include migration path.
- Breaking changes require version bump in API path.
