# MIND Endpoints (v2.0)

Base: `/ai/api`

- Auth
  - `POST /auth/login` – issues JWT (HS256)

- System
  - `GET /health` – service probe
  - `GET /system/status` – version, uptime, component reachability, counters
  - `GET /system/stats` – aggregated stats (queue depth, receipts by status, invoice counts)
  - `GET /system/metrics` – Prometheus metrics (text/plain)
  - `GET /system/db-ping` – DB connectivity probe
  - `GET /system/celery-ping` – Celery worker probe
  - `GET/PUT /system/config` – safe config read/update (whitelist)

- Receipts
  - `GET /receipts` – list with filters/pagination
  - `GET /receipts/{id}` – details
  - `PUT|PATCH /receipts/{id}` – update fields
  - `GET /receipts/monthly-summary` – latest month summary
  - `GET /receipts/{id}/line-items` – retrieve stored line items
  - `PUT /receipts/{id}/line-items` – replace stored line items

- Ingest / Processing
  - `POST /ingest/fetch-ftp` – fetch from local/FTP inbox
  - `POST /ingest/queue-new` – enqueue unprocessed receipts
  - `POST /ingest/process/{fid}/ocr` – trigger OCR
  - `POST /ingest/process/{fid}/classify` – trigger classification
  - `POST /capture/upload` – public capture upload (multipart)

- Reconciliation – FirstCard
  - `POST /reconciliation/firstcard/import` – create `invoice_documents` + `invoice_lines`
  - `POST /reconciliation/firstcard/match` – naive matching lines → receipts
  - `GET /reconciliation/firstcard/statements` – list imported statements
  - `POST /reconciliation/firstcard/statements/{id}/confirm` – mark as completed
  - `POST /reconciliation/firstcard/statements/{id}/reject` – reset to imported

- Export
  - `GET /export/sie` – generate SIE for date range (query: `from`, `to`)

Notes
- All admin endpoints require JWT Bearer except `/health` and `/system/metrics`.
- CORS allowed origins configured via `ALLOWED_ORIGINS`.
