# API Documentation

For endpoint schemas and request/response examples, see OpenAPI contracts in `specs/001-mind-system-receipt/contracts/`.

Key endpoints (admin-facing):
- `GET /ai/api/receipts` - list receipts
- `GET /ai/api/receipts/{id}` - get receipt details
- `POST /ai/api/reconciliation/firstcard/import` - import statement
- `GET /ai/api/export/sie` - export SIE for date range
- `GET /ai/api/system/metrics` - Prometheus metrics (text/plain)

Auth: JWT Bearer (see `backend/src/api/middleware.py`).
