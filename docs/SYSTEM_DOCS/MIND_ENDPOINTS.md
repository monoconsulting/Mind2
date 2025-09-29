# MIND — Endpoints Inventory

> Based on code analysis of `backend/src/api/` as of 2025-09-23. All endpoints are prefixed with `/ai/api` by the Nginx proxy, but base paths are shown here as defined in the Flask app.

## System & Health
- `GET /health`: Returns the health status of the `ai-api` service.
- `GET /system/metrics`: Exposes Prometheus metrics.
- `GET /system/db-stats`: Provides statistics from the database, like the count of unified files.
- `GET /system/db-ping`: Checks database connectivity.
- `GET /system/status`: Returns a detailed status of the service and its components (DB, Redis, Celery).
- `GET /system/stats`: Provides detailed statistics about queues, receipts, and invoices.
- `GET /system/config`: Retrieves the current system configuration.
- `PUT /system/config`: Updates the system configuration (requires auth).
- `POST /system/apply-migrations`: Manually triggers database migrations.
- `GET /system/celery-ping`: Pings the Celery worker to check for availability.

## Authentication (`/auth`)
- `POST /auth/login`: Authenticates a user and returns a JWT.
- `POST /auth/logout`: (Assumed, standard practice) Logs out the user.
- `GET /auth/me`: (Assumed, standard practice) Retrieves the current user's profile.

## Receipts (`/receipts`)
- Endpoints for managing receipts (upload, retrieve, update, delete). Specific routes are defined in `api/receipts.py`.

## Ingest (`/ingest`)
- `POST /ingest/upload`: Endpoint for uploading files for processing.

## Export (`/export`)
- Endpoints for exporting data. Specific routes are defined in `api/export.py`.

## Rules (`/rules`)
- Endpoints for managing accounting or processing rules. Specific routes are defined in `api/rules.py`.

## Tags (`/tags`)
- Endpoints for managing tags on files. Specific routes are defined in `api/tags.py`.

## Reconciliation (`/recon`)
- Endpoints related to company card reconciliation. Specific routes are defined in `api/reconciliation_firstcard.py`.

## Fetcher (`/fetcher`)
- Endpoints for fetching data from external sources. Specific routes are defined in `api/fetcher.py`.

## AI Processing (`/ai`)
### Document Classification
- `POST /ai/classify/document`: AI1 - Classifies document type (receipt, invoice, other, Manual Review).
- `POST /ai/classify/expense`: AI2 - Classifies expense type (personal or corporate).

### Data Extraction
- `POST /ai/extract`: AI3 - Extracts structured data from receipt/invoice to database tables.

### Accounting
- `POST /ai/classify/accounting`: AI4 - Assigns accounting entries according to BAS-2025 chart of accounts.

### Credit Card Reconciliation
- `POST /ai/match/creditcard`: AI5 - Matches receipts with credit card invoice line items.

### Batch Processing & Monitoring
- `POST /ai/process/batch`: Processes multiple files through the AI pipeline in sequence.
- `GET /ai/status/{file_id}`: Retrieves AI processing status for a specific file.

## Admin
- `GET /admin/ping`: A protected endpoint to check for admin authentication.