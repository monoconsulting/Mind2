# Invoice OCR pipeline misclassifies receipts

## Summary
- `_get_invoice_parent_id` (backend/src/services/tasks.py:257-268) now returns the file’s `original_file_id` for any file type that isn’t explicitly `"invoice"`. For normal receipts this equals the receipt id, so `process_ocr` treats receipts as invoices, schedules invoice-only tasks, and logs illegal state assertions.
- `transition_processing_status(..., OCR_PENDING, (UPLOADED,))` (backend/src/services/tasks.py:881-886) is too strict. When subsequent invoice pages finish OCR, the invoice is already `OCR_PENDING`, causing repeated illegal-transition warnings.
- Unit test `backend/tests/unit/test_tasks_invoice_pipeline.py` fails to import because of a `pydantic` `decimal_places` constraint error, so the regression isn’t covered by CI.

## Impact
- Receipt OCR is being routed into the invoice AI/matching pipeline, risking duplicate work, bogus state transitions, and incorrect history logs.
- Invoice processing emits continuous illegal-state metrics on multi-page OCR completion.
- Tests don’t run cleanly, so regressions will slip through.

## How to Reproduce
1. On branch `codex/start-work-on-invoice-ocr-pipeline`, upload a receipt or call `process_ocr` on an existing receipt file id.
2. Observe `_get_invoice_parent_id` returning the same id, causing `invoice_id` to be set.
3. Note invoice history entries (`invoice_ocr`) for receipt files and repeated illegal state assertions.

## Expected
- Receipts should remain on the existing receipt pipeline; only invoice files/pages should set `invoice_id` and trigger invoice-specific tasks.
- OCR transitions should accept both `UPLOADED` and `OCR_PENDING` states (and possibly `OCR_DONE`) to avoid redundant warnings.
- Unit tests should import and run successfully.

## Suggested Fix
1. Restrict `_get_invoice_parent_id` so it only resolves invoice parents (e.g., only when `file_type` is `invoice_page`). For other file types, return `None`.
2. Relax the OCR transition guard to include `OCR_PENDING` (and `OCR_DONE` if reprocessing is allowed).
3. Fix the Pydantic constraint issue in `backend/tests/unit/test_tasks_invoice_pipeline.py` so tests execute.

## References
- Branch: `codex/start-work-on-invoice-ocr-pipeline`
- Files: `backend/src/services/tasks.py`, `backend/tests/unit/test_tasks_invoice_pipeline.py`
