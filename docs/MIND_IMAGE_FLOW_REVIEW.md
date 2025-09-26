# MIND Image Flow Review

## Scope & Summary
- Mapped how receipt image files travel from FTP ingestion through to the admin list rendering.
- Identified where previews are generated, how originals are exposed, and where resolution is degraded.
- Proposed changes for an optimal end-to-end pipeline that reliably delivers high resolution assets on demand.

## Current Flow (September 2025)

### 1. FTP Ingestion
- `POST /ai/api/ingest/fetch-ftp` delegates to `services.fetch_ftp.fetch_from_ftp()` (`backend/src/services/fetch_ftp.py:300`).
- The module loads JSON sidecar metadata before downloading the binary, generates a `file_id` (uuid4), and persists the original via `FileStorage.save()` (`backend/src/services/storage.py:24`).
- Files are written to `STORAGE_DIR/<file_id>/<original_filename>` and metadata is inserted into `unified_files`, `file_tags`, `file_locations` when present (`backend/src/services/fetch_ftp.py:103-218`).

### 2. Storage Layout
- `FileStorage` guards against traversal and creates one directory per receipt id (`backend/src/services/storage.py:12-22`).
- OCR artefacts (line items, boxes) live under `STORAGE_DIR/line_items` (`backend/src/api/receipts.py:16-34`).
- Preview thumbnails are stored as JPEG at `STORAGE_DIR/previews/<receipt_id>.jpg` (`backend/src/api/receipts.py:35-115`).

### 3. Preview Generation
- `_ensure_preview()` locates the first `.jpg`, `.jpeg`, or `.png` in the receipt folder and regenerates the cached preview when required (`backend/src/api/receipts.py:48-115`).
- `_generate_preview()` opens the source with Pillow, applies EXIF orientation, forces portrait rotation if width > height, resizes to max 320px, and re-encodes at quality 85 (`backend/src/api/receipts.py:61-101`).

### 4. Delivery Endpoints
- `GET /ai/api/receipts/<id>/preview` returns the cached 320px JPEG and honours `refresh=true` to drop the cache before regenerating (`backend/src/api/receipts.py:556-574`).
- `GET /ai/api/receipts/<id>/image` opens the original with Pillow, applies EXIF transpose, optionally rotates to portrait, downscales when `size` is provided, and always re-encodes the response as JPEG (`backend/src/api/receipts.py:485-551`).
  - `size=preview|thumbnail|max:<N>` limits the longest side.
  - `quality=high|normal|low` maps to JPEG quality 100, 95, or 80.
  - `rotate=portrait|auto|none` controls the forced rotation (default `auto`).

### 5. Admin Frontend Usage
- The receipts page fetches list data from `/ai/api/receipts` and renders `ReceiptPreview` (start at `main-system/app-frontend/src/ui/pages/Receipts.jsx:378`).
- `usePreviewImage()` sequentially tries `preview_url?refresh=true`, `/preview?refresh=true`, and finally `/image` (`main-system/app-frontend/src/ui/pages/Receipts.jsx:315-352`). Each successful fetch is wrapped in a `URL.createObjectURL` for the thumbnail.
- Clicking a row calls `handlePreview`, which initialises state with the cached thumbnail and kicks off a fetch loop prioritising `/image?quality=high&size=full&rotate=portrait` (`main-system/app-frontend/src/ui/pages/Receipts.jsx:849-934`). If that request fails, the modal silently keeps showing the low resolution preview.
- Downloads reuse `/ai/api/receipts/<id>/image` without parameters, so the browser receives the Pillow-generated JPEG instead of the raw original (`main-system/app-frontend/src/ui/pages/Receipts.jsx:888-907`).

## Identified Issues
- **Original files are always re-encoded as JPEG.** The `/image` endpoint discards the source format even in the `size=full` path, causing visible quality loss for PNG or high quality JPEG originals (`backend/src/api/receipts.py:519-551`).
- **Forced portrait rotation.** The automatic 90 degree rotation for any landscape source can break attachments that are meant to stay landscape.
- **Preview regeneration on every render.** `usePreviewImage()` passes `refresh=true` for each mount, forcing `_ensure_preview()` to delete and rebuild the cached thumbnail repeatedly, creating unnecessary I/O and CPU churn (`main-system/app-frontend/src/ui/pages/Receipts.jsx:324-327`).
- **Silent fallback in the modal.** When `/image?quality=high&size=full` fails, the user keeps seeing the 320px thumbnail with no warning, matching the reported “preview only” behaviour.
- **No cache headers.** Both `/preview` and `/image` responses omit `Cache-Control` and validation headers, preventing downstream caching.
- **Single resolution pipeline.** The system generates only one derivative (320px). The modal relies on the same heavy `/image` endpoint that is also used for downloads, rather than a mid-sized asset optimised for display.

## Proposed Improvements

### Backend
1. **Expose untouched originals.** Add a `format=original` (or `quality=original`) flag to `/receipts/<id>/image` that streams the stored file via `send_file` without Pillow re-encoding when `size` is `full`.
2. **Multi-size derivatives.** Generate `thumb` (320px) and `medium` (e.g. 1200px) variants immediately after FTP import and persist them under `STORAGE_DIR/derivatives/<size>/<id>.jpg`. Use those for list and modal rendering while keeping the raw file for downloads.
3. **Configurable rotation.** Restrict forced portrait rotation to derived thumbnails, and honour the original orientation for the raw/medium outputs.
4. **Caching metadata.** Set `Last-Modified`/`ETag` on `/preview` and `/image` based on the source mtime to enable browser caching.
5. **Error telemetry.** Log Pillow exceptions with the receipt id and return structured JSON so the frontend can warn users when full quality could not be produced.

### Frontend
1. **Stop unconditional refreshes.** Cache the preview URLs and call `?refresh=true` only when the backend marks a receipt as stale or when the user explicitly requests a refresh.
2. **Prefer new medium/original endpoints.** For the modal, request `format=original` (or `size=medium`), and surface an inline warning whenever the high resolution fetch falls back to the thumbnail.
3. **Use `srcset` and decoding hints.** Provide both thumbnail and medium URLs so the browser picks the right asset at different zoom levels.
4. **Lifecycle hygiene.** Ensure object URLs are revoked only after replacement to avoid flicker and memory leaks.

### Operational
- Schedule a watchdog job that verifies each receipt has the required derivatives and records resolution metadata in `unified_files`.
- Add metrics for preview generation latency and high resolution fetch failures to catch regressions early.

## Recommended Next Steps
1. Implement the backend flag for original streaming and update the modal to consume it.
2. Refactor `usePreviewImage()` to avoid `refresh=true` unless the preview is explicitly invalidated.
3. Introduce a post-import job (Celery or cron) that builds `thumb` and `medium` derivatives and stores width/height metadata.
4. Add HTTP caching headers and wire up synthetic monitoring to observe latency and error rates for `/preview` and `/image`.
5. Extend the existing Playwright suite (`main-system/app-frontend/tests/receipt-image-full-test.spec.ts`) to assert that the modal receives a full resolution asset once the new pipeline is in place.

