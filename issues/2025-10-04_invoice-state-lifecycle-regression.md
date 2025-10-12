# Invoice state lifecycle regression in new upload endpoints

## Summary
- `/reconciliation/firstcard/upload-invoice` seeds `invoice_documents.status` with the literal string `"processing"`, which is not part of the new `InvoiceDocumentStatus` enum (`imported`, `matching`, `matched`, `partially_matched`, `completed`, `failed`).
- The `processing_status` column is left at its default `uploaded` value; no transition to `ocr_pending` happens after queuing OCR.
- `process_invoice_document` / `process_invoice_matching` are never scheduled, so the new state machine helpers are effectively bypassed.
- `/reconciliation/firstcard/statements` still filters `invoice_type='company_card'`, hiding all uploaded `credit_card_invoice` records from the UI.

## Impact
- State transitions fail: calls to `transition_document_status` / `transition_processing_status` will not match rows starting from `status='processing'`, causing invoices to get stuck.
- Frontend cannot see the newly uploaded invoices, blocking manual review.
- Observability metrics meant to guard transitions will emit illegal state warnings.

## How to Reproduce
1. Upload an invoice via `/reconciliation/firstcard/upload-invoice`.
2. Inspect `invoice_documents` — `status` becomes `processing`, `processing_status` stays `uploaded`.
3. Call `/reconciliation/firstcard/statements` — the uploaded invoice is missing because of the `invoice_type='company_card'` filter.
4. Trigger matching: `transition_document_status` fails because the row is in an illegal starting state.

## Expected
- Upload sets `status` to `imported` (or another enum value) and transitions `processing_status` to `ocr_pending` via `transition_processing_status`.
- OCR completion and downstream tasks trigger `process_invoice_document` / `process_invoice_matching` so the pipeline advances.
- `/reconciliation/firstcard/statements` lists both legacy `company_card` statements and new `credit_card_invoice` uploads.

## Suggested Fix
1. Use the new state helpers immediately after upload: `transition_document_status(..., IMPORTED, (IMPORTED, MATCHING))` and `transition_processing_status(..., OCR_PENDING, (UPLOADED, OCR_PENDING))`.
2. Schedule the invoice-specific Celery tasks when all pages finish OCR (e.g., inside `process_ocr` or an orchestration fan-in).
3. Adjust `/reconciliation/firstcard/statements` to include `invoice_type IN ('company_card','credit_card_invoice')` and expose the new processing metadata.
4. Add regression tests validating state transitions and list responses.

## References
- Issues #17, #18 requirements in docs/SYSTEM_DOCS/MIND_INVOICE_MATCH_IMPLENTATION_TASK_LIST_v.1.0.md.
- Current implementation: backend/src/api/reconciliation_firstcard.py, backend/src/services/tasks.py, backend/src/services/invoice_status.py.
