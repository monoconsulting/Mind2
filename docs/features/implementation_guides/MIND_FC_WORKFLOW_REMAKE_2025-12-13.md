

# Agent Implementation Plan: OCR Quality Boost + FirstCard (FC) PDF Reliability + FC Preview Modal

**Version:** v1.0  
**Scope:** OCR (PaddleOCR) quality-first improvements, more reliable PDF→PNG conversion for receipts + FirstCard invoices, and a minimal FirstCard preview modal (image-only) in the UI.

---

## System Prompt for the Implementing Agent

```text
You are an implementation agent working inside the MIND repository.

Non-negotiable rules:
- Follow the Source-of-Truth (SoT) documents. If code conflicts with SoT, SoT wins.
- Do NOT introduce new behavior outside the scope defined in this task.
- Do NOT refactor unrelated code. No drive-by improvements.
- Do NOT delete existing functionality. If anything must be removed, comment it out and explain why inline.
- Output must be deterministic. Do not invent IDs or data.
- Modify ONLY the files listed in the “Allowed file changes” section (plus .env/.env.example updates).
- Keep existing interfaces intact unless explicitly required by SoT.

Delivery rules:
- For every modified file, replace the entire file content (full rewrite) in the PR.
- Preserve encoding and Swedish characters (UTF-8).
- Ensure all new/changed Python functions and helpers have Google-style docstrings.
- Run the test plan from this document and include evidence in the PR description (logs, screenshots where relevant).

Goal:
Implement the exact changes described in this document, then validate the OCR + FC import + preview modal end-to-end using the provided logs and SoT references.
```

---

## References (must be followed)

- SoT: use the repo’s SoT folder and follow the latest workflow/OCR/FirstCard specs.  
- Test evidence: `@docs/analyses/workflow_analyze_codex_20251212.md` (use it as the baseline to validate the pipeline).  
- FC import failure log: `fc_card_log.md` (included in this task context).


---

## Problem Summary

1) OCR misses content on dense receipts where text becomes readable only after zooming in.  
2) FirstCard invoice import failed with: `Failed to convert credit card PDF to page images.`  
3) UI needs an image-only preview modal for FirstCard invoices (same paging UX as receipt preview, but no fields).


## FC Import Chain and Status Flow Analysis (based on repo docs + fc_card_log)

### End-to-end chain (expected)

1) FirstCard PDF is ingested into `unified_files` as a parent row (kind=pdf or detected_kind=pdf).
2) Credit card workflow task (`parse_credit_card_statement`) ensures:
   - The parent is in the correct status for conversion.
   - PDF bytes are read from storage.
3) PDF→PNG conversion (`pdf_to_png_pages`) renders each page to `page-XXXX.png` and returns a list of page paths.
4) For each rendered page:
   - A child `unified_files` row is created via `create_unified_file(...)`
   - `other_data.page_number` is set
   - `other_data.source_file_id` points back to the parent PDF
5) OCR is queued for each child page and progresses through statuses (OCR_PENDING → OCR_DONE), then AI extraction as defined in SoT.

### What the failure log shows (fc_card_log.md)

- The pipeline reached conversion but aborted with:
  `Failed to convert credit card PDF to page images.`
- This error is thrown when `pdf_to_png_pages(...)` returns an empty list (no rendered pages) or when conversion raises.

Typical root causes:

- `fitz`/PyMuPDF missing inside the backend runtime.
- DPI too high for a specific PDF (memory/timeouts) causing conversion to fail or return no pages.
- Corrupt or unsupported PDF.

### Fixes implemented by the code below

1) **Configurable DPI** (`OCR_PDF_DPI`) for both receipt PDF conversion and FirstCard PDF conversion.
2) **Deterministic DPI fallback ladder**:
   - Try configured DPI first.
   - If conversion fails or returns no pages, retry 300 → 250 → 200 → 150.
   - The used DPI is persisted into history (`model_name=fitz-dpi-<used>`).
3) **Child-page `source` propagation**:
   - `create_unified_file(...)` requires a `source=` kwarg.
   - The code now passes `source=other_data.get("source")` from the parent `unified_files.other_data`.
4) **Preview data completeness**:
   - `GET /ai/api/reconciliation/firstcard/invoices/<id>` now includes `pages[]` with `url` so the frontend can render images without guessing endpoints.

### Status flow (high-level)

- The repo already documents the FirstCard status flow (`docs/FIRSTCARD_STATUS_FLOW.md`).
- The preview modal and status endpoint changes do **not** alter status transitions; they only:
  - increase conversion robustness, and
  - expose page preview URLs to the UI.



---

## Allowed File Changes (hard scope)

Backend:

- `backend/src/services/ocr.py`
- `backend/src/services/tasks/ocr_tasks.py`
- `backend/src/services/tasks/creditcard_tasks.py`
- `backend/src/api/reconciliation_firstcard/routes/status.py`

Frontend:

- `main-system/app-frontend/src/ui/components/DocumentPreviewModal.jsx`
- `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

Config/docs:

- Update `.env` and `.env.example` only to expose new OCR controls (no other changes).


---

## Implementation Goals

### A) OCR (PaddleOCR) Quality-First

- Add environment-controlled scaling of input images before OCR.
- Add deterministic fallback passes:
  - Zoom pass (upscale) when text looks too small / too little extracted.
  - Optional tiled OCR as a last resort.
- Expose controls via `.env` (defaults in code remain safe and quality-first).

### B) PDF → PNG Conversion Reliability (Receipts + FirstCard)

- Make PDF conversion DPI configurable via `.env`.
- Add a deterministic DPI fallback ladder on conversion failure: try configured DPI, then 300/250/200/150.
- Ensure logging/history reflects the actually used DPI.

### C) FirstCard Preview Modal

- Backend: include `pages[]` with `url` in `GET /ai/api/reconciliation/firstcard/invoices/<id>`.
- Frontend: add a minimal image-only modal with paging + zoom.
- Add a Preview button in the FirstCard invoice list/table (CompanyCard).


---

## New / Extended `.env` Keys

Add these keys (values shown are quality-first recommendations; defaults are also coded):

```bash
# OCR Settings (existing)
OCR_LANG=sv
OCR_USE_ANGLE_CLS=true
OCR_SHOW_LOG=false

# OCR Quality (new)
OCR_INPUT_LONG_SIDE=4500
OCR_INPUT_MAX_LONG_SIDE=6500

OCR_ZOOM_ENABLED=true
OCR_ZOOM_FACTOR=2.0

# If median box height (px) is below this, zoom pass is triggered (also triggers on too little text/boxes).
OCR_MIN_BOX_HEIGHT_PX=12
OCR_FALLBACK_MIN_CHARS=80
OCR_FALLBACK_MIN_BOXES=15

# Tile fallback (last resort)
OCR_TILE_ENABLE=true
OCR_TILE_GRID=2
OCR_TILE_OVERLAP=0.15

# Paddle detection resize behavior
OCR_DET_LIMIT_SIDE_LEN=4096
OCR_DET_LIMIT_TYPE=max

# PDF → PNG render DPI (new)
OCR_PDF_DPI=450

```

---

## Dependency Check (must run before coding)

Inside the backend container:

```bash
python -c "import paddle; print('paddle', getattr(paddle,'__version__','?'))" || true
python -c "import paddleocr; print('paddleocr', getattr(paddleocr,'__version__','?'))" || true
python -c "import fitz; print('pymupdf/fitz OK')" || true

```

- If `fitz` is missing, PDF conversion will fail (this directly matches the FC failure log).
- PaddleOCR major versions may differ in supported init args; the code below is defensive.


---

## Code Changes

### File: `backend/src/services/ocr.py`

```python
from __future__ import annotations

import json
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:
    from paddleocr import PaddleOCR  # type: ignore
except Exception:  # pragma: no cover
    PaddleOCR = None  # type: ignore


_OCR_ENGINE: Optional["PaddleOCR"] = None

def _env_bool(key: str, default: bool) -> bool:
    """Read a boolean environment variable.

    The value is considered truthy if it matches one of: "true", "1", "t", "yes", "y", "on"
    (case-insensitive). Any other non-empty value is treated as false.

    Args:
        key: Environment variable name.
        default: Default value if the variable is missing or empty.

    Returns:
        Parsed boolean value.
    """
    raw = os.getenv(key)
    if raw is None:
        return default
    raw = str(raw).strip().lower()
    if raw == "":
        return default
    return raw in {"true", "1", "t", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    """Read an integer environment variable.

    Args:
        key: Environment variable name.
        default: Default value if missing or invalid.

    Returns:
        Parsed integer value.
    """
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    """Read a float environment variable.

    Args:
        key: Environment variable name.
        default: Default value if missing or invalid.

    Returns:
        Parsed float value.
    """
    raw = os.getenv(key)
    if raw is None:
        return default
    try:
        return float(str(raw).strip())
    except Exception:
        return default


def _clamp_int(value: int, *, min_value: int, max_value: int) -> int:
    """Clamp an integer into a closed interval.

    Args:
        value: Value to clamp.
        min_value: Inclusive minimum.
        max_value: Inclusive maximum.

    Returns:
        Clamped value.
    """
    return max(min_value, min(max_value, value))


def _receipt_dir(base: str | Path, receipt_id: str) -> Path:
    return Path(base).resolve() / receipt_id


def _write_boxes(base: str | Path, receipt_id: str, boxes: List[Dict[str, Any]]) -> None:
    root = _receipt_dir(base, receipt_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "ocr_boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_line_items(base: str | Path, receipt_id: str, line_items: List[Dict[str, Any]]) -> None:
    root = _receipt_dir(base, receipt_id)
    line_items_dir = root.parent / "line_items"
    line_items_dir.mkdir(parents=True, exist_ok=True)
    (line_items_dir / f"{receipt_id}.json").write_text(json.dumps(line_items, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_images(base: str | Path, receipt_id: str) -> List[Path]:
    root = _receipt_dir(base, receipt_id)
    if not root.exists():
        return []
    return sorted(
        [p for p in root.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}]
    )


def _get_ocr_engine() -> Optional["PaddleOCR"]:
    """Create (or reuse) a PaddleOCR engine instance.

    This function is intentionally defensive to support multiple PaddleOCR versions.
    It prefers quality-first settings and exposes key toggles through environment variables.

    Environment variables:
        OCR_LANG: PaddleOCR language code, e.g. "sv" or "sv+en".
        OCR_USE_ANGLE_CLS: Whether to enable the angle classifier.
        OCR_SHOW_LOG: Whether to enable PaddleOCR internal logging (if supported by the installed version).
        OCR_DET_LIMIT_SIDE_LEN: Detection resize limit (pixels).
        OCR_DET_LIMIT_TYPE: "max" or "min" behavior for the detection resize limit.

    Returns:
        A cached PaddleOCR engine instance, or None if PaddleOCR is unavailable.
    """
    import logging

    logger = logging.getLogger(__name__)

    global _OCR_ENGINE
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE

    if PaddleOCR is None:
        logger.error("OCR: PaddleOCR import failed; engine not available.")
        return None

    lang = os.getenv("OCR_LANG", "sv")
    use_angle_cls = _env_bool("OCR_USE_ANGLE_CLS", True)
    show_log = _env_bool("OCR_SHOW_LOG", False)

    det_limit_side_len = _env_int("OCR_DET_LIMIT_SIDE_LEN", 4096)
    det_limit_side_len = _clamp_int(det_limit_side_len, min_value=960, max_value=10000)
    det_limit_type = os.getenv("OCR_DET_LIMIT_TYPE", "max").strip().lower()
    if det_limit_type not in {"min", "max"}:
        det_limit_type = "max"

    # Log runtime versions to make future upgrades deterministic and auditable.
    try:
        import paddle  # type: ignore

        logger.info("OCR: paddle version=%s", getattr(paddle, "__version__", "unknown"))
    except Exception:
        logger.info("OCR: paddle version=unknown (import failed)")
    try:
        import paddleocr  # type: ignore

        logger.info("OCR: paddleocr package version=%s", getattr(paddleocr, "__version__", "unknown"))
    except Exception:
        logger.info("OCR: paddleocr package version=unknown (import failed)")

    logger.info(
        "OCR: Initializing PaddleOCR(lang=%s, use_angle_cls=%s, det_limit_side_len=%s, det_limit_type=%s, show_log=%s)",
        lang,
        use_angle_cls,
        det_limit_side_len,
        det_limit_type,
        show_log,
    )

    # PaddleOCR has changed init parameters across versions. Build a best-effort init with safe fallbacks.
    init_kwargs: dict[str, Any] = {
        "lang": lang,
        "use_angle_cls": use_angle_cls,
        "det_limit_side_len": det_limit_side_len,
        "det_limit_type": det_limit_type,
    }

    # Some versions support show_log in __init__, some don't.
    if show_log:
        init_kwargs["show_log"] = True

    try:
        _OCR_ENGINE = PaddleOCR(**init_kwargs)
        logger.info("OCR: PaddleOCR initialized successfully with extended kwargs.")
        return _OCR_ENGINE
    except TypeError as exc:
        # Retry without show_log and/or detection limit kwargs (older/newer versions may differ).
        logger.warning("OCR: PaddleOCR init TypeError: %s. Retrying with reduced kwargs.", exc)
    except Exception:
        logger.exception("OCR: Failed to initialize PaddleOCR (unexpected error).")
        _OCR_ENGINE = None
        return None

    reduced_kwargs: dict[str, Any] = {
        "lang": lang,
        "use_angle_cls": use_angle_cls,
    }
    try:
        if show_log:
            reduced_kwargs["show_log"] = True
        _OCR_ENGINE = PaddleOCR(**reduced_kwargs)
        logger.info("OCR: PaddleOCR initialized successfully with reduced kwargs.")
        return _OCR_ENGINE
    except TypeError as exc:
        logger.warning("OCR: PaddleOCR init still failing: %s. Retrying without angle classifier.", exc)
    except Exception:
        logger.exception("OCR: Failed to initialize PaddleOCR with reduced kwargs.")
        _OCR_ENGINE = None
        return None

    try:
        _OCR_ENGINE = PaddleOCR(lang=lang)
        logger.info("OCR: PaddleOCR initialized successfully without angle classifier.")
        return _OCR_ENGINE
    except Exception:
        logger.exception("OCR: Failed to initialize PaddleOCR final fallback.")
        _OCR_ENGINE = None
        return None



def _extract_text_from_images(images: List[Path]) -> Dict[str, Any]:
    """Extract OCR text and bounding boxes from a list of receipt page images.

    This function is quality-first. It supports:
      - Environment-controlled image scaling before OCR (to preserve small text).
      - A deterministic fallback "zoom pass" when detected text appears too small.
      - Optional tiled OCR (grid + overlap) as a last-resort for very dense/small text.

    Environment variables:
        OCR_USE_ANGLE_CLS: Enables angle classification if supported (also passed to the ocr() call as cls=...).
        OCR_INPUT_LONG_SIDE: Target long side (pixels) for OCR input preparation.
        OCR_INPUT_MAX_LONG_SIDE: Maximum allowed long side (pixels) to avoid excessive memory usage.
        OCR_ZOOM_ENABLED: Enables the zoom fallback pass.
        OCR_ZOOM_FACTOR: Scale multiplier applied for the zoom fallback pass.
        OCR_MIN_BOX_HEIGHT_PX: Median box height (px) below which the zoom pass is triggered.
        OCR_FALLBACK_MIN_CHARS: Minimum extracted character count before considering fallback.
        OCR_FALLBACK_MIN_BOXES: Minimum extracted box count before considering fallback.
        OCR_TILE_ENABLE: Enables tiled OCR fallback.
        OCR_TILE_GRID: Grid size for tiling (2 => 2x2 tiles, 3 => 3x3 tiles).
        OCR_TILE_OVERLAP: Fractional overlap per tile (0.0 - 0.5).

    Args:
        images: List of image file paths (one per page) to OCR.

    Returns:
        Dictionary with keys:
            text: Combined OCR text.
            boxes: List of normalized bounding boxes with text.
            merchant: Extracted merchant (best-effort).
            gross: Extracted total amount (best-effort).
            purchase_datetime: Extracted purchase date/time (best-effort).
            vat_breakdown: Extracted VAT breakdown (best-effort).
            line_items: Extracted line items (best-effort).
    """
    import logging
    import math
    import statistics

    logger = logging.getLogger(__name__)

    full_text: List[str] = []
    boxes: List[Dict[str, Any]] = []

    engine = _get_ocr_engine()
    if not images or Image is None:
        logger.warning("OCR: No images or PIL not available. Images: %s", len(images) if images else 0)
        return {
            "text": "",
            "boxes": [],
            "merchant": None,
            "gross": None,
            "purchase_datetime": None,
            "vat_breakdown": {},
            "line_items": [],
        }

    if engine is None:
        logger.error("OCR: PaddleOCR engine not available - cannot process images")
        return {
            "text": "",
            "boxes": [],
            "merchant": None,
            "gross": None,
            "purchase_datetime": None,
            "vat_breakdown": {},
            "line_items": [],
        }

    use_angle_cls = _env_bool("OCR_USE_ANGLE_CLS", True)

    input_long_side = _env_int("OCR_INPUT_LONG_SIDE", 4500)
    input_max_long_side = _env_int("OCR_INPUT_MAX_LONG_SIDE", 6500)
    input_long_side = _clamp_int(input_long_side, min_value=960, max_value=15000)
    input_max_long_side = _clamp_int(input_max_long_side, min_value=input_long_side, max_value=20000)

    zoom_enabled = _env_bool("OCR_ZOOM_ENABLED", True)
    zoom_factor = _env_float("OCR_ZOOM_FACTOR", 2.0)
    min_box_height_px = _env_int("OCR_MIN_BOX_HEIGHT_PX", 12)

    fallback_min_chars = _env_int("OCR_FALLBACK_MIN_CHARS", 80)
    fallback_min_boxes = _env_int("OCR_FALLBACK_MIN_BOXES", 15)

    tile_enable = _env_bool("OCR_TILE_ENABLE", True)
    tile_grid = _env_int("OCR_TILE_GRID", 2)
    tile_grid = _clamp_int(tile_grid, min_value=2, max_value=4)
    tile_overlap = _env_float("OCR_TILE_OVERLAP", 0.15)
    tile_overlap = max(0.0, min(0.5, tile_overlap))

    def _call_engine_ocr(img_path: Path) -> list[Any]:
        """Call engine.ocr() in a version-tolerant way."""
        try:
            return engine.ocr(str(img_path), cls=use_angle_cls) or []
        except TypeError:
            return engine.ocr(str(img_path)) or []

    def _parse_ocr_result(
        *,
        ocr_result: list[Any],
        image_width: int,
        image_height: int,
        scale_to_original: float,
        offset_x: int = 0,
        offset_y: int = 0,
        base_width: int | None = None,
        base_height: int | None = None,
    ) -> tuple[list[str], list[dict[str, Any]], list[float], list[float]]:
        """Parse PaddleOCR results into text lines and normalized boxes.

        Args:
            ocr_result: Raw PaddleOCR result list.
            image_width: Width of the image passed to OCR (tile or full prepared image).
            image_height: Height of the image passed to OCR.
            scale_to_original: Scale factor from OCR image coordinates to original image coordinates.
                If OCR image is a resized version of original, use that resize scale.
                Original_px = OCR_px / scale_to_original.
            offset_x: X offset (in OCR image coordinates) if parsing a tile.
            offset_y: Y offset (in OCR image coordinates) if parsing a tile.
            base_width: Width of the full prepared image (for tile coordinate normalization).
            base_height: Height of the full prepared image.

        Returns:
            A tuple of:
                - text_lines: list of extracted text snippets
                - out_boxes: list of box dicts normalized to original image dimensions
                - heights_px: list of box heights in original pixels
                - confidences: list of confidence values (0..1) when available
        """
        text_lines: list[str] = []
        out_boxes: list[dict[str, Any]] = []
        heights_px: list[float] = []
        confidences: list[float] = []

        # Fallback for normalization when parsing tiles: normalize based on the full prepared image size.
        norm_w = base_width if base_width is not None else image_width
        norm_h = base_height if base_height is not None else image_height

        def append_detection(text_value: Any, polygon: Any, confidence: Any) -> None:
            if text_value is None or polygon is None:
                return
            try:
                text_str = str(text_value).strip()
            except Exception:
                text_str = str(text_value)
            if not text_str:
                return

            # polygon is expected to be list of points: [[x,y], [x,y], [x,y], [x,y]]
            points: list[tuple[float, float]] = []
            try:
                for pt in polygon:
                    if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                        continue
                    points.append((float(pt[0]) + float(offset_x), float(pt[1]) + float(offset_y)))
            except Exception:
                return
            if len(points) < 2:
                return

            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            x1, x2 = min(xs), max(xs)
            y1, y2 = min(ys), max(ys)

            # Map to original pixel coordinates when OCR is running on resized images.
            orig_x1 = x1 / scale_to_original
            orig_y1 = y1 / scale_to_original
            orig_x2 = x2 / scale_to_original
            orig_y2 = y2 / scale_to_original

            # Normalize to original image dimensions (scale_to_original was derived from original).
            # We compute original w/h by reversing scale on the normalization dimensions as well.
            orig_w = norm_w / scale_to_original
            orig_h = norm_h / scale_to_original
            if orig_w <= 0 or orig_h <= 0:
                return

            x_norm = orig_x1 / orig_w
            y_norm = orig_y1 / orig_h
            w_norm = (orig_x2 - orig_x1) / orig_w
            h_norm = (orig_y2 - orig_y1) / orig_h

            x_norm = max(min(x_norm, 1.0), 0.0)
            y_norm = max(min(y_norm, 1.0), 0.0)
            w_norm = max(min(w_norm, 1.0), 0.0)
            h_norm = max(min(h_norm, 1.0), 0.0)

            text_lines.append(text_str)

            conf_val: float | None = None
            try:
                if confidence is not None:
                    conf_val = float(confidence)
            except Exception:
                conf_val = None

            if conf_val is not None:
                confidences.append(conf_val)

            # Box height in original pixels for "small text" detection.
            heights_px.append(float(orig_y2 - orig_y1))

            out_boxes.append(
                {
                    "field": text_str,
                    "confidence": conf_val,
                    "x": x_norm,
                    "y": y_norm,
                    "w": w_norm,
                    "h": h_norm,
                }
            )

        for ocr_result_item in ocr_result:
            handled = False
            if hasattr(ocr_result_item, "json"):
                result_data = getattr(ocr_result_item, "json", None)
                if result_data and isinstance(result_data, dict):
                    res = result_data.get("res")
                    if isinstance(res, dict):
                        rec_texts = res.get("rec_texts", [])
                        rec_polys = res.get("rec_polys", [])
                        rec_scores = res.get("rec_scores", [])
                        for i, text_value in enumerate(rec_texts):
                            if i >= len(rec_polys):
                                continue
                            polygon = rec_polys[i]
                            confidence = rec_scores[i] if i < len(rec_scores) else None
                            append_detection(text_value, polygon, confidence)
                        handled = True
            if handled:
                continue

            sequence: list[Any] = []
            if isinstance(ocr_result_item, (list, tuple)):
                sequence = list(ocr_result_item)
            elif isinstance(ocr_result_item, dict):
                sequence = [ocr_result_item]
            else:
                continue

            for line in sequence:
                if isinstance(line, dict):
                    polygon = line.get("points") or line.get("polygon") or line.get("box")
                    text_value = line.get("text") or line.get("value") or line.get("field")
                    confidence = line.get("score") or line.get("confidence")
                    append_detection(text_value, polygon, confidence)
                    continue

                if not isinstance(line, (list, tuple)) or len(line) < 2:
                    continue

                polygon = line[0]
                info = line[1]
                text_value = None
                confidence = None
                if isinstance(info, (list, tuple)):
                    if len(info) >= 1:
                        text_value = info[0]
                    if len(info) >= 2:
                        confidence = info[1]
                elif isinstance(info, dict):
                    text_value = info.get("text") or info.get("value") or info.get("field")
                    confidence = info.get("score") or info.get("confidence")
                else:
                    text_value = info
                append_detection(text_value, polygon, confidence)

        return text_lines, out_boxes, heights_px, confidences

    def _prepare_scaled_image(original_path: Path, *, target_long_side: int, tag: str) -> tuple[Path, float, int, int]:
        """Create a deterministic resized copy for OCR input.

        Args:
            original_path: Original image path.
            target_long_side: Desired long side in pixels.
            tag: Suffix used in the generated filename.

        Returns:
            Tuple of (prepared_path, scale_factor, prepared_width, prepared_height).
        """
        prepared_path = original_path.parent / f"{original_path.stem}.ocr_input.{tag}.png"
        with Image.open(original_path) as im:
            im = im.convert("RGB")
            w0, h0 = im.size
            long_side = max(w0, h0)
            if long_side <= 0:
                raise ValueError("Invalid image size")

            # Determine scale factor (quality-first, but capped).
            scale = float(target_long_side) / float(long_side)
            # Do not shrink below original unless exceeding max allowed long side.
            if scale < 1.0:
                scale = 1.0

            # Apply max cap.
            target_long_side_capped = min(target_long_side, input_max_long_side)
            scale_capped = float(target_long_side_capped) / float(long_side)
            if scale_capped < scale:
                scale = scale_capped

            new_w = max(1, int(round(w0 * scale)))
            new_h = max(1, int(round(h0 * scale)))

            if new_w != w0 or new_h != h0:
                im = im.resize((new_w, new_h), resample=Image.LANCZOS)

            im.save(prepared_path, format="PNG", optimize=False)

        return prepared_path, scale, new_w, new_h

    def _score_pass(text_lines: list[str], out_boxes: list[dict[str, Any]], confidences: list[float]) -> tuple[int, int, float]:
        """Compute a deterministic pass score for choosing the best OCR pass."""
        text_len = sum(len(t) for t in text_lines)
        box_count = len(out_boxes)
        conf_avg = float(sum(confidences) / len(confidences)) if confidences else 0.0
        return (text_len, box_count, conf_avg)

    def _should_fallback(text_lines: list[str], out_boxes: list[dict[str, Any]], heights_px: list[float]) -> bool:
        """Determine if OCR likely missed content due to small text."""
        text_len = sum(len(t) for t in text_lines)
        box_count = len(out_boxes)
        median_h = statistics.median(heights_px) if heights_px else 0.0

        if text_len < fallback_min_chars:
            return True
        if box_count < fallback_min_boxes:
            return True
        if median_h > 0 and median_h < float(min_box_height_px):
            return True
        return False

    for img_path in images:
        logger.info("OCR: Processing %s", img_path)
        try:
            with Image.open(img_path) as im_check:
                orig_w, orig_h = im_check.size
                logger.info("OCR: Original image size %sx%s", orig_w, orig_h)
        except Exception as e:
            logger.error("OCR: Failed to open image %s: %s", img_path, e)
            continue

        # Pass A: scaled input (quality-first).
        try:
            prepared_path, scale_a, prep_w, prep_h = _prepare_scaled_image(
                img_path,
                target_long_side=input_long_side,
                tag="base",
            )
            result_a = _call_engine_ocr(prepared_path)
            text_a, boxes_a, heights_a, conf_a = _parse_ocr_result(
                ocr_result=result_a,
                image_width=prep_w,
                image_height=prep_h,
                scale_to_original=scale_a,
            )
            best = ("base", text_a, boxes_a, heights_a, conf_a)
            best_score = _score_pass(text_a, boxes_a, conf_a)
            logger.info("OCR: Base pass score=%s", best_score)
        except Exception as e:
            logger.error("OCR: Base pass failed for %s: %s", img_path, e)
            continue

        # Pass B: zoom pass (2x or env factor) if needed.
        if zoom_enabled and _should_fallback(text_a, boxes_a, heights_a):
            try:
                zoom_long_side = int(round(float(input_long_side) * float(zoom_factor)))
                zoom_long_side = _clamp_int(zoom_long_side, min_value=input_long_side, max_value=input_max_long_side)
                prepared_zoom_path, scale_b, zoom_w, zoom_h = _prepare_scaled_image(
                    img_path,
                    target_long_side=zoom_long_side,
                    tag="zoom",
                )
                result_b = _call_engine_ocr(prepared_zoom_path)
                text_b, boxes_b, heights_b, conf_b = _parse_ocr_result(
                    ocr_result=result_b,
                    image_width=zoom_w,
                    image_height=zoom_h,
                    scale_to_original=scale_b,
                )
                score_b = _score_pass(text_b, boxes_b, conf_b)
                logger.info("OCR: Zoom pass score=%s (zoom_long_side=%s)", score_b, zoom_long_side)
                if score_b > best_score:
                    best = ("zoom", text_b, boxes_b, heights_b, conf_b)
                    best_score = score_b
            except Exception as e:
                logger.warning("OCR: Zoom pass failed for %s: %s", img_path, e)

        # Pass C: tiled OCR on the best current prepared image, if still needed.
        chosen_tag, chosen_text, chosen_boxes, chosen_heights, chosen_conf = best
        if tile_enable and _should_fallback(chosen_text, chosen_boxes, chosen_heights):
            try:
                # Reuse the zoom image if it exists and was chosen; otherwise base.
                tile_tag = "zoom" if chosen_tag == "zoom" else "base"
                tile_path = img_path.parent / f"{img_path.stem}.ocr_input.{tile_tag}.png"
                if not tile_path.exists():
                    tile_path = prepared_path

                with Image.open(tile_path) as base_im:
                    base_im = base_im.convert("RGB")
                    base_w, base_h = base_im.size

                    # Determine scale factor used for this prepared image.
                    # We infer it by comparing long side vs original long side (deterministic, since we generated it).
                    orig_long = max(orig_w, orig_h)
                    base_long = max(base_w, base_h)
                    scale_c = float(base_long) / float(orig_long) if orig_long > 0 else 1.0

                    tile_w = int(math.ceil(base_w / float(tile_grid)))
                    tile_h = int(math.ceil(base_h / float(tile_grid)))
                    overlap_w = int(round(tile_w * tile_overlap))
                    overlap_h = int(round(tile_h * tile_overlap))

                    tile_text_all: list[str] = []
                    tile_boxes_all: list[dict[str, Any]] = []
                    tile_heights_all: list[float] = []
                    tile_conf_all: list[float] = []

                    for r in range(tile_grid):
                        for c in range(tile_grid):
                            left = max(0, c * tile_w - overlap_w)
                            top = max(0, r * tile_h - overlap_h)
                            right = min(base_w, (c + 1) * tile_w + overlap_w)
                            bottom = min(base_h, (r + 1) * tile_h + overlap_h)
                            if right <= left or bottom <= top:
                                continue

                            tile_im = base_im.crop((left, top, right, bottom))
                            tile_file = img_path.parent / f"{img_path.stem}.ocr_tile.r{r}c{c}.{tile_tag}.png"
                            tile_im.save(tile_file, format="PNG", optimize=False)

                            tile_res = _call_engine_ocr(tile_file)
                            t_text, t_boxes, t_heights, t_conf = _parse_ocr_result(
                                ocr_result=tile_res,
                                image_width=int(right - left),
                                image_height=int(bottom - top),
                                scale_to_original=scale_c,
                                offset_x=int(left),
                                offset_y=int(top),
                                base_width=base_w,
                                base_height=base_h,
                            )
                            tile_text_all.extend(t_text)
                            tile_boxes_all.extend(t_boxes)
                            tile_heights_all.extend(t_heights)
                            tile_conf_all.extend(t_conf)

                    score_c = _score_pass(tile_text_all, tile_boxes_all, tile_conf_all)
                    logger.info("OCR: Tile pass score=%s (grid=%sx%s overlap=%s)", score_c, tile_grid, tile_grid, tile_overlap)

                    if score_c > best_score:
                        best = ("tile", tile_text_all, tile_boxes_all, tile_heights_all, tile_conf_all)
                        best_score = score_c
            except Exception as e:
                logger.warning("OCR: Tile pass failed for %s: %s", img_path, e)

        chosen_tag, chosen_text, chosen_boxes, _, _ = best
        logger.info("OCR: Selected pass '%s' for %s with score=%s", chosen_tag, img_path, best_score)

        full_text.extend(chosen_text)
        boxes.extend(chosen_boxes)

    combined_text = "\n".join(full_text)
    merchant = _extract_merchant(combined_text)
    purchase_date = _extract_date(combined_text)
    total_amount = _extract_amount(combined_text)
    vat_breakdown = _extract_vat_breakdown(combined_text)
    line_items = _extract_line_items(combined_text, total_amount)

    return {
        "text": combined_text,
        "boxes": boxes,
        "merchant": merchant,
        "gross": total_amount,
        "purchase_datetime": purchase_date,
        "vat_breakdown": vat_breakdown,
        "line_items": line_items,
    }



def _extract_merchant(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in lines[:5]:
        lower = line.lower()
        if any(keyword in lower for keyword in ["receipt", "order", "total", "amount", "date", "invoice"]):
            continue
        if len(line.split()) <= 8:
            return line
    return lines[0] if lines else None


def _extract_date(text: str) -> Optional[str]:
    patterns = [
        r"(20\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01]))",
        r"((0[1-9]|[12]\d|3[01])[-/](0[1-9]|1[0-2])[-/](20\d{2}))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace('/', '-')
    return None


def _extract_amount(text: str) -> Optional[float]:
    matches = re.findall(r"(?<!\d)(\d{1,6}[\.,]\d{2})(?!\d)", text)
    if not matches:
        return None
    try:
        values = [float(m.replace(',', '.')) for m in matches]
    except ValueError:
        return None
    return max(values) if values else None


def _extract_vat_breakdown(text: str) -> Dict[int, float]:
    vat_breakdown = {}
    pattern = re.compile(r"(moms|vat|tax)d*s*\(?s*(25|12|6|0)s*\)?s*[:s]*([\d\s.,]+)", re.IGNORECASE)
    for match in pattern.finditer(text):
        try:
            rate = int(match.group(2))
            amount_str = match.group(3).replace(' ', '').replace(',', '.')
            amount = float(amount_str)
            if rate in {25, 12, 6, 0}:
                vat_breakdown[rate] = vat_breakdown.get(rate, 0.0) + amount
        except (ValueError, IndexError):
            continue
    return vat_breakdown


def _extract_line_items(text: str, total_amount: Optional[float]) -> List[Dict[str, Any]]:
    line_items = []
    line_pattern = re.compile(r"^((?!total|summa|subtotal|moms|vat|tax|netto|brutto).+?)\s+([\d\s.,]+[.,]\d{2})$", re.IGNORECASE | re.MULTILINE)
    for match in line_pattern.finditer(text):
        try:
            desc = match.group(1).strip()
            amount_str = match.group(2).replace(' ', '').replace(',', '.')
            amount = float(amount_str)
            if total_amount is not None and amount > total_amount:
                continue
            if len(desc) > 2 and len(desc) < 50:
                line_items.append({
                    "description": desc,
                    "quantity": 1,
                    "unit_price": amount,
                    "total": amount,
                    "vat_rate": 0,
                })
        except (ValueError, IndexError):
            continue
    return line_items


def run_ocr(receipt_id: str, storage_dir: str | Path | None = None) -> Dict[str, Any]:
    """Perform OCR/extraction using PaddleOCR (with graceful fallback)."""
    base = storage_dir or os.getenv("STORAGE_DIR", "/data/storage")
    base_path = Path(base)
    receipt_path = _receipt_dir(base_path, receipt_id)
    receipt_path.mkdir(parents=True, exist_ok=True)
    images = _list_images(base_path, receipt_id)

    ocr_result = _extract_text_from_images(images)
    boxes = ocr_result.get("boxes", [])
    _write_boxes(base_path, receipt_id, boxes)

    line_items = ocr_result.get("line_items", [])
    if line_items:
        _write_line_items(base_path, receipt_id, line_items)

    if not ocr_result.get("text"):
        return {
            "merchant_name": None,
            "purchase_datetime": None,
            "gross_amount": None,
            "net_amount": None,
            "confidence": 0.0,
            "boxes_saved": True,
            "vat_breakdown": {},
            "line_items": [],
        }

    gross_val = ocr_result.get("gross")
    vat_breakdown = ocr_result.get("vat_breakdown", {})
    vat_sum = sum(vat_breakdown.values())

    net_val = None
    try:
        if gross_val is not None:
            net_val = float(gross_val) - vat_sum
    except (ValueError, TypeError):
        net_val = None

    return {
        "merchant_name": ocr_result.get("merchant"),
        "purchase_datetime": ocr_result.get("purchase_datetime"),
        "gross_amount": float(gross_val) if gross_val is not None else None,
        "net_amount": net_val,
        "confidence": 0.85,
        "text": ocr_result.get("text"),
        "boxes_saved": True,
        "vat_breakdown": vat_breakdown,
        "line_items": line_items,
    }

```

### File: `backend/src/services/tasks/ocr_tasks.py`

```python
from __future__ import annotations

import logging
import os
import time
import uuid
import hashlib
from pathlib import Path
from typing import Any

from .common import (
    FileStorage,
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    AiStatus,
    celery_app,
    db_cursor,
    create_unified_file,
    get_unified_file_by_hash,
    log_event,
    pdf_to_png_pages,
    run_ocr,
    update_other_data,
    DuplicateFileError,
    group,
    chord,
    parse_credit_card_statement,
)
from .creditcard_tasks import _ensure_creditcard_pages_and_ocr
from .file_management_tasks import (
    _enforce_file_metadata,
    _maybe_advance_invoice_from_file,
    _update_file_fields,
    _update_file_status,
)
from .history import _history
from .invoice_tasks import _persist_invoice_lines
from .utils.invoice_utils import _collect_invoice_ocr_text, _load_unified_file_info
from .workflow_base import (
    begin_import_stage,
    complete_import_stage,
    ensure_workflow,
    get_workflow_stage,
    mark_stage,
    log_import_event,
)
logger = logging.getLogger(__name__)

# TASK_INVENTORY: ACTIVE (2025-11-28). WF1 OCR stage for receipt workflow.
@celery_app.task(name="wf1_run_ocr")
def wf1_run_ocr(workflow_run_id: int) -> int:
    """
    Workflow 1: OCR Task.

    - Ensures the task is part of a WF1 workflow.
    - Marks the 'ocr' stage as running.
    - Executes OCR on the file associated with the workflow.
    - Marks the 'ocr' stage as 'succeeded' or 'failed'.
    - Returns the workflow_run_id for the next task in the chain.
    """
    import time
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF1_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "ocr", "failed", message="File ID missing in workflow run.")
        raise ValueError("File ID is missing.")

    begin_import_stage(workflow_run_id, "r_ocr", message=f"OCR startar för fil {file_id}")
    mark_stage(workflow_run_id, "ocr", "running", start=True)
    start_time = time.time()
    log_event(
        logger,
        "wf1.ocr.start",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
    )

    result: dict[str, Any] | None = None
    error_msg: str | None = None

    try:
        result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        log_event(
            logger,
            "wf1.ocr.error",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=error_msg,
        )

    elapsed = int((time.time() - start_time) * 1000)

    if result:
        _update_file_fields(file_id, ocr_raw=result.get("text"))
        text_len = len(result.get("text", ""))
        message = f"OCR succeeded, extracted {text_len} chars in {elapsed}ms."
        mark_stage(workflow_run_id, "ocr", "succeeded", message=message, end=True)
        complete_import_stage(workflow_run_id, "r_ocr", success=True, message=message)
        _update_file_status(file_id, AiStatus.OCR_DONE.value)
        log_event(
            logger,
            "wf1.ocr.succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            duration_ms=elapsed,
            characters=text_len,
        )
    else:
        message = f"OCR failed: {error_msg or 'OCR returned no results'}"
        mark_stage(workflow_run_id, "ocr", "failed", message=message, end=True)
        complete_import_stage(workflow_run_id, "r_ocr", success=False, message=message)
        # Do not raise an exception, allow the workflow to be inspected.
        # A failed stage will already halt the workflow chain by default.
        log_event(
            logger,
            "wf1.ocr.failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=error_msg or "no_text",
            duration_ms=elapsed,
        )
        _update_file_status(file_id, AiStatus.OCR_FAILED.value)

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 PDF splitter that schedules per-page OCR.
@celery_app.task(name="wf2_prepare_pdf_pages", queue="wf2")
def wf2_prepare_pdf_pages(workflow_run_id: int) -> int:
    """
    Workflow 2: Prepare PDF Pages Task.
    - Splits the source PDF into individual PNG pages.
    - Creates a unified_file record for each page.
    - Triggers the parallel OCR tasks for each page.
    """
    import time

    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "prepare_pages", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "prepare_pages", "running", start=True)

    parent_info = _load_unified_file_info(file_id) or {}
    mime_type = str(parent_info.get("mime_type") or "").lower()
    file_type = str(parent_info.get("file_type") or "").lower()
    log_event(
        logger,
        "convert.wf2.prepare_start",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
        mime_type=mime_type,
        file_type=file_type,
    )
    if mime_type and mime_type != "application/pdf":
        message = f"Unsupported mime_type for WF2: {mime_type}"
        log_event(
            logger,
            "convert.wf2.prepare_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            reason="unsupported_mime",
            mime_type=mime_type,
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=message, end=True)
        raise ValueError(message)
    if not mime_type and file_type not in {"pdf", "invoice"}:
        message = f"Unsupported file_type for WF2: {file_type or 'unknown'}"
        log_event(
            logger,
            "convert.wf2.prepare_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            reason="unsupported_file_type",
            file_type=file_type or "unknown",
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=message, end=True)
        raise ValueError(message)

    storage_dir = os.getenv("STORAGE_DIR", "/data/storage")
    fs = FileStorage(storage_dir)

    conversion_started: float | None = None
    try:
        originals_root = (fs.base / "originals").resolve()
        original_filename = str(
            parent_info.get("original_file_name")
            or parent_info.get("original_filename")
            or ""
        )
        suffix = Path(original_filename).suffix or ".pdf"
        stored_original_name = f"{file_id}{suffix if suffix.startswith('.') else f'.{suffix}'}"
        original_path = (originals_root / stored_original_name).resolve()

        if not str(original_path).startswith(str(originals_root)):
            raise ValueError("Original file path resolved outside storage root.")
        if not original_path.exists():
            raise FileNotFoundError(f"Original file not found in storage for {file_id}")

        log_event(
            logger,
            "convert.wf2.read_original",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            original_filename=original_filename or original_path.name,
            storage_path=str(original_path),
        )

        data = original_path.read_bytes()
        safe_filename = original_filename or original_path.name

        converted_root = (fs.base / "converted" / file_id).resolve()
        converted_root.mkdir(parents=True, exist_ok=True)

        # Convert PDF to PNG pages
        conversion_started = time.perf_counter()
        try:
            pdf_dpi = int(os.getenv("OCR_PDF_DPI", "300") or "300")
        except Exception:
            pdf_dpi = 300

        dpi_candidates = [pdf_dpi, 300, 250, 200, 150]
        seen: set[int] = set()
        pages = []
        last_exc: Exception | None = None
        for dpi_candidate in dpi_candidates:
            if dpi_candidate in seen or dpi_candidate <= 0:
                continue
            seen.add(dpi_candidate)
            try:
                pages = pdf_to_png_pages(data, converted_root, file_id, dpi=dpi_candidate)
                if pages:
                    pdf_dpi = dpi_candidate
                    break
            except Exception as exc:
                last_exc = exc

        if not pages:
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("PDF conversion resulted in no pages.")

        page_refs: list[dict[str, Any]] = []
        duplicate_page_ids: list[str] = []
        for page in pages:
            page_number = page.index + 1
            page_id = str(uuid.uuid4())
            page_hash = hashlib.sha256(page.bytes).hexdigest()

            target_file_id = page_id
            duplicate = False

            try:
                create_unified_file(
                    file_id=page_id,
                    file_type="pdf_page",
                    workflow_type="receipt",
                    content_hash=page_hash,
                    submitted_by="workflow",
                    source="wf2_split",
                    original_filename=f"{safe_filename}-page-{page_number:04d}.png",
                    initial_ai_status=AiStatus.UPLOADED.value,
                    mime_type="image/png",
                    file_suffix=".png",
                    original_file_id=file_id,
                    original_file_name=safe_filename,
                    original_file_size=len(page.bytes),
                    extra_metadata={
                        "detected_kind": "pdf_page",
                        "page_number": page_number,
                        "source_pdf": file_id,
                    },
                    create_workflow=False,
                )
            except DuplicateFileError:
                existing = get_unified_file_by_hash(page_hash)
                if not existing:
                    raise
                target_file_id = existing.id
                duplicate = True
                duplicate_page_ids.append(target_file_id)
                log_event(
                    logger,
                    "convert.wf2.duplicate_page_reused",
                    workflow_run_id=workflow_run_id,
                    file_id=file_id,
                    page_number=page_number,
                    reused_file_id=target_file_id,
                )

            stored_page_name = f"page-{page_number:04d}.png"
            stored_page_path = fs.adopt(target_file_id, stored_page_name, page.path)
            if page_number == 1:
                try:
                    existing_parent_images = [
                        name
                        for name in fs.list(file_id)
                        if name.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
                    ]
                    if not existing_parent_images:
                        fs.save(file_id, "page-0001.png", stored_page_path.read_bytes())
                        log_event(
                            logger,
                            "wf2.parent_preview_written",
                            workflow_run_id=workflow_run_id,
                            file_id=file_id,
                            source_page_file_id=target_file_id,
                        )
                except Exception as exc:
                    log_event(
                        logger,
                        "wf2.parent_preview_write_failed",
                        workflow_run_id=workflow_run_id,
                        file_id=file_id,
                        error=str(exc),
                    )
            page_refs.append(
                {
                    "file_id": target_file_id,
                    "page_number": page_number,
                    "duplicate": duplicate,
                    "workflow_type": "receipt",
                }
            )

        duration_ms = int((time.perf_counter() - conversion_started) * 1000) if conversion_started else None
        converted_page_ids = [page["file_id"] for page in page_refs]
        log_event(
            logger,
            "convert.wf2.conversion_succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            page_count=len(page_refs),
            duplicate_reused=len(duplicate_page_ids),
            duration_ms=duration_ms,
            page_ids=converted_page_ids,
        )
        _history(
            file_id,
            "pdf_convert",
            "success",
            ai_stage_name="PDF-Conversion",
            log_text=(
                f"WF2 converted PDF into {len(page_refs)} page(s): page_ids={converted_page_ids}; "
                f"workflow_run_id={workflow_run_id}; duplicate_pages_reused={len(duplicate_page_ids)}"
            ),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name=f"fitz-dpi-{pdf_dpi}",
        )

        # Update the parent PDF unified_file with page info
        other_data = dict(parent_info.get("other_data", {}) or {})
        other_data.update({"page_count": len(page_refs), "pages": page_refs})
        if duplicate_page_ids:
            other_data["duplicate_page_ids"] = duplicate_page_ids
        update_other_data(file_id, other_data)

        mark_stage(
            workflow_run_id,
            "prepare_pages",
            "succeeded",
            message=(
                f"Split PDF into {len(page_refs)} pages."
                + (f" Reused {len(duplicate_page_ids)} duplicate page(s)." if duplicate_page_ids else "")
            ),
            end=True,
        )
        log_event(
            logger,
            "convert.wf2.prepare_succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            page_count=len(page_refs),
            duplicate_reused=len(duplicate_page_ids),
        )

        # Now, trigger the parallel OCR
        if page_refs:
            ocr_tasks = group(
                wf2_run_page_ocr.s(workflow_run_id, page["file_id"], page["page_number"]).set(queue="wf2")
                for page in page_refs
            )
            callback = wf2_merge_ocr_results.s(workflow_run_id).set(queue="wf2")
            chord(ocr_tasks)(callback)
            log_event(
                logger,
                "convert.wf2.ocr_dispatched",
                workflow_run_id=workflow_run_id,
                file_id=file_id,
                page_count=len(page_refs),
            )
    except Exception as e:
        duration_ms = int((time.perf_counter() - conversion_started) * 1000) if conversion_started else None
        log_event(
            logger,
            "convert.wf2.conversion_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=str(e),
            duration_ms=duration_ms,
        )
        _history(
            file_id,
            "pdf_convert",
            "error",
            ai_stage_name="PDF-Conversion",
            log_text="WF2 PDF conversion failed.",
            error_message=str(e),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name=f"fitz-dpi-{pdf_dpi}",
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=str(e), end=True)
        raise

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 per-page OCR execution.
@celery_app.task(name="wf2_run_page_ocr", queue="wf2")
def wf2_run_page_ocr(
    workflow_run_id: int, page_file_id: str, page_number: int | str | None = None
) -> tuple[int, str, str]:
    """
    Workflow 2: OCR Task for a single page.
    - Runs OCR and returns the text.
    """
    import time
    ensure_workflow(workflow_run_id, expected_prefix="WF2_")

    page_info = _load_unified_file_info(page_file_id)
    effective_page_number = (
        page_number
        if page_number is not None
        else (page_info.get("other_data", {}).get("page_number", "unknown") if page_info else "unknown")
    )
    stage_key = f"ocr_page_{effective_page_number}"

    mark_stage(workflow_run_id, stage_key, "running", start=True)
    start_time = time.time()
    log_event(
        logger,
        "wf2.page_ocr.start",
        workflow_run_id=workflow_run_id,
        page_file_id=page_file_id,
        page_number=effective_page_number,
    )

    result: dict[str, Any] | None = None
    error_msg: str | None = None
    text = ""

    try:
        result = run_ocr(page_file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        log_event(
            logger,
            "wf2.page_ocr.error",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            error=error_msg,
        )

    elapsed = int((time.time() - start_time) * 1000)

    if result:
        text = result.get("text", "")
        _update_file_fields(page_file_id, ocr_raw=text)
        message = f"OCR succeeded for page {effective_page_number}, extracted {len(text)} chars in {elapsed}ms."
        mark_stage(workflow_run_id, stage_key, "succeeded", message=message, end=True)
        log_event(
            logger,
            "wf2.page_ocr.succeeded",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            duration_ms=elapsed,
            characters=len(text),
        )
    else:
        message = f"OCR failed for page {effective_page_number}: {error_msg or 'OCR returned no results'}"
        mark_stage(workflow_run_id, stage_key, "failed", message=message, end=True)
        log_event(
            logger,
            "wf2.page_ocr.failed",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            error=error_msg or 'no_text',
            duration_ms=elapsed,
        )

    return (workflow_run_id, page_file_id, text)

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 fan-in to merge OCR results and continue workflow.
@celery_app.task(name="wf2_merge_ocr_results", queue="wf2")
def wf2_merge_ocr_results(results: list[tuple[int, str, str]], workflow_run_id: int):
    """
    Workflow 2: Merge OCR Results Task.
    - Collects OCR text from all page tasks.
    - Saves the combined text.
    - Triggers the next step in the workflow.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id") # This is the parent PDF file_id
    if not file_id:
        mark_stage(workflow_run_id, "merge_ocr", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "merge_ocr", "running", start=True)

    all_text = []
    failed_pages = []
    for result in results:
        if result and len(result) == 3:
            _, page_id, text = result
            if text:
                all_text.append(text)
            else:
                failed_pages.append(page_id)

    combined_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
    
    # Save the combined text to the parent PDF's other_data
    parent_file_info = _load_unified_file_info(file_id) or {}
    other_data = dict(parent_file_info.get("other_data", {}) or {})
    other_data["combined_ocr_text"] = combined_text
    if failed_pages:
        other_data["failed_ocr_pages"] = failed_pages
    update_other_data(file_id, other_data)

    # Update parent ocr_raw to enable downstream AI
    _update_file_fields(file_id, ocr_raw=combined_text)
    _update_file_status(file_id, AiStatus.OCR_DONE.value)

    # Mark pages as completed to avoid orphan queue noise
    for result in results:
        if result and len(result) == 3:
            _, page_id, _ = result
            _update_file_status(page_id, AiStatus.COMPLETED.value)

    message = f"Merged OCR text from {len(all_text)} pages. {len(failed_pages)} pages failed."
    status = "succeeded"
    if failed_pages:
        status = "failed"
        message += f" Failed pages: {', '.join(failed_pages)}"
    elif not combined_text:
        status = "failed"
        message = "OCR merge produced no text."

    mark_stage(workflow_run_id, "merge_ocr", status, message=message, end=True)

    if status != "succeeded":
        return workflow_run_id

    # Decide next step based on intended workflow type
    parent_workflow_type = str(parent_file_info.get("workflow_type") or "").lower()

    if parent_workflow_type in ("receipt", ""):
        # Create and dispatch a WF1 workflow_run for the parent PDF (single log entry expected)
        try:
            from services.workflow_runs import create_workflow_run
            from services.tasks.workflow_tasks import dispatch_workflow, mark_stage as wt_mark_stage
        except Exception:
            dispatch_workflow = None
            create_workflow_run = None
            wt_mark_stage = None

        if create_workflow_run and dispatch_workflow and wt_mark_stage:
            # Ensure invoice_analysis is marked so wf2_finalize can succeed
            wt_mark_stage(workflow_run_id, "invoice_analysis", "succeeded", message="Skipped: forwarded to WF1")

            new_wr_id = create_workflow_run(
                workflow_key="WF1_RECEIPT",
                source_channel="wf2_split",
                file_id=file_id,
                content_hash=parent_file_info.get("content_hash") or "",
            )
            dispatch_workflow(new_wr_id)
            log_event(
                logger,
                "wf2.dispatch_wf1_after_split",
                workflow_run_id=workflow_run_id,
                new_workflow_run_id=new_wr_id,
                file_id=file_id,
            )
        else:
            log_event(
                logger,
                "wf2.dispatch_wf1_after_split_failed",
                workflow_run_id=workflow_run_id,
                file_id=file_id,
                reason="dispatch helpers unavailable",
            )

        # Finalize WF2 to succeeded to keep SoT invariant
        mark_stage(
            workflow_run_id,
            "finalize",
            "succeeded",
            message="WF2 slutförd, dispatchad till WF1 for receipt processing",
            end=True,
            workflow_status_override="succeeded",
        )
        begin_import_stage(
            workflow_run_id,
            "finalize_ok",
            message="WF2 slutförd",
        )
        complete_import_stage(
            workflow_run_id,
            "finalize_ok",
            success=True,
            message="PDF-split avslutad och skickad vidare till WF1",
        )
        log_import_event(
            workflow_run_id,
            "KLAR",
            message="WF2 slutförd",
        )
    else:
        # Non-receipt path: continue existing WF2 invoice analysis chain
        wf2_run_invoice_analysis.s(workflow_run_id).set(queue="wf2").apply_async()

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 invoice analysis stage (parses merged OCR).
@celery_app.task(name="wf2_run_invoice_analysis", queue="wf2")
def wf2_run_invoice_analysis(workflow_run_id: int) -> int:
    """
    Workflow 2: Invoice Analysis Task.
    - Parses the combined OCR text.
    - Creates invoice line items.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "invoice_analysis", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "invoice_analysis", "running", start=True)
    log_event(
        logger,
        "wf2.invoice_analysis.start",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
    )

    parent_info = _load_unified_file_info(file_id) or {}

    try:
        other_data = dict(parent_info.get("other_data", {}) or {})
        combined_text = other_data.get("combined_ocr_text", "")

        if not combined_text:
            raise ValueError("Combined OCR text is missing.")

        # This logic is from the old `process_invoice_document`
        parsed = parse_credit_card_statement(combined_text)
        lines = parsed.get("lines") or []
        inserted = _persist_invoice_lines(file_id, lines)

        other_data["invoice_line_count"] = inserted
        update_other_data(file_id, other_data)

        message = f"Invoice analysis complete. Inserted {inserted} lines."
        mark_stage(workflow_run_id, "invoice_analysis", "succeeded", message=message, end=True)
        log_event(
            logger,
            "wf2.invoice_analysis.succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            inserted=inserted,
        )

        # Trigger finalization (lazy import to avoid circular import at module load)
        import importlib

        wf_tasks = importlib.import_module("services.tasks.workflow_tasks")
        finalize_task = getattr(wf_tasks, "wf2_finalize", None)
        if not finalize_task:
            raise NameError("wf2_finalize task not found in workflow_tasks module")

        finalize_task.s(workflow_run_id).set(queue="wf2").apply_async()

    except Exception as e:
        mark_stage(workflow_run_id, "invoice_analysis", "failed", message=str(e), end=True)
        log_event(
            logger,
            "wf2.invoice_analysis.failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=str(e),
        )
        raise

    return workflow_run_id

__all__ = [
    "wf1_run_ocr",
    "wf2_prepare_pdf_pages",
    "wf2_run_page_ocr",
    "wf2_merge_ocr_results",
    "wf2_run_invoice_analysis",
]

```

### File: `backend/src/services/tasks/creditcard_tasks.py`

```python
from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Tuple

from .common import (
    DuplicateFileError,
    FileStorage,
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    AiStatus,
    _persist_credit_card_match,
    db_cursor,
    create_unified_file,
    log_event,
    parse_credit_card_statement,
    pdf_to_png_pages,
    record_invoice_decision,
    run_ocr,
    track_task,
    transition_document_status,
    transition_line_status,
    transition_line_status_and_link,
    transition_processing_status,
    update_other_data,
)
from .file_management_tasks import (
    _enforce_file_metadata,
    _maybe_advance_invoice_from_file,
    _update_file_fields,
    _update_file_status,
)
from .history import _history
from .invoice_tasks import _to_decimal
from .utils.invoice_utils import (
    _collect_invoice_ocr_text,
    _load_invoice_file_records,
    _load_invoice_metadata,
    _update_invoice_metadata,
)

logger = logging.getLogger(__name__)
MATCH_DATE_WINDOW_DAYS = 60
MATCH_AMOUNT_TOLERANCE = Decimal("10")
MAX_RECEIPT_CANDIDATES = 25


def _ensure_creditcard_pages_and_ocr(
    file_id: str,
    parent_info: dict[str, Any],
) -> Tuple[str, dict[str, Any]]:
    """Ensure credit card invoice pages exist and OCR text is available."""
    import time

    other_data = dict(parent_info.get("other_data", {}) or {})
    existing_combined = other_data.get("combined_ocr_text")
    if existing_combined:
        log_event(
            logger,
            "convert.creditcard.cached_result",
            file_id=file_id,
            characters=len(existing_combined),
        )
        _history(
            file_id,
            "pdf_convert",
            "skipped",
            ai_stage_name="PDF-Conversion",
            log_text="OCR text already cached; skipping conversion.",
        )
        return existing_combined, other_data

    storage_dir = os.getenv("STORAGE_DIR", "/data/storage")
    fs = FileStorage(storage_dir)

    mime_type = str(parent_info.get("mime_type") or "").lower()
    file_type = str(parent_info.get("file_type") or "").lower()
    workflow_type = str(parent_info.get("workflow_type") or "").lower()
    detected_kind = (other_data.get("detected_kind") or file_type or "").lower()
    is_pdf_source = mime_type == "application/pdf" or detected_kind == "pdf" or file_type == "cc_pdf"
    expected_parent_type = "cc_pdf" if is_pdf_source else "cc_image"

    if file_type != expected_parent_type or workflow_type != "creditcard_invoice":
        _enforce_file_metadata(
            file_id,
            file_type=expected_parent_type,
            workflow_type="creditcard_invoice",
        )
    parent_info["file_type"] = expected_parent_type
    parent_info["workflow_type"] = "creditcard_invoice"

    page_refs = []
    for page in list(other_data.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("file_id")
        if not page_id:
            continue
        _enforce_file_metadata(
            page_id,
            file_type="cc_image",
            workflow_type="creditcard_invoice",
        )
        page["file_type"] = "cc_image"
        page_refs.append(page)

    log_event(
        logger,
        "convert.creditcard.ensure_state",
        file_id=file_id,
        is_pdf_source=is_pdf_source,
        existing_pages=len(page_refs),
        has_combined_text=bool(existing_combined),
    )

    # Convert PDF to pages if not already done
    if is_pdf_source and not page_refs:
        originals_root = (fs.base / "originals").resolve()
        original_filename = str(
            parent_info.get("original_file_name")
            or parent_info.get("original_filename")
            or ""
        )
        suffix = Path(original_filename).suffix or ".pdf"
        stored_original_name = f"{file_id}{suffix if suffix.startswith('.') else f'.{suffix}'}"
        original_path = (originals_root / stored_original_name).resolve()
        if not original_path.exists():
            raise FileNotFoundError(f"Original file not found in storage for {file_id}")

        log_event(
            logger,
            "convert.creditcard.conversion_start",
            file_id=file_id,
            original_filename=original_filename or original_path.name,
            storage_path=str(original_path),
        )

        data = original_path.read_bytes()
        converted_root = (fs.base / "converted" / file_id).resolve()
        converted_root.mkdir(parents=True, exist_ok=True)

        conversion_started = time.perf_counter()
        try:
            try:
                pdf_dpi = int(os.getenv("OCR_PDF_DPI", "300") or "300")
            except Exception:
                pdf_dpi = 300

            dpi_candidates = [pdf_dpi, 300, 250, 200, 150]
            seen: set[int] = set()
            pages = []
            last_exc: Exception | None = None
            for dpi_candidate in dpi_candidates:
                if dpi_candidate in seen or dpi_candidate <= 0:
                    continue
                seen.add(dpi_candidate)
                try:
                    pages = pdf_to_png_pages(data, converted_root, file_id, dpi=dpi_candidate)
                    if pages:
                        pdf_dpi = dpi_candidate
                        break
                except Exception as exc:
                    last_exc = exc

            if not pages:
                if last_exc is not None:
                    raise last_exc
                raise RuntimeError("PDF conversion resulted in no pages.")

            safe_filename = original_filename or original_path.name
            page_refs = []
            for page in pages:
                page_number = page.index + 1
                page_id = str(uuid.uuid4())
                page_hash = hashlib.sha256(page.bytes).hexdigest()
                try:
                    create_unified_file(
                        file_id=page_id,
                        file_type="cc_image",
                        create_workflow=False,
                        content_hash=page_hash,
                        submitted_by="workflow",
                        source=other_data.get("source"),
                        original_filename=f"{safe_filename}-page-{page_number:04d}.png",
                        initial_ai_status=AiStatus.UPLOADED.value,
                        mime_type="image/png",
                        file_suffix=".png",
                        original_file_id=file_id,
                        original_file_name=safe_filename,
                        original_file_size=len(page.bytes),
                        extra_metadata={
                            "detected_kind": "invoice_page",
                            "page_number": page_number,
                            "source_pdf": file_id,
                            "workflow_type": "creditcard_invoice",
                        },
                    )
                except DuplicateFileError:
                    log_event(
                        logger,
                        "convert.creditcard.page_duplicate",
                        file_id=file_id,
                        page_number=page_number,
                    )
                    # If a page already exists, reuse it by locating the ID
                    with db_cursor() as cur:
                        cur.execute(
                            "SELECT id, other_data FROM unified_files WHERE original_file_id=%s AND other_data LIKE %s",
                            (file_id, f'%\"page_number\": {page_number}%'),
                        )
                        row = cur.fetchone()
                    if row:
                        page_id = row[0]

                stored_page_name = f"page-{page_number:04d}.png"
                fs.adopt(page_id, stored_page_name, page.path)
                _enforce_file_metadata(
                    page_id,
                    file_type="cc_image",
                    workflow_type="creditcard_invoice",
                )
                page_refs.append(
                    {"file_id": page_id, "page_number": page_number, "file_type": "cc_image"}
                )
        except Exception as exc:
            duration_ms = int((time.perf_counter() - conversion_started) * 1000)
            error_msg = f"{type(exc).__name__}: {exc}"
            log_event(
                logger,
                "convert.creditcard.conversion_failed",
                file_id=file_id,
                error=error_msg,
                duration_ms=duration_ms,
            )
            _history(
                file_id,
                "pdf_convert",
                "error",
                ai_stage_name="PDF-Conversion",
                log_text="Failed to convert credit card PDF to page images.",
                error_message=error_msg,
                processing_time_ms=duration_ms,
                provider="pymupdf",
                model_name=f"fitz-dpi-{pdf_dpi}",
            )
            raise

        duration_ms = int((time.perf_counter() - conversion_started) * 1000)
        converted_page_ids = [page.get("file_id") for page in page_refs if page.get("file_id")]
        log_event(
            logger,
            "convert.creditcard.conversion_succeeded",
            file_id=file_id,
            page_count=len(page_refs),
            duration_ms=duration_ms,
            page_ids=converted_page_ids,
        )
        _history(
            file_id,
            "pdf_convert",
            "success",
            ai_stage_name="PDF-Conversion",
            log_text=(
                f"Converted credit card PDF to {len(page_refs)} page image(s): "
                f"page_ids={converted_page_ids}"
            ),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name=f"fitz-dpi-{pdf_dpi}",
        )

        logger.info(
            "WF3 creditcard invoice %s generated %d page image(s): %s",
            file_id,
            len(page_refs),
            ", ".join(page.get("file_id", "?") for page in page_refs),
        )
    elif not is_pdf_source:
        logger.info(
            "WF3 creditcard invoice %s stored as single image (file_type=%s, workflow_type=creditcard_invoice)",
            file_id,
            expected_parent_type,
        )
        log_event(
            logger,
            "convert.creditcard.single_image_source",
            file_id=file_id,
            file_type=expected_parent_type,
        )
        _history(
            file_id,
            "pdf_convert",
            "skipped",
            ai_stage_name="PDF-Conversion",
            log_text=f"Skipped PDF conversion for {file_id}: source is non-PDF ({expected_parent_type}).",
        )
    else:
        logger.info(
            "WF3 creditcard invoice %s reusing %d existing page image(s).",
            file_id,
            len(page_refs),
        )
        log_event(
            logger,
            "convert.creditcard.pages_reused",
            file_id=file_id,
            page_count=len(page_refs),
        )
        _history(
            file_id,
            "pdf_convert",
            "skipped",
            ai_stage_name="PDF-Conversion",
            log_text=f"Reused {len(page_refs)} existing page image(s) for credit card PDF conversion.",
        )
    other_data["pages"] = page_refs
    update_other_data(file_id, other_data)

    # Run OCR on pages (or directly on the file if not a PDF)
    texts: list[str] = []
    if page_refs:
        for page in page_refs:
            page_id = page.get("file_id")
            if not page_id:
                continue
            result = run_ocr(page_id, storage_dir)
            text = (result or {}).get("text") or ""
            if text:
                texts.append(text)
                _update_file_fields(page_id, ocr_raw=text)
                _update_file_status(page_id, InvoiceProcessingStatus.OCR_DONE.value)
                log_event(
                    logger,
                    "convert.creditcard.page_ocr_completed",
                    file_id=file_id,
                    page_id=page_id,
                    page_number=page.get("page_number"),
                    characters=len(text),
                )
            else:
                log_event(
                    logger,
                    "convert.creditcard.page_ocr_empty",
                    file_id=file_id,
                    page_id=page_id,
                    page_number=page.get("page_number"),
                )
    else:
        result = run_ocr(file_id, storage_dir)
        text = (result or {}).get("text") or ""
        if text:
            texts.append(text)
            _update_file_fields(file_id, ocr_raw=text)
            log_event(
                logger,
                "convert.creditcard.single_ocr_completed",
                file_id=file_id,
                characters=len(text),
            )
        else:
            log_event(
                logger,
                "convert.creditcard.single_ocr_empty",
                file_id=file_id,
            )

    combined_text = "\n\n--- PAGE BREAK ---\n\n".join(texts).strip()
    if not combined_text:
        logger.warning("Credit card invoice %s produced no OCR text.", file_id)
        log_event(
            logger,
            "convert.creditcard.ocr_empty",
            file_id=file_id,
            page_count=len(page_refs) or 1,
        )
    other_data["combined_ocr_text"] = combined_text
    update_other_data(file_id, other_data)
    _update_file_status(file_id, InvoiceProcessingStatus.OCR_DONE.value)

    if combined_text:
        log_event(
            logger,
            "convert.creditcard.ocr_completed",
            file_id=file_id,
            page_count=len(page_refs) or 1,
            characters=len(combined_text),
        )

    return combined_text, other_data

def _load_credit_items_for_invoice(
    document_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[Optional[int], list[dict[str, Any]]]:
    """Fetch credit card invoice items from invoice_lines and normalise data for matching."""
    if db_cursor is None:
        return (None, [])

    items: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       transaction_date,
                       amount,
                       merchant_name,
                       description,
                       match_status
                  FROM invoice_lines
                 WHERE invoice_id=%s
                 ORDER BY id ASC
                """,
                (document_id,),
            )
            rows = cur.fetchall() or []
    except Exception:
        return (None, [])

    for row in rows:
        (
            line_id,
            transaction_date,
            amount,
            merchant_name,
            description,
            match_status,
        ) = row

        # Map match_status to legacy matched_flag for backward compatibility
        matched_flag = 0
        if match_status == InvoiceLineMatchStatus.MANUAL.value:
            matched_flag = 2
        elif match_status in (InvoiceLineMatchStatus.AUTO.value, InvoiceLineMatchStatus.CONFIRMED.value):
            matched_flag = 1

        items.append(
            {
                "id": int(line_id),
                "line_no": None,  # Not stored in invoice_lines
                "purchase_date": transaction_date,
                "amount_original": _to_decimal(amount),
                "amount_sek": _to_decimal(amount),
                "gross_amount": _to_decimal(amount),
                "net_amount": None,
                "merchant": (merchant_name or description or "").strip(),
                "matched_flag": matched_flag,
                "used": False,
            }
        )

    return (None, items)

def _select_credit_item_for_line(
    line_ctx: dict[str, Any],
    items: list[dict[str, Any]],
) -> tuple[Optional[int], Optional[Decimal]]:
    """Pick the best credit card invoice item for the provided invoice line."""
    if not items:
        return (None, None)

    line_amount: Optional[Decimal] = line_ctx.get("amount")
    merchant_hint_raw = (line_ctx.get("merchant_hint") or "").strip()
    merchant_hint = merchant_hint_raw.lower()

    line_date_raw = line_ctx.get("transaction_date")
    if isinstance(line_date_raw, datetime):
        line_date: Optional[date] = line_date_raw.date()
    elif isinstance(line_date_raw, date):
        line_date = line_date_raw
    elif isinstance(line_date_raw, str):
        try:
            line_date = datetime.fromisoformat(line_date_raw[:10]).date()
        except Exception:
            line_date = None
    else:
        line_date = None

    best_item: Optional[dict[str, Any]] = None
    best_amount: Optional[Decimal] = None
    best_score: Optional[tuple[float, int, int, int]] = None

    for item in items:
        if item.get("used"):
            continue
        if item.get("matched_flag"):
            continue

        amount_candidates = [
            value
            for value in (
                item.get("amount_sek"),
                item.get("gross_amount"),
                item.get("amount_original"),
                item.get("net_amount"),
            )
            if value is not None
        ]
        if line_amount is not None and amount_candidates:
            diffs = [abs(line_amount - cand) for cand in amount_candidates]
            best_diff = min(diffs)
            best_amt = amount_candidates[diffs.index(best_diff)]
        else:
            best_diff = Decimal("999999")
            best_amt = amount_candidates[0] if amount_candidates else None

        item_date_raw = item.get("purchase_date")
        if isinstance(item_date_raw, datetime):
            item_date = item_date_raw.date()
        elif isinstance(item_date_raw, date):
            item_date = item_date_raw
        else:
            item_date = None
        if line_date is not None and item_date is not None:
            date_diff = abs((line_date - item_date).days)
        else:
            date_diff = 9999

        merchant_penalty = 1
        item_merchant = (item.get("merchant") or "").lower()
        if not merchant_hint or not item_merchant:
            merchant_penalty = 0
        elif merchant_hint in item_merchant or item_merchant in merchant_hint:
            merchant_penalty = 0

        score = (
            float(best_diff if isinstance(best_diff, Decimal) else Decimal(best_diff)),
            date_diff,
            merchant_penalty,
            item.get("line_no") if item.get("line_no") is not None else item["id"],
        )

        if best_score is None or score < best_score:
            best_score = score
            best_item = item
            best_amount = best_amt

    if best_item is not None:
        best_item["used"] = True
        return (best_item["id"], best_amount)

    return (None, None)

def auto_match_invoice_lines(document_id: str) -> tuple[int, int]:
    if db_cursor is None:
        return (0, 0)

    pending_rows: list[Any] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       transaction_date,
                       amount,
                       COALESCE(merchant_name, description) AS merchant_hint,
                       match_status
                  FROM invoice_lines
                 WHERE invoice_id=%s
                   AND (match_status IS NULL OR match_status IN (%s, %s))
                """,
                (document_id, InvoiceLineMatchStatus.PENDING.value, InvoiceLineMatchStatus.UNMATCHED.value),
            )
            pending_rows = cur.fetchall() or []
    except Exception:
        log_event(
            logger,
            "matching.auto.lines_fetch_failed",
            invoice_id=document_id,
            reason="db_error",
        )
        return (0, 0)

    pending_total = len(pending_rows)
    log_event(
        logger,
        "matching.auto.lines_fetched",
        invoice_id=document_id,
        pending=pending_total,
    )

    if pending_total == 0:
        log_event(
            logger,
            "matching.auto.skipped",
            invoice_id=document_id,
            reason="no_pending_lines",
        )
        return (0, 0)

    def _safe_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _normalize_date(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        if isinstance(value, str):
            return value.split(" ")[0]
        return str(value)

    pending: dict[int, dict[str, Any]] = {}
    metadata = _load_invoice_metadata(document_id) or {}
    _, credit_items = _load_credit_items_for_invoice(document_id, metadata)
    log_event(
        logger,
        "matching.auto.credit_items_loaded",
        invoice_id=document_id,
        credit_items=len(credit_items),
    )

    def _fetch_receipt_candidates(tx_date: Any, amount: Optional[Decimal]) -> list[Any]:
        if amount is None or db_cursor is None or tx_date is None:
            return []
        date_value = _normalize_date(tx_date)
        if date_value is None:
            return []
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT uf.id,
                           COALESCE(uf.purchase_datetime, uf.created_at) AS match_datetime,
                           CAST(
                               COALESCE(
                                   NULLIF(uf.gross_amount, 0),
                                   NULLIF(uf.gross_amount_sek, 0),
                                   NULLIF(uf.net_amount, 0),
                                   NULLIF(uf.net_amount_sek, 0)
                               ) AS DECIMAL(13, 2)
                           ) AS match_amount,
                           c.name
                      FROM unified_files AS uf
                 LEFT JOIN invoice_lines AS il ON il.matched_file_id = uf.id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                      WHERE (
                                COALESCE(uf.purchase_datetime, uf.created_at) IS NULL
                             OR ABS(
                                   DATEDIFF(
                                       DATE(COALESCE(uf.purchase_datetime, uf.created_at)),
                                       %s
                                   )
                               ) <= %s
                           )
                        AND (
                                COALESCE(
                                    NULLIF(uf.gross_amount, 0),
                                    NULLIF(uf.gross_amount_sek, 0),
                                    NULLIF(uf.net_amount, 0),
                                    NULLIF(uf.net_amount_sek, 0)
                                ) IS NULL
                             OR ABS(
                                   COALESCE(
                                       NULLIF(uf.gross_amount, 0),
                                       NULLIF(uf.gross_amount_sek, 0),
                                       NULLIF(uf.net_amount, 0),
                                       NULLIF(uf.net_amount_sek, 0)
                                   ) - %s
                               ) <= %s
                           )
                        AND (uf.credit_card_match IS NULL OR uf.credit_card_match = 0)
                        AND il.id IS NULL
                  ORDER BY
                           CASE WHEN match_amount IS NULL THEN 1 ELSE 0 END,
                           ABS(match_amount - %s) ASC,
                           COALESCE(uf.purchase_datetime, uf.created_at) DESC
                      LIMIT %s
                    """,
                    (
                        date_value,
                        MATCH_DATE_WINDOW_DAYS,
                        amount,
                        float(MATCH_AMOUNT_TOLERANCE),
                        amount,
                        MAX_RECEIPT_CANDIDATES,
                    ),
                )
                return cur.fetchall() or []
        except Exception:
            return []

    for row in pending_rows:
        line_id = int(row[0])
        tx_date = row[1]
        amount = _safe_decimal(row[2])
        merchant_hint = row[3]
        match_status = row[4]
        pending[line_id] = {
            "transaction_date": tx_date,
            "amount": amount,
            "merchant_hint": merchant_hint,
            "initial_status": match_status,
            "matched": False,
            "candidates": [],
        }
        if amount is None or tx_date is None:
            continue
        for candidate in _fetch_receipt_candidates(tx_date, amount):
            receipt_id = str(candidate[0])
            purchase_dt = candidate[1]
            candidate_amount = _safe_decimal(candidate[2])
            company_name = candidate[3]
            if isinstance(purchase_dt, datetime):
                receipt_date = purchase_dt.date()
            elif isinstance(purchase_dt, date):
                receipt_date = purchase_dt
            else:
                receipt_date = None
            if isinstance(tx_date, datetime):
                line_dt = tx_date.date()
            elif isinstance(tx_date, date):
                line_dt = tx_date
            elif isinstance(tx_date, str):
                try:
                    line_dt = datetime.fromisoformat(tx_date[:10]).date()
                except Exception:
                    line_dt = None
            else:
                line_dt = None
            if line_dt is not None and receipt_date is not None:
                date_diff = abs((line_dt - receipt_date).days)
            else:
                date_diff = 9999
            if amount is not None and candidate_amount is not None and amount != 0:
                amount_diff = abs(amount - candidate_amount)
                ratio = min((amount_diff / abs(amount)), Decimal("1"))
            else:
                amount_diff = Decimal("999999")
                ratio = Decimal("1")
            confidence = max(
                0.25,
                float(
                    min(
                        Decimal("0.95"),
                        Decimal("1")
                        - ratio * Decimal("0.6")
                        - Decimal(min(date_diff, 30)) / Decimal("120"),
                    )
                ),
            )
            pending[line_id]["candidates"].append(
                {
                    "receipt_id": receipt_id,
                    "purchase_datetime": purchase_dt,
                    "amount": candidate_amount,
                    "company_name": company_name,
                    "amount_diff": amount_diff,
                    "date_diff": date_diff,
                    "confidence": confidence,
                }
            )
        log_event(
            logger,
            "matching.auto.candidates_collected",
            invoice_id=document_id,
            line_id=line_id,
            candidates=len(pending[line_id]["candidates"]),
            merchant_hint=merchant_hint,
            amount=amount,
        )

    matched = 0
    used_receipts: set[str] = set()
    line_order = sorted(
        pending.keys(),
        key=lambda lid: (len(pending[lid].get("candidates") or []), lid),
    )

    for line_id in line_order:
        line_ctx = pending.get(line_id)
        if not line_ctx or line_ctx.get("matched"):
            continue
        candidates = line_ctx.get("candidates") or []
        if not candidates:
            log_event(
                logger,
                "matching.auto.no_candidates",
                invoice_id=document_id,
                line_id=line_id,
                merchant_hint=line_ctx.get("merchant_hint"),
                amount=line_ctx.get("amount"),
            )
            continue

        item_id, matched_amount = _select_credit_item_for_line(line_ctx, credit_items)
        if item_id is None:
            log_event(
                logger,
                "matching.auto.no_invoice_item",
                invoice_id=document_id,
                line_id=line_id,
                merchant_hint=line_ctx.get("merchant_hint"),
            )
            continue

        for candidate in sorted(
            candidates, key=lambda c: (c["amount_diff"], c["date_diff"])
        ):
            receipt_id = candidate["receipt_id"]
            if receipt_id in used_receipts:
                continue

            updated = transition_line_status_and_link(
                line_id,
                receipt_id,
                candidate["confidence"],
                InvoiceLineMatchStatus.AUTO,
                (
                    InvoiceLineMatchStatus.PENDING,
                    InvoiceLineMatchStatus.UNMATCHED,
                ),
            )
            if not updated:
                log_event(
                    logger,
                    "matching.auto.transition_blocked",
                    invoice_id=document_id,
                    line_id=line_id,
                    receipt_id=receipt_id,
                )
                continue

            line_ctx["matched"] = True
            line_ctx["matched_file_id"] = receipt_id
            used_receipts.add(receipt_id)
            matched += 1

            try:
                with db_cursor() as cur:
                    cur.execute(
                        (
                            "INSERT INTO invoice_line_history "
                            "(invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                            "VALUES (%s, 'matched', 'system', NULL, %s, %s)"
                        ),
                        (line_id, receipt_id, "auto-match-ai5"),
                    )
            except Exception:
                pass

            if matched_amount is None:
                matched_amount = line_ctx.get("amount")

            persist_ok = True
            try:
                _persist_credit_card_match(
                    receipt_id,
                    item_id,
                    matched_amount,
                    candidate["confidence"],
                    True,
                    match_origin="auto",
                )
            except Exception:
                persist_ok = False
                logger.exception(
                    "Failed to persist credit card match (auto) for line %s -> %s",
                    line_id,
                    receipt_id,
                )
                log_event(
                    logger,
                    "matching.auto.persist_failed",
                    invoice_id=document_id,
                    line_id=line_id,
                    receipt_id=receipt_id,
                    invoice_item_id=item_id,
                    level="error",
                )
            record_invoice_decision("matched")
            log_event(
                logger,
                "matching.auto.matched",
                invoice_id=document_id,
                line_id=line_id,
                receipt_id=receipt_id,
                invoice_item_id=item_id,
                amount_diff=candidate["amount_diff"],
                date_diff=candidate["date_diff"],
                confidence=candidate["confidence"],
                matched_amount=matched_amount,
                persisted=persist_ok,
            )
            break

    for line_id, ctx in pending.items():
        if ctx.get("matched"):
            continue
        if ctx.get("initial_status") == InvoiceLineMatchStatus.UNMATCHED.value:
            continue
        updated = transition_line_status(
            line_id,
            InvoiceLineMatchStatus.UNMATCHED,
            (
                InvoiceLineMatchStatus.PENDING,
                InvoiceLineMatchStatus.UNMATCHED,
            ),
        )
        if not updated:
            continue
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "INSERT INTO invoice_line_history "
                        "(invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                        "VALUES (%s, 'no_match', 'system', NULL, NULL, %s)"
                    ),
                    (line_id, "auto-match-ai5-unmatched"),
                )
        except Exception:
            pass
        record_invoice_decision("unmatched")
        log_event(
            logger,
            "matching.auto.marked_unmatched",
            invoice_id=document_id,
            line_id=line_id,
            previous_status=ctx.get("initial_status"),
        )

    total_lines_db: Optional[int] = None
    matched_lines_db: Optional[int] = None
    if db_cursor is not None:
        try:
            total_lines = 0
            matched_lines = 0
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT COUNT(*), SUM(CASE WHEN match_status IN (%s, %s, %s) "
                        "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%%s"
                    ),
                    (
                        InvoiceLineMatchStatus.AUTO.value,
                        InvoiceLineMatchStatus.MANUAL.value,
                        InvoiceLineMatchStatus.CONFIRMED.value,
                        document_id,
                    ),
                )
                row = cur.fetchone()
                if row:
                    total_lines = int(row[0] or 0)
                    matched_lines = int(row[1] or 0)
                    total_lines_db = total_lines
                    matched_lines_db = matched_lines
            metadata = _load_invoice_metadata(document_id) or {}
            metadata.setdefault("line_counts", {})
            metadata["line_counts"] = {
                "total": total_lines,
                "matched": matched_lines,
                "unmatched": max(total_lines - matched_lines, 0),
            }
            _update_invoice_metadata(document_id, metadata)
        except Exception:
            pass

    log_event(
        logger,
        "matching.auto.completed",
        invoice_id=document_id,
        matched=matched,
        evaluated=len(pending_rows),
        total_lines=total_lines_db,
        matched_lines=matched_lines_db,
    )
    return (matched, len(pending_rows))

def refresh_invoice_match_state(document_id: str) -> tuple[int, int]:
    """Recompute invoice match counters and update lifecycle states."""
    if db_cursor is None:
        return (0, 0)

    total_lines = 0
    matched_lines = 0
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT COUNT(*), SUM(CASE WHEN match_status IN (%s, %s, %s) "
                    "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%%s"
                ),
                (
                    InvoiceLineMatchStatus.AUTO.value,
                    InvoiceLineMatchStatus.MANUAL.value,
                    InvoiceLineMatchStatus.CONFIRMED.value,
                    document_id,
                ),
            )
            row = cur.fetchone()
            if row:
                total_lines = int(row[0] or 0)
                matched_lines = int(row[1] or 0)
    except Exception:
        log_event(
            logger,
            "matching.invoice_state.refresh_failed",
            invoice_id=document_id,
            reason="line_count_query_failed",
            level="error",
        )
        return (0, 0)

    try:
        metadata = _load_invoice_metadata(document_id) or {}
        metadata.setdefault("line_counts", {})
        metadata["line_counts"] = {
            "total": total_lines,
            "matched": matched_lines,
            "unmatched": max(total_lines - matched_lines, 0),
        }
        metadata["processing_status"] = metadata.get("processing_status")
        _update_invoice_metadata(document_id, metadata)
    except Exception:
        pass

    try:
        if total_lines == 0:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                (
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.MATCHED,
                (
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    InvoiceDocumentStatus.MATCHED,
                ),
            )
        elif matched_lines == 0:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                (
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.IMPORTED,
                (
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.IMPORTED,
                ),
            )
        elif matched_lines < total_lines:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                (
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.MATCHED,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                ),
            )
        else:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                (
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.MATCHED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    InvoiceDocumentStatus.MATCHED,
                ),
            )
    except Exception:
        pass

    return (total_lines, matched_lines)

__all__ = [
    "_ensure_creditcard_pages_and_ocr",
    "_load_credit_items_for_invoice",
    "_select_credit_item_for_line",
    "auto_match_invoice_lines",
    "refresh_invoice_match_state",
]

```

### File: `backend/src/api/reconciliation_firstcard/routes/status.py`

```python
# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Status endpoints for FirstCard invoice reconciliation.

Provides invoice processing status and detailed invoice information.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flask import jsonify

from .. import recon_bp
from ..utils.db_helpers import (
    count_invoice_lines,
    list_invoice_files,
    load_invoice_document,
    as_decimal,
)

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


from services.status_constants import (
    AiStatus,
    InvoiceProcessingStatus,
    InvoiceLineMatchStatus,
)


logger = logging.getLogger(__name__)

def _build_receipt_image_url(file_id: str) -> str:
    """Build a high-quality receipt image URL for preview purposes.

    Args:
        file_id: The unified_files id for a receipt or invoice page image.

    Returns:
        A relative URL to the receipt image endpoint, using original size and high quality.
    """
    return f"/ai/api/receipts/{file_id}/image?size=original&quality=high"


# OCR status constants
_OCR_COMPLETE_STATUSES = {
    AiStatus.OCR_DONE.value,
    AiStatus.COMPLETED.value,
    "processed",
    "ready",
    "ai_done",
}


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/status")
def invoice_status(invoice_id: str) -> Any:
    """Return processing status, OCR progress, and match stats for an invoice."""

    doc = load_invoice_document(invoice_id)
    if not doc:
        return jsonify({"error": "not_found"}), 404

    status, metadata, _ = doc
    source_file_id = metadata.get("source_file_id") or invoice_id
    files = list_invoice_files(source_file_id)

    page_records: list[dict[str, Any]] = []
    for record in files:
        page_number = record["other_data"].get("page_number")
        if page_number is None and record["id"] == source_file_id:
            # Single-page uploads reuse the main file without explicit numbering.
            page_number = 1 if metadata.get("detected_kind") != "pdf" else None
        if page_number is None:
            continue
        page_records.append(
            {
                "file_id": record["id"],
                "page_number": int(page_number),
                "status": record.get("ai_status") or AiStatus.UPLOADED.value,
                "url": _build_receipt_image_url(record["id"]),
            }
        )

    if not page_records and files:
        # Fallback for legacy metadata without page numbers.
        for idx, record in enumerate(files, 1):
            page_records.append(
                {
                    "file_id": record["id"],
                    "page_number": idx,
                    "status": record.get("ai_status") or AiStatus.UPLOADED.value,
                    "url": _build_receipt_image_url(record["id"]),
                }
            )

    total_pages = metadata.get("page_count") or len(page_records)
    if total_pages == 0 and page_records:
        total_pages = len(page_records)

    completed_pages = sum(
        1
        for page in page_records
        if (page.get("status") or "").lower() in _OCR_COMPLETE_STATUSES
    )

    if total_pages <= 0:
        total_pages = len(page_records)
    percentage = 0.0
    if total_pages:
        percentage = round((completed_pages / total_pages) * 100, 2)

    processing_status = metadata.get("processing_status")
    if not processing_status:
        processing_status = InvoiceProcessingStatus.OCR_DONE.value if completed_pages >= total_pages and total_pages else InvoiceProcessingStatus.OCR_PENDING.value

    ai_summary = metadata.get("ai_summary")
    if not ai_summary:
        for record in files:
            if record["id"] == source_file_id and record.get("ocr_raw"):
                snippet = (record["ocr_raw"] or "")
                ai_summary = snippet[:400]
                break

    total_lines, matched_lines = count_invoice_lines(invoice_id)

    invoice_summary = metadata.get("invoice_summary")
    if not isinstance(invoice_summary, dict):
        invoice_summary = None

    response = {
        "invoice_id": invoice_id,
        "status": status,
        "processing_status": processing_status,
        "source_file_id": source_file_id,
        "ocr_progress": {
            "total_pages": total_pages,
            "completed_pages": completed_pages,
            "percentage": percentage,
            "pages": page_records,
        },
        "ai_summary": ai_summary or "",
        "line_counts": {
            "total": total_lines,
            "matched": matched_lines,
            "unmatched": max(total_lines - matched_lines, 0),
        },
        "overall_confidence": metadata.get("overall_confidence"),
        "invoice_summary": invoice_summary,
        "creditcard_main_id": metadata.get("creditcard_main_id"),
        "period_start": metadata.get("period_start"),
        "period_end": metadata.get("period_end"),
    }

    return jsonify(response), 200


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>")
def invoice_detail(invoice_id: str) -> Any:
    if db_cursor is None:  # pragma: no cover
        return jsonify({"error": "not_found"}), 404

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT invoice_type,
                       status,
                       processing_status,
                       period_start,
                       period_end,
                       uploaded_at,
                       metadata_json
                  FROM invoice_documents
                 WHERE id = %s
                   AND deleted_at IS NULL
                """,
                (invoice_id,),
            )
            row = cur.fetchone()
    except Exception:
        row = None

    if not row:
        return jsonify({"error": "not_found"}), 404

    (
        invoice_type,
        status,
        processing_status,
        period_start,
        period_end,
        uploaded_at,
        metadata_raw,
    ) = row

    metadata: dict[str, Any] = {}
    if metadata_raw:
        try:
            metadata = json.loads(metadata_raw)
        except Exception:
            metadata = {}

    computed_total, computed_matched = count_invoice_lines(invoice_id)
    stored_counts = metadata.get("line_counts") if isinstance(metadata.get("line_counts"), dict) else None
    if isinstance(stored_counts, dict):
        total_lines = int(stored_counts.get("total") or computed_total)
        matched_lines = int(stored_counts.get("matched") or computed_matched)
        unmatched_lines = stored_counts.get("unmatched")
        if unmatched_lines is None:
            unmatched_lines = max(total_lines - matched_lines, 0)
    else:
        total_lines = computed_total
        matched_lines = computed_matched
        unmatched_lines = max(total_lines - matched_lines, 0)
    line_counts = {
        "total": total_lines,
        "matched": matched_lines,
        "unmatched": unmatched_lines,
    }
    metadata["line_counts"] = line_counts

    # Build page preview information for this invoice (used by the frontend preview modal).
    source_file_id = metadata.get("source_file_id") or invoice_id
    files = list_invoice_files(source_file_id)
    page_records: list[dict[str, Any]] = []
    for record in files:
        page_number = (record.get("other_data") or {}).get("page_number")
        if page_number is None and record.get("id") == source_file_id:
            page_number = 1 if metadata.get("detected_kind") != "pdf" else None
        if page_number is None:
            continue
        page_records.append(
            {
                "file_id": record["id"],
                "page_number": int(page_number),
                "status": record.get("ai_status") or AiStatus.UPLOADED.value,
                "url": _build_receipt_image_url(record["id"]),
            }
        )

    if not page_records and files:
        for idx, record in enumerate(files, 1):
            page_records.append(
                {
                    "file_id": record["id"],
                    "page_number": idx,
                    "status": record.get("ai_status") or AiStatus.UPLOADED.value,
                    "url": _build_receipt_image_url(record["id"]),
                }
            )
    page_records = sorted(page_records, key=lambda p: int(p.get("page_number") or 0))
    metadata["pages"] = page_records

    creditcard_main_id = metadata.get("creditcard_main_id")
    card_details: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []

    # Read card details from invoice_summary metadata if available
    summary_payload = metadata.get("invoice_summary")
    if isinstance(summary_payload, dict):
        if any(k in summary_payload for k in ["card_type", "card_name", "card_holder"]):
            card_details = {
                "card_type": summary_payload.get("card_type"),
                "card_name": summary_payload.get("card_name"),
                "card_number_masked": summary_payload.get("card_number_masked"),
                "card_holder": summary_payload.get("card_holder"),
            }

    # Read invoice lines from invoice_lines table (NEW approach)
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT il.id,
                           il.transaction_date,
                           il.merchant_name,
                           il.description,
                           il.amount,
                           NULL AS currency,
                           il.extraction_confidence AS confidence,
                           il.match_status,
                           il.match_score,
                           il.matched_file_id,
                           COALESCE(uf.purchase_datetime, uf.created_at) AS receipt_datetime,
                           COALESCE(
                               NULLIF(uf.gross_amount, 0),
                               NULLIF(uf.gross_amount_sek, 0),
                               NULLIF(uf.net_amount, 0),
                               NULLIF(uf.net_amount_sek, 0)
                           ) AS receipt_gross_amount,
                           uf.credit_card_match,
                           uf.created_at,
                           c.name AS vendor_name
                      FROM invoice_lines AS il
                 LEFT JOIN unified_files AS uf ON uf.id = il.matched_file_id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                     WHERE il.invoice_id = %s
                  ORDER BY il.id ASC
                    """,
                    (invoice_id,),
                )
                line_rows = cur.fetchall() or []
        except Exception:
            logger.exception("Failed to load invoice lines for %s", invoice_id)
            line_rows = []

        for (
            line_id,
            transaction_date,
            merchant_name,
            description,
            amount,
            currency,
            confidence,
            match_status,
            match_score,
            matched_file_id,
            receipt_purchase_dt,
            receipt_gross_amount,
            receipt_match_flag,
            receipt_created_at,
            receipt_vendor_name,
        ) in line_rows:
            matched_receipt: dict[str, Any] | None = None
            if matched_file_id:
                matched_receipt = {
                    "file_id": matched_file_id,
                    "purchase_datetime": receipt_purchase_dt.isoformat() if hasattr(receipt_purchase_dt, "isoformat") else receipt_purchase_dt,
                    "gross_amount": float(receipt_gross_amount) if receipt_gross_amount is not None else None,
                    "credit_card_match": bool(receipt_match_flag) if receipt_match_flag is not None else False,
                    "vendor_name": receipt_vendor_name,
                    "matched_at": receipt_created_at.isoformat() if hasattr(receipt_created_at, "isoformat") else receipt_created_at,
                }

            # Build lines array
            lines.append(
                {
                    "id": int(line_id),
                    "invoice_id": invoice_id,
                    "transaction_date": transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else transaction_date,
                    "amount": float(amount) if amount is not None else None,
                    "currency": currency,
                    "description": description or merchant_name or "",
                    "merchant_name": merchant_name,
                    "match_status": match_status or InvoiceLineMatchStatus.PENDING.value,
                    "match_score": float(match_score) if match_score is not None else None,
                    "matched_file_id": matched_file_id,
                    "matched_receipt": matched_receipt,
                    "confidence": float(confidence) if confidence is not None else None,
                }
            )

            # Build items array for backward compatibility (deprecated, but kept for now)
            # Map match_status to legacy matched flag
            matched_flag = 0
            if match_status == InvoiceLineMatchStatus.MANUAL.value:
                matched_flag = 2
            elif match_status in (InvoiceLineMatchStatus.AUTO.value, InvoiceLineMatchStatus.CONFIRMED.value):
                matched_flag = 1

            items.append(
                {
                    "id": int(line_id),
                    "line_no": None,  # Not stored in invoice_lines
                    "purchase_date": transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else transaction_date,
                    "merchant_name": merchant_name,
                    "merchant_city": None,  # Not stored in invoice_lines
                    "amount_original": float(amount) if amount is not None else None,
                    "amount_sek": float(amount) if amount is not None else None,
                    "gross_amount": float(amount) if amount is not None else None,
                    "net_amount": None,
                    "vat_rate": None,
                    "currency_original": currency,
                    "matched": matched_flag,
                    "matched_receipt_id": matched_file_id,
                }
            )

    summary_payload = metadata.get("invoice_summary") if isinstance(metadata.get("invoice_summary"), dict) else None

    invoice_payload = {
        "id": invoice_id,
        "invoice_type": invoice_type,
        "status": status,
        "processing_status": processing_status or metadata.get("processing_status"),
        "period_start": metadata.get("period_start") or period_start,
        "period_end": metadata.get("period_end") or period_end,
        "uploaded_at": str(uploaded_at) if uploaded_at else None,
        "submitted_by": metadata.get("submitted_by"),
        "line_counts": line_counts,
        "invoice_summary": summary_payload,
        "overall_confidence": metadata.get("overall_confidence"),
        "creditcard_main_id": metadata.get("creditcard_main_id"),
        "invoice_number": (summary_payload or {}).get("invoice_number") or metadata.get("invoice_number"),
        "pages": metadata.get("pages") or [],
        "metadata": metadata,
    }
    if card_details:
        invoice_payload["creditcard_details"] = card_details

    return jsonify({"invoice": invoice_payload, "lines": lines, "items": items}), 200

```

### File: `main-system/app-frontend/src/ui/components/DocumentPreviewModal.jsx`

```jsx
import React from 'react'
import { FiX, FiChevronLeft, FiChevronRight, FiMaximize, FiMinimize } from 'react-icons/fi'
import { api } from '../api'

/**
 * DocumentPreviewModal
 *
 * A lightweight preview modal for FirstCard invoices. It focuses purely on rendering
 * the largest possible page image, with pagination and zoom controls.
 *
 * The backend is expected to return `invoice.pages` (or `invoice.metadata.pages`) where each page contains:
 *   - file_id: string
 *   - page_number: number
 *   - url: string (preferred)
 *
 * If `url` is missing, this component falls back to the receipt image endpoint using `file_id`.
 */
export default function DocumentPreviewModal({
  open,
  documentId,
  onClose,
}) {
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState(null)
  const [pages, setPages] = React.useState([])
  const [currentPageIndex, setCurrentPageIndex] = React.useState(0)
  const [zoom, setZoom] = React.useState(1)

  const resolvePageUrl = React.useCallback((page) => {
    if (!page) return null
    if (page.url) return page.url
    const fileId = page.file_id || page.id
    if (!fileId) return null
    return `/ai/api/receipts/${fileId}/image?size=original&quality=high`
  }, [])

  React.useEffect(() => {
    if (!open || !documentId) {
      setPages([])
      setCurrentPageIndex(0)
      setZoom(1)
      setError(null)
      return
    }

    const fetchPages = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${documentId}`)
        if (!res.ok) throw new Error(`Status ${res.status}`)

        const data = await res.json()
        const invoicePages = data?.invoice?.pages || data?.invoice?.metadata?.pages || []
        const normalized = Array.isArray(invoicePages)
          ? invoicePages
              .map((p, idx) => ({
                ...p,
                page_number: p.page_number || idx + 1,
                url: resolvePageUrl(p),
              }))
              .filter((p) => !!p.url)
              .sort((a, b) => (a.page_number || 0) - (b.page_number || 0))
          : []

        if (!normalized.length) {
          setPages([])
          setError('Inga sidor hittades för detta dokument.')
        } else {
          setPages(normalized)
          setCurrentPageIndex(0)
          setZoom(1)
        }
      } catch (err) {
        console.error('Failed to load document pages', err)
        setPages([])
        setError('Kunde inte ladda dokumentet.')
      } finally {
        setLoading(false)
      }
    }

    fetchPages()
  }, [open, documentId, resolvePageUrl])

  if (!open) return null

  const hasMultiplePages = pages.length > 1
  const currentPage = pages[currentPageIndex]
  const currentUrl = resolvePageUrl(currentPage)

  const goPrev = () => setCurrentPageIndex((idx) => Math.max(0, idx - 1))
  const goNext = () => setCurrentPageIndex((idx) => Math.min(pages.length - 1, idx + 1))

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal w-full h-full max-w-6xl max-h-[90vh] flex flex-col p-0 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
          <div className="text-white font-medium">
            Dokumentgranskning {hasMultiplePages && `(${currentPageIndex + 1} / ${pages.length})`}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
              className="icon-button"
              aria-label="Zoom out"
            >
              <FiMinimize />
            </button>
            <span className="text-xs text-gray-400 w-12 text-center">{Math.round(zoom * 100)}%</span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(4, z + 0.25))}
              className="icon-button"
              aria-label="Zoom in"
            >
              <FiMaximize />
            </button>
            <div className="w-px h-6 bg-gray-700 mx-2" />
            <button type="button" onClick={onClose} className="icon-button" aria-label="Close">
              <FiX />
            </button>
          </div>
        </div>

        <div className="flex-1 relative bg-gray-900 overflow-auto flex items-center justify-center p-4">
          {loading ? (
            <div className="loading-spinner" />
          ) : error ? (
            <div className="text-gray-300 p-6">{error}</div>
          ) : !currentUrl ? (
            <div className="text-gray-300 p-6">Kunde inte hitta någon bild att visa.</div>
          ) : (
            <div
              className="relative transition-transform duration-200 ease-out"
              style={{ transform: `scale(${zoom})` }}
            >
              <img
                src={currentUrl}
                alt={`Sida ${currentPageIndex + 1}`}
                className="max-w-full shadow-2xl"
                onError={() => setError('Kunde inte visa bild.')}
              />
            </div>
          )}

          {hasMultiplePages && !loading && !error && (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  goPrev()
                }}
                className="absolute left-4 top-1/2 -translate-y-1/2 icon-button bg-gray-800/80 hover:bg-gray-700/80"
                disabled={currentPageIndex === 0}
                aria-label="Previous page"
              >
                <FiChevronLeft />
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  goNext()
                }}
                className="absolute right-4 top-1/2 -translate-y-1/2 icon-button bg-gray-800/80 hover:bg-gray-700/80"
                disabled={currentPageIndex === pages.length - 1}
                aria-label="Next page"
              >
                <FiChevronRight />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

```

### File: `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

```jsx
import React from 'react'
import {
  FiRefreshCw,
  FiCheckCircle,
  FiAlertTriangle,
  FiFileText,
  FiUpload,
  FiEye,
  FiLink,
  FiX,
  FiChevronRight,
  FiAlertCircle,
  FiTrash2,
  FiPercent,
} from 'react-icons/fi'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'
import DocumentPreviewModal from '../components/DocumentPreviewModal'
import { api } from '../api'

const MOJIBAKE_PATTERN = /\u00c3[\x80-\xBF]/;
let cachedUtf8Decoder = null;

function ensureUtf8Decoder() {
  if (cachedUtf8Decoder) {
    return cachedUtf8Decoder;
  }
  if (typeof TextDecoder === 'function') {
    try {
      cachedUtf8Decoder = new TextDecoder('utf-8', { fatal: false });
    } catch (err) {
      cachedUtf8Decoder = null;
    }
  }
  return cachedUtf8Decoder;
}

function fixMojibakeString(value) {
  if (typeof value !== 'string' || value.length === 0) {
    return value;
  }
  if (!MOJIBAKE_PATTERN.test(value)) {
    return value;
  }
  try {
    const decoder = ensureUtf8Decoder();
    if (decoder) {
      const bytes = new Uint8Array(value.length);
      for (let index = 0; index < value.length; index += 1) {
        bytes[index] = value.charCodeAt(index) & 0xff;
      }
      const decoded = decoder.decode(bytes);
      if (decoded && decoded !== value) {
        return decoded;
      }
    }
  } catch (err) {
    // Swallow and fall back
  }
  if (typeof Buffer !== 'undefined') {
    try {
      const decoded = Buffer.from(value, 'latin1').toString('utf8');
      if (decoded && decoded !== value) {
        return decoded;
      }
    } catch (err) {
      // Ignore buffer fallback failure
    }
  }
  if (typeof decodeURIComponent === 'function' && typeof escape === 'function') {
    try {
      const decoded = decodeURIComponent(escape(value));
      if (decoded && decoded !== value) {
        return decoded;
      }
    } catch (err) {
      // ignore
    }
  }
  return value;
}

function fixEncodingDeep(value) {
  if (typeof value === 'string') {
    return fixMojibakeString(value);
  }
  if (Array.isArray(value)) {
    return value.map((entry) => fixEncodingDeep(entry));
  }
  if (value && typeof value === 'object') {
    const next = {};
    for (const [key, nested] of Object.entries(value)) {
      next[key] = fixEncodingDeep(nested);
    }
    return next;
  }
  return value;
}

const DOCUMENT_STATUS_MAP = [
  { ids: ['matched', 'matchad', 'completed', 'done', 'success'], label: 'Matchad', tone: 'success' },
  { ids: ['partially_matched', 'ready_for_matching', 'processed'], label: 'Bearbetad', tone: 'success' },
  { ids: ['processing', 'matching', 'running', 'ai_processing', 'ocr_done'], label: 'Under bearbetning', tone: 'processing' },
  { ids: ['queued', 'pending', 'created', 'uploaded', 'imported', 'ocr_pending'], label: 'Ej bearbetad', tone: 'pending' },
  { ids: ['failed', 'error'], label: 'Fel', tone: 'failed' },
]

const LINE_STATUS_MAP = {
  auto: { label: 'Auto', tone: 'success' },
  manual: { label: 'Manuell', tone: 'processing' },
  confirmed: { label: 'Bekräftad', tone: 'success' },
  unmatched: { label: 'Obearbetad', tone: 'pending' },
  ignored: { label: 'Ignorerad', tone: 'pending' },
  pending: { label: 'I kö', tone: 'pending' },
}

const IMPORT_STAGE_LABELS = {
  src_portal: 'Portaluppladdning',
  src_ftp: 'FTP-import',
  src_fc: 'FirstCard-uppladdning',
  ingest_store: 'Lagra filmetadata',
  ingest_wf1: 'Skapa WF1',
  fc_create: 'Skapa FC-dokument',
  fc_ocr: 'OCR FirstCard',
  fc_parse: 'AI6 – FC-parsning',
  fc_ready: 'FC redo för matchning',
  fc_is_fc: 'FC-verifiering',
  detect_type: 'AI1 – Dokumentklassning',
  r_ocr: 'OCR kvitto',
  r_ai3: 'AI3 – Dataextraktion',
  r_ai4: 'AI4 – Normalisering',
  r_persist: 'Spara extraherad data',
  r_queue_match: 'Köa för matchning',
  ai5: 'AI5 – Matchning',
  m_found: 'Match hittad?',
  m_link: 'Länka kvitto',
  m_unmatched: 'Omatchade rader',
  finalize_ok: 'Slutförd',
  finalize_fail: 'Avslutad med fel',
  manual_review: 'Manuell granskning',
  resume_dispatch: 'Återupptar',
  restart_dispatch: 'Omstartar',
  KLAR: 'KLAR',
}

const toneClass = {
  success: 'status-passed',
  processing: 'status-processing',
  pending: 'status-pending',
  failed: 'status-failed',
}

const INITIAL_SYSTEM_SUMMARY = {
  receipts: { matched: 0, total: 0 },
  purchases: { unmatched: 0, total: 0 },
  invoices: { incomplete: 0, total: 0 },
}

// Map stage keys to tone colors
function getStageResultTone(stageKey) {
  if (!stageKey) return 'pending'

  // Completed/success stages
  if (['finalize_ok', 'KLAR', 'm_link', 'fc_ready'].includes(stageKey)) {
    return 'success'
  }

  // Failed stages
  if (['finalize_fail'].includes(stageKey) || stageKey.includes('fail')) {
    return 'failed'
  }

  // Processing stages (everything else is in progress)
  return 'processing'
}

function normalizeStatus(status) {
  return String(status ?? '').toLowerCase()
}

function describeDocumentStatus(status) {
  const normalized = normalizeStatus(status)
  const match = DOCUMENT_STATUS_MAP.find(({ ids }) => ids.includes(normalized))
  if (match) {
    return match
  }
  return { label: status || 'Okänd', tone: 'pending' }
}

function describeLineStatus(status) {
  if (!status) {
    return LINE_STATUS_MAP.pending
  }
  return LINE_STATUS_MAP[normalizeStatus(status)] ?? { label: status, tone: 'pending' }
}

function formatDate(value, withTime = true) {
  if (!value) {
    return '-'
  }
  try {
    const raw = typeof value === 'string' ? value : value?.toString?.()
    if (!raw) {
      return '-'
    }
    const parsed = raw.length === 10 ? new Date(`${raw}T00:00:00Z`) : new Date(raw)
    if (Number.isNaN(parsed.getTime())) {
      return raw
    }
    return parsed.toLocaleString('sv-SE', withTime
      ? { dateStyle: 'short', timeStyle: 'short' }
      : { dateStyle: 'short' })
  } catch (error) {
    return typeof value === 'string' ? value : '-'
  }
}

function formatNumber(value) {
  const numeric = Number(value ?? 0)
  if (Number.isNaN(numeric)) {
    return '0'
  }
  return numeric.toLocaleString('sv-SE')
}

function describeProcessingStatus(status) {
  const normalized = normalizeStatus(status)
  switch (normalized) {
    case 'ocr_pending':
      return { label: 'OCR pågår', tone: 'processing' }
    case 'ocr_done':
      return { label: 'OCR klar', tone: 'processing' }
    case 'ai_processing':
      return { label: 'AI6 bearbetar', tone: 'processing' }
    case 'ready_for_matching':
      return { label: 'Redo för matchning', tone: 'success' }
    case 'matching_completed':
      return { label: 'Matchning klar', tone: 'success' }
    case 'failed':
      return { label: 'Misslyckades', tone: 'failed' }
    default:
      return { label: status || 'Okänd', tone: 'processing' }
  }
}

function describeFirstCardStatus(statement) {
  if (!statement) {
    return { label: 'Okänd', tone: 'pending' }
  }

  // Use current_stage_key from workflow if available
  const stageKey = statement.current_stage_key
  if (stageKey && IMPORT_STAGE_LABELS[stageKey]) {
    return {
      label: IMPORT_STAGE_LABELS[stageKey],
      tone: getStageResultTone(stageKey),
    }
  }

  // Fallback to processing_status if no stage key
  const processing = normalizeStatus(statement.processing_status || statement.status)
  switch (processing) {
    case 'uploaded':
    case 'imported':
    case 'ocr_pending':
      return { label: 'PDF', tone: 'pending' }
    case 'ocr_done':
    case 'ai_processing':
      return { label: 'OCR', tone: 'processing' }
    case 'ready_for_matching':
      return { label: 'AI5', tone: 'processing' }
    case 'matching_completed':
    case 'completed':
      return { label: 'Match Done (AI6)', tone: 'success' }
    case 'failed':
      return { label: 'Fel', tone: 'failed' }
    default:
      return describeDocumentStatus(statement.status)
  }
}

function formatStageLabel(key) {
  if (!key) {
    return 'Okänd'
  }
  if (IMPORT_STAGE_LABELS[key]) {
    return IMPORT_STAGE_LABELS[key]
  }
  if (key.endsWith('_start')) {
    const base = key.replace(/_start$/, '')
    const label = IMPORT_STAGE_LABELS[base] || base
    return `${label} – start`
  }
  if (key.endsWith('_end')) {
    const base = key.replace(/_end$/, '')
    const label = IMPORT_STAGE_LABELS[base] || base
    return `${label} – klart`
  }
  return key
}


const currencyFormatter = new Intl.NumberFormat('sv-SE', {
  style: 'currency',
  currency: 'SEK',
  minimumFractionDigits: 2,
})

function formatAmount(value) {
  if (value === null || value === undefined) {
    return '-'
  }
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return String(value)
  }
  return currencyFormatter.format(num)
}

function formatCurrency(value, currency = 'SEK') {
  if (value === null || value === undefined) {
    return '-'
  }
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return String(value)
  }
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(num)
  } catch (error) {
    return currencyFormatter.format(num)
  }
}

function formatDurationMs(durationMs) {
  if (durationMs === null || durationMs === undefined) {
    return null
  }
  const value = Number(durationMs)
  if (!Number.isFinite(value) || value < 0) {
    return null
  }
  if (value < 1000) {
    return `${Math.round(value)} ms`
  }
  const seconds = value / 1000
  if (seconds < 60) {
    const rounded = seconds < 10 ? seconds.toFixed(2) : seconds.toFixed(1)
    return `${rounded.replace(/\.0+$/, '')} s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds - minutes * 60)
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}m`
}

const initialCandidatesState = {
  open: false,
  line: null,
  candidates: [],
  loading: false,
}

const INITIAL_LOG_STATE = {
  open: false,
  loading: false,
  error: null,
  data: null,
  invoiceId: null,
}

function buildUploadErrorMessage(status, payload) {
  const code = payload?.error
  switch (code) {
    case 'duplicate_file':
      return 'Filen har redan laddats upp tidigare.'
    case 'unsupported_file_type':
      return 'Filtypen stöds inte. Ladda upp en PDF eller bildfil.'
    case 'empty_file':
      return 'Filen var tom.'
    case 'missing_file':
      return 'Ingen fil skickades.'
    case 'upload_failed':
      return payload?.details
        ? `Serverfel: ${payload.details}`
        : 'Servern rapporterade ett fel under uppladdningen.'
    default:
      if (status === 413) {
        return 'Filen är för stor.'
      }
      if (status === 415) {
        return 'Filtypen stöds inte.'
      }
      if (status >= 500) {
        return 'Serverfel uppstod.'
      }
      if (status >= 400) {
        return `Fel ${status}.`
      }
      return 'Okänt fel.'
  }
}

export default function CompanyCard() {
  const [items, setItems] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const [documentFeedback, setDocumentFeedback] = React.useState(null)
  const [matchingDocumentId, setMatchingDocumentId] = React.useState(null)

  const [selectedDocumentId, setSelectedDocumentId] = React.useState(null)
  const [previewOpen, setPreviewOpen] = React.useState(false)
  const [previewInvoiceId, setPreviewInvoiceId] = React.useState(null)
  const selectedDocumentIdRef = React.useRef(null)
  const [selectedDocument, setSelectedDocument] = React.useState(null)
  const [documentLines, setDocumentLines] = React.useState([])
  const [documentItems, setDocumentItems] = React.useState([])
  const [systemSummary, setSystemSummary] = React.useState(INITIAL_SYSTEM_SUMMARY)
  const [systemSummaryLoading, setSystemSummaryLoading] = React.useState(false)
  const [detailLoading, setDetailLoading] = React.useState(false)

  const [candidateState, setCandidateState] = React.useState(initialCandidatesState)
  const [assigningLineId, setAssigningLineId] = React.useState(null)
  const [candidateFeedback, setCandidateFeedback] = React.useState(null)
  const [deletingDocumentId, setDeletingDocumentId] = React.useState(null)

  const [previewReceipt, setPreviewReceipt] = React.useState(null)
  const [previewImage, setPreviewImage] = React.useState(null)
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false)
  const [logState, setLogState] = React.useState(INITIAL_LOG_STATE)
  const [logActionState, setLogActionState] = React.useState({ clearing: false, error: '', success: '' })

  const [sortColumn, setSortColumn] = React.useState('updated_at')
  const [sortDirection, setSortDirection] = React.useState('desc')
  const [sortLineColumn, setSortLineColumn] = React.useState('transaction_date')
  const [sortLineDirection, setSortLineDirection] = React.useState('desc')

  React.useEffect(() => {
    selectedDocumentIdRef.current = selectedDocumentId
  }, [selectedDocumentId])

  const loadSystemSummary = React.useCallback(async () => {
    setSystemSummaryLoading(true)
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/summary')
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      let payload = await res.json()
      payload = fixEncodingDeep(payload)
      setSystemSummary({
        receipts: {
          matched: Number(payload?.receipts?.matched) || 0,
          total: Number(payload?.receipts?.total) || 0,
        },
        purchases: {
          unmatched: Number(payload?.purchases?.unmatched) || 0,
          total: Number(payload?.purchases?.total) || 0,
        },
        invoices: {
          incomplete: Number(payload?.invoices?.incomplete) || 0,
          total: Number(payload?.invoices?.total) || 0,
        },
      })
    } catch (error) {
      console.error('Failed to load FirstCard summary', error)
    } finally {
      setSystemSummaryLoading(false)
    }
  }, [])

  const loadStatements = React.useCallback(async (preferredId = selectedDocumentIdRef.current) => {
    setLoading(true)
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      let data = await res.json()
      data = fixEncodingDeep(data)
      const nextItems = Array.isArray(data?.statements) ? data.statements : []
      setItems(nextItems)
      if (!nextItems.length) {
        setSelectedDocumentId(null)
        setSelectedDocument(null)
        setDocumentLines([])
        setDocumentItems([])
        setDocumentFeedback({
          type: 'info',
          text: 'Inga kontoutdrag hittades. Ladda upp ett utdrag för att börja matcha kvitton.',
        })
      } else {
        const targetId = preferredId && nextItems.some((item) => item.id === preferredId)
          ? preferredId
          : nextItems[0].id
        setSelectedDocumentId(targetId)
        setDocumentItems([])
        setDocumentFeedback(null)
      }
      return nextItems
    } catch (error) {
      console.error('Failed to load statements', error)
      setItems([])
      setSelectedDocumentId(null)
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentItems([])
      setDocumentFeedback({
        type: 'error',
        text: `Fel vid hämtning av kontoutdrag: ${error instanceof Error ? error.message : error}`,
      })
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDocumentDetail = React.useCallback(async (invoiceId) => {
    if (!invoiceId) {
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentItems([])
      return
    }
    setDetailLoading(true)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      let data = await res.json()
      data = fixEncodingDeep(data)
      const invoice = data?.invoice ?? null
      const lines = Array.isArray(data?.lines) ? data.lines : []
      const items = Array.isArray(data?.items) ? data.items : []
      setSelectedDocument(invoice)
      setDocumentLines(lines)
      setDocumentItems(items)
    } catch (error) {
      console.error('Failed to load invoice detail', error)
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentItems([])
      setDocumentFeedback({
        type: 'error',
        text: `Kunde inte hämta detaljer för utdraget (${invoiceId}): ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setDetailLoading(false)
    }
  }, [])

  React.useEffect(() => {
    loadStatements()
    loadSystemSummary()

    const intervalId = setInterval(() => {
      loadStatements(selectedDocumentIdRef.current)
      loadSystemSummary()
    }, 15000) // Poll every 15 seconds

    return () => clearInterval(intervalId) // Cleanup on unmount
  }, [loadStatements, loadSystemSummary])

  React.useEffect(() => {
    if (selectedDocumentId) {
      loadDocumentDetail(selectedDocumentId)
    }
  }, [selectedDocumentId, loadDocumentDetail])

  const fetchInvoiceLog = React.useCallback(async (invoiceId) => {
    if (!invoiceId) {
      return
    }
    setLogState((prev) => ({
      open: true,
      loading: true,
      error: null,
      data: prev.invoiceId === invoiceId ? prev.data : null,
      invoiceId,
    }))
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}/log`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const payloadRaw = await res.json()
      const payload = fixEncodingDeep(payloadRaw)
      setLogState({
        open: true,
        loading: false,
        error: null,
        data: payload,
        invoiceId,
      })
    } catch (error) {
      console.error('Failed to fetch invoice log', error)
      setLogState({
        open: true,
        loading: false,
        error: error instanceof Error ? error.message : String(error),
        data: null,
        invoiceId,
      })
    }
  }, [])

  const closeLogViewer = React.useCallback(() => {
    setLogState(INITIAL_LOG_STATE)
    setLogActionState({ clearing: false, error: '', success: '' })
  }, [])

  const handleClearInvoiceLog = React.useCallback(async (invoiceId) => {
    if (!invoiceId || logActionState.clearing) {
      return
    }
    if (!window.confirm('Vill du rensa alla loggar för detta kontoutdrag? Detta går inte att ångra.')) {
      return
    }
    setLogActionState({ clearing: true, error: '', success: '' })
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}/log`, { method: 'DELETE' })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      await res.json().catch(() => ({}))
      setLogActionState({ clearing: false, error: '', success: 'Loggen rensades.' })
      await fetchInvoiceLog(invoiceId)
    } catch (error) {
      setLogActionState({
        clearing: false,
        error: error instanceof Error ? error.message : String(error),
        success: ''
      })
    }
  }, [fetchInvoiceLog, logActionState.clearing])

  const onMatchDocument = React.useCallback(async (statementId) => {
    if (!statementId) return
    setMatchingDocumentId(statementId)
    try {
      const response = await api.fetch('/ai/api/reconciliation/firstcard/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: statementId }),
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      setDocumentFeedback({ type: 'success', text: 'Matchning klar. Uppdaterar listan...' })
      await loadStatements(statementId)
      await loadDocumentDetail(statementId)
    } catch (error) {
      setDocumentFeedback({
        type: 'error',
        text: `Matchningen misslyckades: ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setMatchingDocumentId(null)
    }
  }, [loadStatements, loadDocumentDetail])

  const handleDeleteStatement = React.useCallback(
    async (statementId) => {
      if (!statementId) return
      if (typeof window !== 'undefined') {
        const confirmed = window.confirm('Är du säker på att du vill ta bort utdraget?')
        if (!confirmed) {
          return
        }
      }
      setDeletingDocumentId(statementId)
      try {
        const res = await api.fetch(`/ai/api/reconciliation/firstcard/statements/${statementId}`, {
          method: 'DELETE',
        })
        if (!res.ok) {
          let message = `Status ${res.status}`
          try {
            const payload = await res.json()
            if (payload?.error) {
              message = payload.error
            }
          } catch (error) {
            // ignore json parse errors
          }
          throw new Error(message)
        }
        if (selectedDocumentId === statementId) {
          setSelectedDocumentId(null)
          setSelectedDocument(null)
          setDocumentLines([])
          setDocumentItems([])
        }
        const refreshed = await loadStatements()
        if (Array.isArray(refreshed) && refreshed.length > 0) {
          setDocumentFeedback({
            type: 'success',
            text: 'Utdraget har tagits bort.',
          })
        }
      } catch (error) {
        setDocumentFeedback({
          type: 'error',
          text: `Kunde inte ta bort utdraget: ${error instanceof Error ? error.message : error}`,
        })
      } finally {
        setDeletingDocumentId(null)
      }
    },
    [loadStatements, selectedDocumentId],
  )

  const [matchingAllUnmatched, setMatchingAllUnmatched] = React.useState(false)

  const handleMatchAllUnmatched = React.useCallback(async () => {
    const unmatchedStatements = items.filter((item) => (item.line_counts?.unmatched ?? 0) > 0)
    if (!unmatchedStatements.length) {
      setDocumentFeedback({
        type: 'info',
        text: 'Inga omatchade poster hittades.',
      })
      return
    }

    setMatchingAllUnmatched(true)
    let successCount = 0
    let failCount = 0

    for (const statement of unmatchedStatements) {
      try {
        const response = await api.fetch('/ai/api/reconciliation/firstcard/match', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ document_id: statement.id }),
        })

        if (response.ok) {
          successCount++
        } else {
          failCount++
        }
      } catch (error) {
        console.error(`Failed to match statement ${statement.id}`, error)
        failCount++
      }
    }

    setMatchingAllUnmatched(false)
    await loadStatements(selectedDocumentIdRef.current)
    if (selectedDocumentId) {
      await loadDocumentDetail(selectedDocumentId)
    }

    if (failCount === 0) {
      setDocumentFeedback({
        type: 'success',
        text: `Matchning klar. ${successCount} utdrag har bearbetats.`,
      })
    } else {
      setDocumentFeedback({
        type: 'warning',
        text: `Matchning delvis klar. ${successCount} lyckades, ${failCount} misslyckades.`,
      })
    }
  }, [items, loadStatements, loadDocumentDetail, selectedDocumentId])

  const [resumingDocumentId, setResumingDocumentId] = React.useState(null)
  const pollingIntervalRef = React.useRef(null)

  // Silent refresh - no loading state, no flickering
  const silentRefreshStatements = React.useCallback(async () => {
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      if (!res.ok) {
        return null
      }
      let data = await res.json()
      data = fixEncodingDeep(data)
      return Array.isArray(data?.statements) ? data.statements : []
    } catch (error) {
      console.error('Silent refresh failed', error)
      return null
    }
  }, [])

  const startStatusPolling = React.useCallback((statementId) => {
    // Clear any existing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    // Poll every 2 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const refreshedItems = await silentRefreshStatements()

        if (!refreshedItems) return

        // Find the statement we're polling for
        const statement = refreshedItems.find(item => item.id === statementId)

        if (statement) {
          const processingStatus = statement.processing_status
          const status = statement.status

          // Only update state if data has actually changed
          setItems(prevItems => {
            const oldStatement = prevItems.find(item => item.id === statementId)
            const hasChanged = !oldStatement ||
                              oldStatement.processing_status !== processingStatus ||
                              oldStatement.status !== status

            return hasChanged ? refreshedItems : prevItems
          })

          // Stop polling if we reach a terminal state
          if (processingStatus === 'matching_completed' ||
              status === 'matched' ||
              status === 'failed' ||
              processingStatus === 'ready_for_matching') {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
            setResumingDocumentId(null)
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 2000)
  }, [silentRefreshStatements])

  // Cleanup polling on unmount
  React.useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  const handleResumeOrRestartInvoice = React.useCallback(async (statementId, processingStatus) => {
    if (!statementId) return
    setResumingDocumentId(statementId)

    try {
      // Determine if we should resume or restart based on processing_status
      const isCompleted = processingStatus === 'matching_completed' || processingStatus === 'ready_for_matching'
      const action = isCompleted ? 'restart' : 'resume'

      const response = await api.fetch(`/ai/api/reconciliation/firstcard/statements/${statementId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      const result = await response.json()

      setDocumentFeedback({
        type: 'success',
        text: `Fakturaimport ${action === 'restart' ? 'omstartas' : 'återupptas'}...`,
      })

      // Update the statement in state immediately with the new status
      if (result.processing_status || result.status || result.current_stage_key) {
        setStatements(prev => prev.map(stmt =>
          stmt.id === statementId
            ? {
                ...stmt,
                processing_status: result.processing_status || stmt.processing_status,
                status: result.status || stmt.status,
                current_stage_key: result.current_stage_key || stmt.current_stage_key,
              }
            : stmt
        ))
      }

      // Also reload from server to get full details
      await loadStatements(statementId)
      if (selectedDocumentId === statementId) {
        await loadDocumentDetail(statementId)
      }

      // Start polling for status updates
      startStatusPolling(statementId)

    } catch (error) {
      setDocumentFeedback({
        type: 'error',
        text: `Kunde inte återuppta fakturaimport: ${error instanceof Error ? error.message : error}`,
      })
      setResumingDocumentId(null)
    }
  }, [loadStatements, loadDocumentDetail, selectedDocumentId, startStatusPolling])

  const onOpenCandidates = React.useCallback(async (line) => {
    if (!line) return
    setCandidateState({ open: true, line, candidates: [], loading: true })
    setCandidateFeedback(null)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/lines/${line.id}/candidates`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const data = await res.json()
      const candidates = Array.isArray(data?.candidates) ? data.candidates : []
      setCandidateState({ open: true, line: data?.line ?? line, candidates, loading: false })
    } catch (error) {
      console.error('Failed to load candidates', error)
      setCandidateState({ open: true, line, candidates: [], loading: false })
      setCandidateFeedback({
        type: 'error',
        text: `Kunde inte hämta kandidater: ${error instanceof Error ? error.message : error}`,
      })
    }
  }, [])

  const closeCandidates = React.useCallback(() => {
    setCandidateState(initialCandidatesState)
    setCandidateFeedback(null)
  }, [])

  const assignCandidate = React.useCallback(async (lineId, receiptId) => {
    if (!lineId || !receiptId) return
    setAssigningLineId(lineId)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/lines/${lineId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matched_file_id: receiptId }),
      })
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      setCandidateFeedback({ type: 'success', text: 'Kvitto matchat mot raden.' })
      await loadStatements(selectedDocumentIdRef.current)
      await loadDocumentDetail(selectedDocumentIdRef.current)
      closeCandidates()
    } catch (error) {
      console.error('Failed to assign candidate', error)
      setCandidateFeedback({
        type: 'error',
        text: `Kunde inte matcha kvittot: ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setAssigningLineId(null)
    }
  }, [closeCandidates, loadDocumentDetail, loadStatements])

  const openReceiptPreview = React.useCallback((receiptId, extra = {}) => {
    if (!receiptId) return
    setPreviewReceipt({ id: receiptId, ...extra })
    setPreviewImage(null)
  }, [])

  const closeReceiptPreview = React.useCallback(() => {
    setPreviewReceipt(null)
    setPreviewImage(null)
  }, [])

  const handleReceiptUpdate = React.useCallback((updated) => {
    if (updated?.id && candidateState.line && updated.id === candidateState.line.matched_file_id) {
      loadDocumentDetail(selectedDocumentIdRef.current)
    } else {
      loadDocumentDetail(selectedDocumentIdRef.current)
    }
  }, [candidateState.line, loadDocumentDetail])

  const handleUploadComplete = React.useCallback(async ({ lastInvoiceId, successMessage } = {}) => {
    await loadStatements(lastInvoiceId)
    if (successMessage) {
      setDocumentFeedback({ type: 'success', text: successMessage })
    }
  }, [loadStatements])

  const handleSort = React.useCallback((column) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }, [sortColumn])

  const sortedItems = React.useMemo(() => {
    if (!sortColumn) return items

    const sorted = [...items].sort((a, b) => {
      let aVal, bVal

      switch (sortColumn) {
        case 'card_name':
          aVal = (a.card_name || '').toLowerCase()
          bVal = (b.card_name || '').toLowerCase()
          break
        case 'invoice_date':
          aVal = a.invoice_date || ''
          bVal = b.invoice_date || ''
          break
        case 'due_date':
          aVal = a.due_date || ''
          bVal = b.due_date || ''
          break
        case 'amount_to_pay':
          aVal = Number(a.amount_to_pay) || 0
          bVal = Number(b.amount_to_pay) || 0
          break
        case 'status':
          aVal = (a.status || '').toLowerCase()
          bVal = (b.status || '').toLowerCase()
          break
        case 'overall_confidence':
          aVal = Number(a.overall_confidence) || 0
          bVal = Number(b.overall_confidence) || 0
          break
        case 'total_lines':
          aVal = Number(a.line_counts?.total) || 0
          bVal = Number(b.line_counts?.total) || 0
          break
        case 'matched_lines':
          aVal = Number(a.line_counts?.matched) || 0
          bVal = Number(b.line_counts?.matched) || 0
          break
        case 'unmatched_lines':
          aVal = Number(a.line_counts?.unmatched) || 0
          bVal = Number(b.line_counts?.unmatched) || 0
          break
        case 'updated_at':
          aVal = a.updated_at || a.uploaded_at || ''
          bVal = b.updated_at || b.uploaded_at || ''
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
      return 0
    })

    return sorted
  }, [items, sortColumn, sortDirection])

  const detailSummaryCards = React.useMemo(() => {
    if (!selectedDocument) {
      return []
    }
    const summary = selectedDocument.invoice_summary ?? {}
    const details = selectedDocument.creditcard_details ?? {}
    const currency = summary.currency || 'SEK'
    const amountToPay = summary.amount_to_pay ?? summary.invoice_total
    const cardHolder = summary.card_holder || details.card_holder || 'Okänd'
    const cardType = summary.card_type || details.card_type
    const cardName = summary.card_name || details.card_name
    const cardNumberMasked = summary.card_number_masked || details.card_number_masked
    const cardDescriptor = [cardType, cardName].filter(Boolean).join(' - ') || cardNumberMasked || 'Okänt'
    const rows = [
      { label: 'Fakturanummer', value: summary.invoice_number || 'Okänt' },
      { label: 'Kortinnehavare', value: cardHolder },
      { label: 'Kort', value: cardDescriptor },
      {
        label: 'Belopp att betala',
        value: amountToPay != null ? formatCurrency(amountToPay, currency) : '-',
      },
      {
        label: 'AI-konfidens',
        value:
          selectedDocument.overall_confidence != null
            ? `${Math.round(Number(selectedDocument.overall_confidence) * 100)}%`
            : '–',
      },
    ]
    if (selectedDocument.creditcard_main_id) {
      rows.push({ label: 'Invoice-ID', value: selectedDocument.creditcard_main_id })
    }
    return rows
  }, [selectedDocument])

  const lineCounts = selectedDocument?.line_counts ?? {
    total: documentLines.length,
    matched: documentLines.filter((line) => line.match_status && line.match_status !== 'unmatched').length,
    unmatched: documentLines.filter((line) => !line.match_status || line.match_status === 'unmatched').length,
  }

  const receiptStats = systemSummary.receipts ?? INITIAL_SYSTEM_SUMMARY.receipts
  const purchaseStats = systemSummary.purchases ?? INITIAL_SYSTEM_SUMMARY.purchases
  const invoiceStats = systemSummary.invoices ?? INITIAL_SYSTEM_SUMMARY.invoices
  const totalInvoices = Number(invoiceStats.total) || 0
  const totalItems = Number(purchaseStats.total) || 0
  const matchedItems = Math.max(totalItems - (Number(purchaseStats.unmatched) || 0), 0)
  const matchedItemsPercent = totalItems ? Math.round((matchedItems / totalItems) * 100) : 0

  const handleSortLines = React.useCallback((column) => {
    if (sortLineColumn === column) {
      setSortLineDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortLineColumn(column)
      setSortLineDirection('asc')
    }
  }, [sortLineColumn])

  const sortedDocumentLines = React.useMemo(() => {
    if (!sortLineColumn) return documentLines

    const sorted = [...documentLines].sort((a, b) => {
      let aVal, bVal

      switch (sortLineColumn) {
        case 'transaction_date':
          aVal = a.transaction_date || ''
          bVal = b.transaction_date || ''
          break
        case 'description':
          aVal = (a.description || '').toLowerCase()
          bVal = (b.description || '').toLowerCase()
          break
        case 'amount':
          aVal = Number(a.amount) || 0
          bVal = Number(b.amount) || 0
          break
        case 'match_status':
          aVal = (a.match_status || '').toLowerCase()
          bVal = (b.match_status || '').toLowerCase()
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortLineDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortLineDirection === 'asc' ? 1 : -1
      return 0
    })

    return sorted
  }, [documentLines, sortLineColumn, sortLineDirection])

  const renderFeedback = () => {
    const feedback = candidateFeedback ?? documentFeedback
    if (!feedback) return null
    const tone = feedback.type === 'success' ? 'alert-success' : feedback.type === 'info' ? 'alert-info' : 'alert-error'
    return (
      <div className={`alert ${tone} mb-4`}>
        {feedback.text}
      </div>
    )
  }

  const renderLineTable = () => {
    if (!selectedDocumentId) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-400">
          <FiFileText className="text-3xl" />
          <div>Välj ett kontoutdrag för att se dess transaktioner.</div>
        </div>
      )
    }

    if (detailLoading) {
      return (
        <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
          <div className="loading-spinner" />
          <span>Laddar detaljer...</span>
        </div>
      )
    }

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
            <tr>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('transaction_date')}
              >
                Datum {sortLineColumn === 'transaction_date' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('description')}
              >
                Beskrivning {sortLineColumn === 'description' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('amount')}
              >
                Belopp {sortLineColumn === 'amount' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('match_status')}
              >
                Status {sortLineColumn === 'match_status' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th className="px-4 py-3">Matchat kvitto</th>
              <th className="px-4 py-3 text-right">Åtgärder</th>
            </tr>
          </thead>
          <tbody>
            {sortedDocumentLines.length > 0 ? sortedDocumentLines.map((line) => {
              const statusDetails = describeLineStatus(line.match_status)
              const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
              const matchedReceipt = line.matched_receipt
              const isAssigning = assigningLineId === line.id

              return (
                <tr key={line.id} className="border-t border-gray-700">
                  <td className="px-4 py-3 text-gray-200 whitespace-nowrap">{formatDate(line.transaction_date, false)}</td>
                  <td className="px-4 py-3 text-gray-100">
                    <div className="font-medium">{line.description || '–'}</div>
                    <div className="text-xs text-gray-400">Rad-ID: {line.id}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{line && line.currency ? formatCurrency(line.amount, line.currency) : formatAmount(line.amount)}</td>
                  <td className="px-4 py-3 text-gray-200">
                    <span className={`status-badge ${badgeClass}`}>{statusDetails.label}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-200">
                    {matchedReceipt ? (
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-gray-100">{matchedReceipt.vendor_name || 'Okänd leverantör'}</span>
                        <span className="text-xs text-gray-400">{formatDate(matchedReceipt.purchase_datetime, false)}  –  {formatAmount(matchedReceipt.gross_amount)}</span>
                        <button
                          type="button"
                          className="btn btn-text btn-xxs self-start"
                          onClick={() => openReceiptPreview(matchedReceipt.file_id, { credit_card_match: matchedReceipt.credit_card_match })}
                        >
                          Förhandsgranska
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">Ingen</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={(event) => {
                          event.stopPropagation()
                          onOpenCandidates(line)
                        }}
                      >
                        {candidateState.open && candidateState.line?.id === line.id ? 'Stäng kandidater' : 'Visa kandidater'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={isAssigning || !matchedReceipt}
                        onClick={(event) => {
                          event.stopPropagation()
                          if (matchedReceipt) {
                            openReceiptPreview(matchedReceipt.file_id, { credit_card_match: matchedReceipt.credit_card_match })
                          }
                        }}
                      >
                        Förhandsgranska
                      </button>
                    </div>
                  </td>
                </tr>
              )
            }) : (
              <tr className="border-t border-gray-700">
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">-</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    )
  }

  const renderItemTable = () => {
    if (detailLoading && !documentItems.length) {
      return (
        <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
          <div className="loading-spinner" />
          <span>Laddar transaktioner...</span>
        </div>
      )
    }

    const rows = documentItems.length ? documentItems : []

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
            <tr>
              <th className="px-4 py-3">Köpdatum</th>
              <th className="px-4 py-3">Butik</th>
              <th className="px-4 py-3">Stad</th>
              <th className="px-4 py-3">Belopp</th>
              <th className="px-4 py-3">Nettobelopp</th>
              <th className="px-4 py-3">Moms %</th>
              <th className="px-4 py-3">Valuta</th>
              <th className="px-4 py-3 text-center">Matchad</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((item, index) => {
              const matched = Number(item.matched) === 1
              const currency = item.currency_original || 'SEK'
              const amountOriginal = item.amount_original != null ? formatCurrency(item.amount_original, currency) : '-'
              const netAmount = item.net_amount != null ? formatCurrency(item.net_amount, currency) : '-'
              const vatDisplay = item.vat_rate != null ? `${Number(item.vat_rate).toFixed(2)}%` : '-'
              return (
                <tr key={item.id ?? `item-${index}`} className="border-t border-gray-700">
                  <td className="px-4 py-3 text-gray-200 whitespace-nowrap">{formatDate(item.purchase_date, false)}</td>
                  <td className="px-4 py-3 text-gray-100">{item.merchant_name || '-'}</td>
                  <td className="px-4 py-3 text-gray-200">{item.merchant_city || '-'}</td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{amountOriginal}</td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{netAmount}</td>
                  <td className="px-4 py-3 text-gray-200">{vatDisplay}</td>
                  <td className="px-4 py-3 text-gray-200">{item.currency_original || currency}</td>
                  <td className="px-4 py-3 text-center">
                    {matched ? (
                      <FiCheckCircle className="inline text-green-400" aria-label="Matchad" />
                    ) : (
                      <FiX className="inline text-red-400" aria-label="Ej matchad" />
                    )}
                  </td>
                </tr>
              )
            }) : (
              <tr className="border-t border-gray-700">
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">-</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    )
  }

  const candidatesContent = candidateState.open && candidateState.line ? (
    <div className="modal-backdrop" onClick={closeCandidates}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>Matchningskandidater</h3>
            <p className="text-sm text-gray-400 mt-1">
              Rad {candidateState.line.id}: {candidateState.line.description} - {(candidateState.line?.currency ? formatCurrency(candidateState.line.amount, candidateState.line.currency) : formatAmount(candidateState.line.amount))}
            </p>
          </div>
          <button type="button" className="icon-button" onClick={closeCandidates} aria-label="Stäng">
            <FiX />
          </button>
        </div>
        <div className="modal-body">
          {candidateFeedback && (
            <div className={`alert ${candidateFeedback.type === 'success' ? 'alert-success' : 'alert-error'} mb-4`}>
              {candidateFeedback.text}
            </div>
          )}
          {candidateState.loading ? (
            <div className="flex items-center justify-center gap-3 py-8">
              <div className="loading-spinner" />
              <span>Laddar kandidater...</span>
            </div>
          ) : candidateState.candidates.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <FiFileText className="text-3xl mx-auto mb-2" />
              <p>Inga matchningskandidater hittades för denna rad.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {candidateState.candidates.map((candidate) => (
                <div key={candidate.file_id} className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="font-medium text-gray-100">{candidate.vendor_name || 'Okänd leverantör'}</div>
                      <div className="text-sm text-gray-400 space-y-1">
                        <div>Datum: {formatDate(candidate.purchase_datetime, false)}</div>
                        <div>Belopp: {formatAmount(candidate.gross_amount)}</div>
                        {candidate.match_score != null && (
                          <div>Match-poäng: {Math.round(candidate.match_score * 100)}%</div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn btn-text btn-sm"
                        onClick={() => openReceiptPreview(candidate.file_id)}
                      >
                        <FiEye className="mr-1" />
                        Visa
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => assignCandidate(candidateState.line.id, candidate.file_id)}
                        disabled={assigningLineId === candidateState.line.id}
                      >
                        {assigningLineId === candidateState.line.id ? (
                          <>
                            <div className="loading-spinner mr-1" />
                            Matchar...
                          </>
                        ) : (
                          <>
                            <FiLink className="mr-1" />
                            Matcha
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={closeCandidates}>
            Stäng
          </button>
        </div>
      </div>
    </div>
  ) : null

  const renderLogModal = () => {
    if (!logState.open) {
      return null
    }

    const logData = logState.data ?? {}
    const workflowRuns = Array.isArray(logData?.workflow_runs) ? logData.workflow_runs : []
    const aiHistory = Array.isArray(logData?.ai_history) ? logData.ai_history : []
    const files = Array.isArray(logData?.files) ? logData.files : []
    const metadataPayload = logData?.metadata && typeof logData.metadata === 'object' ? logData.metadata : {}
    const invoiceIdForModal = logData?.invoice_id || logState.invoiceId

    const handleBackdrop = (event) => {
      if (event.target === event.currentTarget) {
        closeLogViewer()
      }
    }

    return (
      <div className="modal-backdrop" role="dialog" aria-label="Importlogg" onClick={handleBackdrop}>
        <div
          className="modal"
          onClick={(event) => event.stopPropagation()}
          style={{ maxWidth: '960px' }}
        >
          <div className="modal-header">
            <div>
              <h3>Importlogg</h3>
              <p className="text-xs text-gray-400 mt-1">
                Kontoutdrag: {invoiceIdForModal || 'okänd'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleClearInvoiceLog(invoiceIdForModal)}
                disabled={!invoiceIdForModal || logState.loading || logActionState.clearing}
              >
                {logActionState.clearing ? (
                  <>
                    <div className="loading-spinner w-4 h-4 mr-2" />
                    Rensar...
                  </>
                ) : (
                  <>
                    <FiTrash2 className="mr-1" />
                    Rensa logg
                  </>
                )}
              </button>
              <button type="button" className="icon-button" onClick={closeLogViewer} aria-label="Stäng logg">
                <FiX />
              </button>
            </div>
          </div>

          <div className="modal-body space-y-6 max-h-[70vh] overflow-y-auto">
            {logActionState.error && (
              <div className="alert alert-error">
                <FiAlertCircle className="mr-2" />
                <span>{`Kunde inte rensa logg: ${logActionState.error}`}</span>
              </div>
            )}
            {logActionState.success && (
              <div className="alert alert-success">
                <FiCheckCircle className="mr-2" />
                <span>{logActionState.success}</span>
              </div>
            )}
            {logState.loading ? (
              <div className="flex items-center justify-center gap-3 py-10 text-gray-200">
                <div className="loading-spinner" />
                <span>Hämtar logg...</span>
              </div>
            ) : logState.error ? (
              <div className="alert alert-error">
                <FiAlertCircle className="mr-2" />
                <span>{`Misslyckades att hämta logg: ${logState.error}`}</span>
              </div>
            ) : (
              <>
                <section>
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                      Workflowkörningar
                    </h4>
                    <span className="text-xs text-gray-500">
                      {workflowRuns.length ? `${workflowRuns.length} st` : 'Inga loggar'}
                    </span>
                  </div>
                  {workflowRuns.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-2">Inga workflow-loggar hittades för detta utdrag.</p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {workflowRuns.map((run) => (
                        <div key={run.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-gray-100">
                                {run.workflow_key}  –  {run.status}
                              </div>
                              <div className="text-xs text-gray-400">
                                Run-ID: {run.id}  –  Source: {run.source_channel || 'okänd'}
                              </div>
                            </div>
                            <div className="text-xs text-gray-400 text-right">
                              <div>Start: {formatDate(run.created_at)}</div>
                              <div>Senast: {formatDate(run.updated_at)}</div>
                            </div>
                          </div>
                          {Array.isArray(run.stages) && run.stages.length > 0 ? (
                            <div className="space-y-2">
                              {run.stages.map((stage, index) => (
                                <div
                                  key={`${run.id}-${stage.stage_key}-${stage.started_at || stage.finished_at || index}`}
                                  className="bg-gray-800/70 border border-gray-700/70 rounded-md px-3 py-2 space-y-1"
                                >
                                  <div className="flex flex-wrap items-center justify-between text-sm font-medium text-gray-100">
                                  <span>{formatStageLabel(stage.stage_key)}</span>
                                    <span>{stage.status}</span>
                                  </div>
                                  <div className="flex flex-wrap items-center justify-between text-xs text-gray-400">
                                    <span>
                                      {formatDate(stage.started_at)}{stage.finished_at ? ` → ${formatDate(stage.finished_at)}` : ''}
                                    </span>
                                    {stage.duration_ms != null && (
                                      <span>{formatDurationMs(stage.duration_ms)}</span>
                                    )}
                                  </div>
                                  {stage.message && (
                                    <pre className="mt-2 text-xs text-gray-300 whitespace-pre-wrap font-mono">
                                      {stage.message}
                                    </pre>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-gray-500">Inga steg registrerade.</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                      AI-historik
                    </h4>
                    <span className="text-xs text-gray-500">
                      {aiHistory.length ? `${aiHistory.length} poster` : 'Inga AI-loggar'}
                    </span>
                  </div>
                  {aiHistory.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-2">
                      Ingen AI-historik registrerad för detta utdrag eller dess sidor.
                    </p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {aiHistory.map((entry) => (
                        <div key={entry.id} className="bg-gray-900 border border-gray-700 rounded-lg p-3 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-gray-100">
                                {(entry.ai_stage_name || entry.job_type || 'Okänt steg')}  –  {entry.status}
                              </div>
                              <div className="text-xs text-gray-400">
                                Fil: {entry.file_id}  –  {formatDate(entry.created_at)}
                              </div>
                            </div>
                            <div className="text-xs text-gray-400 text-right space-y-1">
                              {(entry.provider || entry.model) && (
                                <div>
                                  {entry.provider || 'okänd'}{entry.model ? `  –  ${entry.model}` : ''}
                                </div>
                              )}
                              {entry.processing_time_ms != null && (
                                <div>Tid: {formatDurationMs(entry.processing_time_ms)}</div>
                              )}
                              {entry.confidence != null && (
                                <div>Konfidens: {Math.round(entry.confidence * 100)}%</div>
                              )}
                            </div>
                          </div>
                          {entry.log_text && (
                            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono bg-gray-800/70 border border-gray-700/70 rounded-md p-2">
                              {entry.log_text}
                            </pre>
                          )}
                          {entry.error_message && (
                            <div className="text-xs text-red-300 bg-red-900/30 border border-red-800/40 rounded-md p-2 whitespace-pre-wrap font-mono">
                              {entry.error_message}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                    Filer
                  </h4>
                  {files.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-2">
                      Inga relaterade filer hittades i unified_files.
                    </p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {files.map((file) => (
                        <div key={file.id} className="bg-gray-900 border border-gray-700 rounded-lg p-3 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-100">
                            <span className="font-semibold">{file.id}</span>
                            <span className="text-xs text-gray-400">
                              Skapad: {formatDate(file.created_at)}
                              {file.updated_at ? `  –  Uppdaterad: ${formatDate(file.updated_at)}` : ''}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-300">
                            <div>Filtyp: {file.file_type || '–'}</div>
                            <div>Workflow-typ: {file.workflow_type || '–'}</div>
                            <div>Status: {file.ai_status || '–'}</div>
                            <div>
                              Konfidens: {file.ai_confidence != null ? `${Math.round(file.ai_confidence * 100)}%` : '–'}
                            </div>
                            <div>OCR-tecken: {file.ocr_raw_length ?? 0}</div>
                          </div>
                          {file.ocr_raw_length > 0 && (
                            <details className="bg-gray-800/60 border border-gray-700/60 rounded-md p-2">
                              <summary className="text-xs text-gray-300 cursor-pointer">
                                Visa OCR-text ({file.ocr_raw_length} tecken)
                              </summary>
                              <pre className="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                                {file.ocr_raw}
                              </pre>
                            </details>
                          )}
                          {file.other_data && Object.keys(file.other_data).length > 0 && (
                            <details className="bg-gray-800/50 border border-gray-700/60 rounded-md p-2">
                              <summary className="text-xs text-gray-300 cursor-pointer">
                                Visa other_data
                              </summary>
                              <pre className="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">
                                {JSON.stringify(file.other_data, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                    Metadata (invoice_documents)
                  </h4>
                  {metadataPayload && Object.keys(metadataPayload).length > 0 ? (
                    <div className="mt-3 bg-gray-900 border border-gray-700 rounded-lg p-3">
                      <pre className="text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">
                        {JSON.stringify(metadataPayload, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 mt-2">
                      Ingen metadata sparad för detta utdrag.
                    </p>
                  )}
                </section>
              </>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-text" onClick={closeLogViewer}>
              Stäng
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => logState.invoiceId && fetchInvoiceLog(logState.invoiceId)}
              disabled={logState.loading || !logState.invoiceId}
            >
              {logState.loading ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Hämtar...
                </>
              ) : (
                <>
                  <FiRefreshCw className="mr-2" />
                  Ladda om
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    )
  }


const renderStatementTable = () => {
    if (!items.length) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-10 text-gray-300">
          <FiFileText className="text-3xl" />
          <div>Inga kontoutdrag hittades.</div>
        </div>
      )
    }

    const rows = sortedItems.map((statement) => {
      const statusDetails = describeFirstCardStatus(statement)
      const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
      const lineSummary = statement.line_counts ?? {}
      const isSelected = statement.id === selectedDocumentId
      const cardLabel = statement.card_name || `Utdrag ${statement.id}`
      const invoiceNumber = statement.invoice_summary?.invoice_number || statement.invoice_number || statement.id
      const periodRange = statement.period_start && statement.period_end
        ? `${formatDate(statement.period_start, false)} - ${formatDate(statement.period_end, false)}`
        : null
      const processingDetails = describeProcessingStatus(statement.processing_status || statement.status)
      const updatedAt = statement.updated_at || statement.uploaded_at
      const confidence = typeof statement.overall_confidence === 'number'
        ? `${Math.round(Number(statement.overall_confidence) * 100)}%`
        : '-'
      const invoiceDateLabel = statement.invoice_date ? formatDate(statement.invoice_date, false) : '-'
      const dueDateLabel = statement.due_date ? formatDate(statement.due_date, false) : '-'
      const amountToPayLabel = statement.amount_to_pay ? formatAmount(statement.amount_to_pay) : '-'

      return {
        statement,
        statusDetails,
        badgeClass,
        lineSummary,
        isSelected,
        cardLabel,
        invoiceNumber,
        periodRange,
        processingDetails,
        updatedAt,
        confidence,
        invoiceDateLabel,
        dueDateLabel,
        amountToPayLabel,
      }
    })

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="min-w-full divide-y divide-gray-700 text-sm">
          <thead className="bg-gray-900/60 text-gray-300 uppercase tracking-wide text-xs">
            <tr>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('card_name')}
              >
                Kort {sortColumn === 'card_name' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('invoice_date')}
              >
                Fakturadatum {sortColumn === 'invoice_date' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('due_date')}
              >
                Betalningsdatum {sortColumn === 'due_date' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('amount_to_pay')}
              >
                Belopp {sortColumn === 'amount_to_pay' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('status')}
              >
                Status {sortColumn === 'status' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('overall_confidence')}
              >
                AI - Konfidens {sortColumn === 'overall_confidence' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('total_lines')}
              >
                RADER {sortColumn === 'total_lines' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('matched_lines')}
              >
                Matchade rader {sortColumn === 'matched_lines' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('unmatched_lines')}
              >
                Omatchade rader {sortColumn === 'unmatched_lines' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('updated_at')}
              >
                Senast uppdaterad {sortColumn === 'updated_at' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th className="px-4 py-3 text-center">Logg</th>
              <th className="px-4 py-3 text-center">Matcha omatchade rader</th>
              <th className="px-4 py-3 text-center">Återuppta fakturaimport</th>
              <th className="px-3 py-3 text-right">Ta bort</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {rows.map(({ statement, statusDetails, badgeClass, lineSummary, isSelected, cardLabel, invoiceNumber, periodRange, updatedAt, confidence, invoiceDateLabel, dueDateLabel, amountToPayLabel }) => {
              const rowClasses = isSelected ? 'bg-red-600/10 hover:bg-red-600/20' : 'hover:bg-gray-800/40'
              const hasUnmatchedRows = (lineSummary.unmatched ?? 0) > 0

              return (
                <tr
                  key={statement.id}
                  onClick={() => setSelectedDocumentId(statement.id)}
                  className={`cursor-pointer transition-colors ${rowClasses}`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">
                    <div className="flex items-center gap-2">
                      <FiChevronRight className={`transition-transform ${isSelected ? 'rotate-90 text-red-400' : 'text-gray-500'}`} />
                      {cardLabel}
                    </div>
                    <div className="mt-1 text-xs text-gray-400">Fakturanummer: {invoiceNumber}</div>
                    {periodRange && <div className="text-xs text-gray-400">Period: {periodRange}</div>}
                    <div className="mt-1 text-xs text-gray-400">
                      Uppladdad {formatDate(statement.created_at || statement.uploaded_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-200 text-center">{invoiceDateLabel}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{dueDateLabel}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{amountToPayLabel}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`status-badge ${badgeClass}`}>{statusDetails.label}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-200 text-center">{confidence}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{lineSummary.total ?? '–'}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{lineSummary.matched ?? '–'}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{lineSummary.unmatched ?? '–'}</td>
                  <td className="px-4 py-3 text-gray-200 text-center whitespace-nowrap">
                    {formatDate(updatedAt)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={(event) => {
                        event.stopPropagation()
                        setSelectedDocumentId(statement.id)
                        fetchInvoiceLog(statement.id)
                      }}
                    >
                      Visa logg
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm ml-2"
                      onClick={(event) => {
                        event.stopPropagation()
                        setPreviewInvoiceId(statement.id)
                        setPreviewOpen(true)
                      }}
                    >
                      Preview
                    </button>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {hasUnmatchedRows && (
                      <button
                        type="button"
                        className="btn btn-sm"
                        style={{
                          backgroundColor: '#dc2626',
                          color: 'white',
                          border: 'none',
                        }}
                        onClick={(event) => {
                          event.stopPropagation()
                          onMatchDocument(statement.id)
                        }}
                        disabled={matchingDocumentId === statement.id}
                      >
                        {matchingDocumentId === statement.id ? (
                          <>
                            <div className="loading-spinner mr-1" />
                            Matchar...
                          </>
                        ) : (
                          <>
                            <FiLink className="mr-1" />
                            Matcha omatchade rader
                          </>
                        )}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={(event) => {
                        event.stopPropagation()
                        handleResumeOrRestartInvoice(statement.id, statement.processing_status)
                      }}
                      disabled={resumingDocumentId === statement.id}
                    >
                      {resumingDocumentId === statement.id ? (
                        <>
                          <div className="loading-spinner mr-1" />
                          Bearbetar...
                        </>
                      ) : (
                        <>
                          <FiRefreshCw className="mr-1" />
                          Återuppta fakturaimport
                        </>
                      )}
                    </button>
                  </td>
                  <td className="px-3 py-3 text-right">
                    <button
                      type="button"
                      className={`icon-button ${deletingDocumentId === statement.id ? 'opacity-60 cursor-wait' : 'text-gray-500 hover:text-red-400'}`}
                      onClick={(event) => {
                        event.stopPropagation()
                        handleDeleteStatement(statement.id)
                      }}
                      disabled={deletingDocumentId === statement.id}
                      aria-label="Ta bort utdrag"
                    >
                      {deletingDocumentId === statement.id ? <div className="loading-spinner w-4 h-4" /> : <FiTrash2 />}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="stat-card blue">
          <div className="flex items-center justify-between mb-2">
            <FiCheckCircle className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{formatNumber(totalInvoices)}</div>
              </div>
            )}
          </div>
          <div className="stat-label">Inlästa utdrag</div>
          <div className="stat-subtitle">Totalt antal importerade fakturor</div>
        </div>

        <div className="stat-card green">
          <div className="flex items-center justify-between mb-2">
            <FiFileText className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{formatNumber(totalItems)}</div>
              </div>
            )}
          </div>
          <div className="stat-label">Totalt fakturaposter</div>
          <div className="stat-subtitle">Antal rader (items) i alla utdrag</div>
        </div>

        <div className="stat-card blue">
          <div className="flex items-center justify-between mb-2">
            <FiLink className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{formatNumber(matchedItems)}</div>
              </div>
            )}
          </div>
          <div className="stat-label">Matchade kvitton</div>
          <div className="stat-subtitle">Antal rader som fått kvitto-match</div>
        </div>

        <div className="stat-card yellow">
          <div className="flex items-center justify-between mb-2">
            <FiPercent className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{`${matchedItemsPercent}%`}</div>
                <div className="text-xs text-gray-400">av {formatNumber(totalItems)} rader</div>
              </div>
            )}
          </div>
          <div className="stat-label">Matchningsgrad</div>
          <div className="stat-subtitle">Andel item-rader som är matchade</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="card-title">Kontoutdrag</h3>
            <p className="card-subtitle">Överblick över importerade kontoutdrag.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => loadStatements(selectedDocumentIdRef.current)}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Uppdaterar...
                </>
              ) : (
                <>
                  <FiRefreshCw className="mr-2" />
                  Uppdatera
                </>
              )}
            </button>
            <button
              type="button"
              className="btn btn-sm"
              style={{
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
              }}
              onClick={handleMatchAllUnmatched}
              disabled={matchingAllUnmatched || loading}
            >
              {matchingAllUnmatched ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Matchar...
                </>
              ) : (
                <>
                  <FiLink className="mr-2" />
                  Matcha omatchade poster
                </>
              )}
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setUploadModalOpen(true)}
            >
              <FiUpload className="mr-2" />
              Ladda upp utdrag
            </button>
          </div>
        </div>
        <div className="px-6 pb-6 space-y-4">
          {renderFeedback()}
          {loading ? (
            <div className="flex items-center justify-center gap-3 py-10 text-gray-400">
              <div className="loading-spinner" />
              <span>Laddar kontoutdrag...</span>
            </div>
          ) : (
            renderStatementTable()
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header flex-wrap gap-3">
          <div>
            <h3 className="card-title">Utdragsdetaljer</h3>
            {selectedDocument ? (
              <p className="card-subtitle">
                {selectedDocument.period_start && selectedDocument.period_end
                  ? `Period: ${formatDate(selectedDocument.period_start, false)} – ${formatDate(selectedDocument.period_end, false)}`
                  : 'Välj ett kontoutdrag för att se detaljer.'}
              </p>
            ) : (
              <p className="card-subtitle">Välj ett kontoutdrag för att se detaljer.</p>
            )}
          </div>
        </div>
        <div className="px-6 pb-6 space-y-6">
          {selectedDocument && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Status</div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`status-badge ${toneClass[describeFirstCardStatus(selectedDocument).tone] || 'status-processing'}`}>
                      {describeFirstCardStatus(selectedDocument).label}
                    </span>
                  </div>
                </div>
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Linjer</div>
                  <div className="mt-2 text-gray-100 text-lg font-semibold">{lineCounts.total}</div>
                  <div className="text-xs text-gray-400 mt-1">Matchade: {lineCounts.matched}  –  Obearbetade: {lineCounts.unmatched}</div>
                </div>
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Senast uppdaterad</div>
                  <div className="mt-2 text-gray-100 text-lg font-semibold">
                    {formatDate(selectedDocument.updated_at || selectedDocument.uploaded_at)}
                  </div>
                </div>
              </div>
              {detailSummaryCards.length > 0 && (
                <dl className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {detailSummaryCards.map((item) => (
                    <div key={item.label} className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3">
                      <dt className="text-xs uppercase tracking-wide text-gray-400">{item.label}</dt>
                      <dd className="text-sm font-semibold text-white mt-1 break-words">{item.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </>
          )}

          {renderItemTable()}
          {renderLineTable()}
        </div>
      </div>

      {candidatesContent}
      {renderLogModal()}

      <DocumentPreviewModal
        open={previewOpen}
        documentId={previewInvoiceId}
        onClose={() => setPreviewOpen(false)}
      />

      <InvoiceUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploaded={handleUploadComplete}
      />

      <ReceiptPreviewModal
        open={Boolean(previewReceipt)}
        receipt={previewReceipt}
        previewImage={previewImage}
        onClose={closeReceiptPreview}
        onReceiptUpdate={handleReceiptUpdate}
      />
    </div>
  )
}


function InvoiceUploadModal({ open, onClose, onUploaded }) {
  const fileInputRef = React.useRef(null)
  const [selectedFiles, setSelectedFiles] = React.useState([])
  const [uploading, setUploading] = React.useState(false)
  const [feedback, setFeedback] = React.useState(null)

  React.useEffect(() => {
    if (!open) {
      setSelectedFiles([])
      setFeedback(null)
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleBackdropClick = (event) => {
    if (event.target === event.currentTarget && !uploading && typeof onClose === 'function') {
      onClose()
    }
  }

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files ?? [])
    setSelectedFiles(files)
    setFeedback(null)
  }

  const handleUpload = async () => {
    if (!selectedFiles.length || uploading) {
      return
    }

    setUploading(true)
    setFeedback(null)

    const successes = []
    const failures = []

    for (const file of selectedFiles) {
      const formData = new FormData()
      formData.append('invoice', file)
      try {
        const response = await api.fetch('/ai/api/reconciliation/firstcard/upload-invoice', {
          method: 'POST',
          body: formData,
        })

        if (response.status === 201) {
          const data = await response.json().catch(() => null)
          successes.push({ file, invoiceId: data?.invoice_id ?? null })
        } else {
          const payload = await response.json().catch(() => null)
          failures.push({
            file,
            message: buildUploadErrorMessage(response.status, payload),
          })
        }
      } catch (error) {
        const message = error instanceof Error ? `Nätverksfel: ${error.message}` : 'Nätverksfel.'
        failures.push({ file, message })
      }
    }

    if (successes.length && typeof onUploaded === 'function') {
      const lastInvoiceId = successes[successes.length - 1]?.invoiceId ?? null
      const successSummary = `Uppladdning klar: ${successes.length} fil${successes.length === 1 ? '' : 'er'} skickades för bearbetning.`
      await onUploaded({
        lastInvoiceId,
        successMessage: failures.length ? null : successSummary,
      })
      if (!failures.length) {
        setFeedback({ type: 'success', text: successSummary })
      }
    }

    if (failures.length) {
      const detail = failures
        .map(({ file, message }) => `${file.name} (${message})`)
        .join('; ')
      const prefix = successes.length
        ? `Vissa filer laddades upp, men ${failures.length} misslyckades`
        : `Kunde inte ladda upp ${failures.length} fil${failures.length === 1 ? '' : 'er'}`
      setFeedback({
        type: 'error',
        text: `${prefix}: ${detail}.`,
      })
      setSelectedFiles(failures.map(({ file }) => file))
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } else if (successes.length) {
      setSelectedFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      setTimeout(() => {
        setFeedback(null)
        if (typeof onClose === 'function') {
          onClose()
        }
      }, 1200)
    }

    setUploading(false)
  }

  const selectedSummary = selectedFiles.length
    ? `${selectedFiles.length} fil${selectedFiles.length === 1 ? ' vald' : 'er valda'}`
    : null

  const feedbackTone = feedback?.type === 'success'
    ? 'alert-success'
    : feedback?.type === 'error'
      ? 'alert-error'
      : 'alert-info'

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-label="Ladda upp kontoutdrag"
      onClick={handleBackdropClick}
    >
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Ladda upp kontoutdrag</h3>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Stäng"
            disabled={uploading}
          >
            <FiX />
          </button>
        </div>

        <div className="modal-body space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Välj filer att ladda upp</label>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf"
              className="dm-input w-full"
              disabled={uploading}
              onChange={handleFileSelect}
            />
            {selectedFiles.length > 0 && (
              <ul className="mt-2 text-sm text-gray-300 space-y-1 list-disc list-inside">
                {selectedFiles.map((file) => (
                  <li key={`${file.name}-${file.size}`}>{file.name}</li>
                ))}
              </ul>
            )}
            {selectedSummary && (
              <div className="mt-2 text-xs text-gray-400">{selectedSummary}</div>
            )}
            <p className="mt-2 text-xs text-gray-500">
              Filerna skickas till OCR och matchning direkt efter uppladdning.
            </p>
          </div>

          {feedback && (
            <div className={`alert ${feedbackTone}`}>
              {feedback.type === 'success' ? (
                <FiCheckCircle className="mr-2" />
              ) : (
                <FiAlertCircle className="mr-2" />
              )}
              <span>{feedback.text}</span>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-text" onClick={onClose} disabled={uploading}>
            Avbryt
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading || selectedFiles.length === 0}
          >
            {uploading ? (
              <>
                <div className="loading-spinner mr-2" />
                Laddar upp...
              </>
            ) : (
              <>
                <FiUpload className="mr-2" />
                Ladda upp
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}






```

