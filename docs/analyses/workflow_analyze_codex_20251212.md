# Receipt Import Analysis - 2025-12-12 (Codex)

## Inputs reviewed
- SoT files `docs/source_of_truth/00_INDEX.md` .. `90_TEST_AND_QUALITY_STRATEGY.md` (status model, pipelines, encoding)
- Worklog `docs/worklogs/2025-12-12_Worklog.md`
- Backend: `backend/src/api/ingest.py`, `backend/src/services/fetch_ftp.py`, `backend/src/services/tasks/ocr_tasks.py`, `backend/src/services/tasks/workflow_tasks.py`, `backend/src/services/tasks/ai_pipeline_tasks.py`, `backend/src/services/ocr.py`, `backend/src/api/receipts.py`
- Frontend: `main-system/app-frontend/src/ui/pages/Process.jsx`, `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

## SoT expectation (receipts)
- PNG/JPG (single page) -> workflow key WF1_RECEIPT, ai_status sequence uploaded -> processing -> ocr_done -> completed, stage order per SoT (detect_type, r_ocr, r_ai3, r_ai4, r_persist, r_queue_match, finalize_ok, KLAR).
- PDF receipts (single or multi page) -> workflow key WF2_PDF_SPLIT to create page images + OCR, then WF1_RECEIPT on the parent; ai_status must reach completed only after WF1 finalize; workflow_runs.current_stage should end at KLAR with status succeeded.

## Findings vs SoT

### Storage, OCR and preview readiness
- Portal uploads use `FileStorage.save_original` (`backend/src/api/ingest.py`) which stores files under `/storage/originals/<id>` only; `services/ocr.py` and `/ai/api/receipts/<id>/image` look under `/storage/<id>/...`. Result: OCR runs with zero images and previews 404 for portal-uploaded PNG/JPG/PDF parents. SoT requires full OCR and preview for all formats.
- WF2 creates page PNGs under `/storage/<page_id>/page-*.png`, so pages are OCRable, but the parent PDF still has no image at `/storage/<parent_id>` and preview fails for the receipt itself.
- FTP ingest saves files to `/storage/<id>/<filename>` (`backend/src/services/fetch_ftp.py`), so OCR works there; behavior diverges between sources.

### Ingest routing and initial statuses
- Portal ingest sets `initial_ai_status="processing"` and routes by detected kind only (image -> WF1, pdf -> WF2) without ever using the SoT start value `uploaded`.
- FTP ingest always creates WF1 runs and sets `initial_ai_status="ftp_fetched"` (not a SoT value) regardless of file type, so PDF receipts fetched via FTP bypass WF2 splitting that SoT mandates.

### WF2_PDF_SPLIT behavior
- `wf2_merge_ocr_results` sets parent `ocr_raw` and `ai_status=ocr_done`, then marks WF2 finalize_ok which triggers `ai_status=completed` and `workflow_runs.status=succeeded` before WF1 starts. SoT requires completion only after WF1; current implementation reports completed while AI1-AI4 have not run yet.
- Final stage recorded as `finalize`/`finalize_ok_end`; `workflow_runs.current_stage` stays `finalize` (never KLAR). Latest stage string seen by UI becomes `finalize_ok_end succeeded`, not `KLAR klar` per SoT.
- Stage keys include `ocr_page_<n>` etc., which differ from SoT naming (`page_ocr`, `merge_ocr`).

### WF1 receipt pipeline persistence
- OCR stage works only when image files exist under `/storage/<id>` (FTP or WF2 pages); portal uploads have no files there, so OCR result is empty but still marked succeeded and `ai_status=ocr_done` (`wf1_run_ocr`).
- AI3/AI4 pipeline (`_run_ai_pipeline`) logs results but never persists them: no updates to `unified_files` amounts/dates/company_id, no `receipt_items`, no `ai_accounting_proposals`. Columns in Process view therefore remain null and credit card fields stay empty. SoT requires these fields to be populated as part of r_ai3/r_ai4 stages.

### Status tracking and UI surfacing
- Allowed ai_status set extended with `ftp_fetched` and `processing` as starting values; SoT allows only `uploaded` as entry state.
- `workflow_stage_status` in receipt list picks the most recent `workflow_stage_runs` by `started_at`; because final stages are logged as `finalize_ok_end` and KLAR does not update `workflow_runs`, the UI shows raw strings like `finalize_ok_end succeeded` instead of `KLAR klar`, and derived status logic in `/ai/api/queue` does not treat `finalize_ok_end` as completed.
- `workflow_runs.current_stage` never reaches KLAR (stops at finalize), breaking the SoT invariant that successful workflows end at KLAR/succeeded.

### Preview data in UI
- Process view preview (`ReceiptPreview` + `ReceiptPreviewModal`) always calls `/ai/api/receipts/{id}/image`; backend never exposes the `pages` list from WF2 (`other_data.pages` is not returned in any receipt API response), so multi-page navigation stays empty and even single-page previews fail for portal uploads.

## Impact
- Portal-uploaded receipts (PNG/JPG/PDF) appear with empty OCR text, missing amounts/dates/merchant, and no preview; ai_status may be completed despite no AI processing having run.
- PDF receipts fetched via FTP skip WF2 entirely, so multi-page PDFs are treated as single images and may not follow SoT-required split+merge flow.
- Status displays are inconsistent: Process table and queue show `finalize_ok_end succeeded` or stale stages instead of `KLAR klar`, and ai_status derivation in the queue can stay at processing even when finalize_ok_end is the last stage.
- Credit card last-4 and other columns stay blank because AI3/AI4 outputs are not persisted anywhere.

## 2025-12-12 Repair Notes (Codex)

Utfört enligt `docs/bugs/WORFLOW_REPAIR_2025-12-12.md` (steg 1–4), utan scope‑avvikelser.

- `backend/src/api/ingest.py`: vid uppladdning av enkelbild (jpg/jpeg/png/tif/tiff) sparas en extra kopia som `page-0001.<ext>` under `/data/storage/<file_id>/` så OCR/preview hittar exakt 1 bild.
- `backend/src/services/tasks/ocr_tasks.py`: i `wf2_prepare_pdf_pages()` kopieras första sidans PNG (från sidans `file_id`) till parent‑PDFens `/data/storage/<parent_id>/page-0001.png` om parent saknar bild (idempotent).
- `backend/src/api/receipts.py`:
  - `/receipts` listar nu `upload_stage` baserat på tidigaste `src_*`‑stage i `workflow_stage_runs` (inte senaste stage).
  - `/receipts/<rid>/modal` returnerar 200 även när `company_id` saknas, med `company: {}` och varningslogg.

Drift:
- Restart av `ai-api`, `celery-worker`, `celery-worker-wf1`, `celery-worker-wf2` gjord för att ladda in ändringar.

Verifiering:
- `GET /ai/api/receipts/<rid>/modal` för kvitto utan `company_id` returnerar nu 200 (t.ex. `07935e44-828f-4b45-84b6-d47689b30f51`) och modal‑payload innehåller tom `company`‑dict.
- Ingen backfill av redan uppladdade portal‑filer gjordes (ej i scope). Därför kan äldre kvitton fortfarande sakna `/data/storage/<id>/page-0001.*` respektive parent‑preview och ge 404 på `/image` tills de laddas upp på nytt/resumeras.
- Playwright‑test `web/tests/receipt_image_modal_zoom_orientation.spec.ts` fortsätter att faila p.g.a. testdrift: selector `.receipt-modal-overlay` finns inte längre även om modalens innehåll renderas.
