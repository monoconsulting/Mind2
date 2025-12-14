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


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float between bounds."""
    return max(lo, min(hi, value))


def _median(values: List[float]) -> float | None:
    """Compute the median of a list of floats (returns None if empty)."""
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _get_resample_method() -> Any:
    """Return a high-quality PIL resampling method (LANCZOS where available)."""
    if Image is None:
        return None
    resampling = getattr(Image, "Resampling", None)
    return getattr(resampling, "LANCZOS", getattr(Image, "LANCZOS", getattr(Image, "BICUBIC", None)))


def _prepare_image_for_ocr(
    img_path: Path,
    *,
    output_dir: Path,
    target_long_side: int,
    max_long_side: int,
    zoom_factor: float = 1.0,
) -> tuple[Path, int, int]:
    """Prepare a receipt image for OCR with quality-first scaling.

    The goal is to make text readable for OCR by upscaling smaller inputs (within limits),
    while also preventing runaway memory usage by capping the maximum long side.

    Args:
        img_path: Original image path.
        output_dir: Directory where prepared images are written.
        target_long_side: Desired long-side resolution for OCR.
        max_long_side: Upper cap for long-side resolution.
        zoom_factor: Additional scale multiplier (used for zoom fallback pass).

    Returns:
        Tuple of (prepared_image_path, width_px, height_px).
    """
    if Image is None:  # pragma: no cover
        return img_path, 0, 0

    from PIL import ImageOps  # type: ignore

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_zoom = _clamp(float(zoom_factor or 1.0), 1.0, 6.0)
    resample_method = _get_resample_method()

    with Image.open(img_path) as im:  # type: ignore[attr-defined]
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass

        if im.mode not in {"RGB", "RGBA"}:
            im = im.convert("RGB")
        elif im.mode == "RGBA":
            background = Image.new("RGB", im.size, (255, 255, 255))
            background.paste(im, mask=im.split()[3])
            im = background

        width, height = im.size
        long_side = max(width, height) if width and height else 0

        desired = int(max(1, target_long_side))
        cap = int(max(1, max_long_side))
        if cap < desired:
            cap = desired

        # Baseline scaling to reach at least desired long-side (but never exceed cap).
        scale = 1.0
        if long_side > 0:
            if long_side < desired:
                scale = desired / float(long_side)
            elif long_side > cap:
                scale = cap / float(long_side)

        # Apply optional zoom factor (still capped by max long-side).
        scale *= safe_zoom
        if long_side > 0 and long_side * scale > cap:
            scale = cap / float(long_side)

        if long_side > 0 and abs(scale - 1.0) > 1e-6:
            new_w = max(1, int(round(width * scale)))
            new_h = max(1, int(round(height * scale)))
            if resample_method is not None:
                im = im.resize((new_w, new_h), resample=resample_method)
            else:  # pragma: no cover
                im = im.resize((new_w, new_h))

        prepared_name = f"{img_path.stem}__ocr_{int(round(safe_zoom * 100)):03d}.png"
        prepared_path = (output_dir / prepared_name).resolve()
        im.save(prepared_path, format="PNG", optimize=False)
        return prepared_path, im.size[0], im.size[1]


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
    import logging
    logger = logging.getLogger(__name__)

    global _OCR_ENGINE
    if _OCR_ENGINE is None and PaddleOCR is not None:
        lang = os.getenv("OCR_LANG", "sv+en")
        use_angle_cls = _env_bool("OCR_USE_ANGLE_CLS", True)
        show_log = _env_bool("OCR_SHOW_LOG", False)

        det_limit_side_len = _env_int("OCR_DET_LIMIT_SIDE_LEN", 4096)
        det_limit_type = (os.getenv("OCR_DET_LIMIT_TYPE", "max") or "max").strip()

        init_kwargs: dict[str, Any] = {
            "lang": lang,
            "use_angle_cls": use_angle_cls,
        }
        # Newer PaddleOCR versions may accept these detector resize controls.
        init_kwargs["det_limit_side_len"] = det_limit_side_len
        init_kwargs["det_limit_type"] = det_limit_type

        # Older versions used show_log; newer versions ignore/remove it. Try safely.
        if show_log:
            init_kwargs["show_log"] = True

        try:
            logger.info(
                "Initializing PaddleOCR lang=%s use_angle_cls=%s det_limit_side_len=%s det_limit_type=%s",
                lang,
                use_angle_cls,
                det_limit_side_len,
                det_limit_type,
            )
            _OCR_ENGINE = PaddleOCR(**init_kwargs)
        except TypeError as exc:
            logger.warning(
                "PaddleOCR init failed with full kwargs (%s); retrying with reduced kwargs",
                exc,
            )
            reduced_kwargs = {"lang": lang, "use_angle_cls": use_angle_cls}
            try:
                _OCR_ENGINE = PaddleOCR(**reduced_kwargs)
            except TypeError as exc2:
                logger.warning(
                    "PaddleOCR init failed with reduced kwargs (%s); retrying without angle classifier",
                    exc2,
                )
                _OCR_ENGINE = PaddleOCR(lang=lang)
        except Exception:
            logger.exception("Failed to initialize PaddleOCR")
            _OCR_ENGINE = None
        else:
            logger.info("PaddleOCR initialized successfully")
    return _OCR_ENGINE


def _extract_text_from_images(images: List[Path]) -> Dict[str, Any]:
    import logging
    logger = logging.getLogger(__name__)

    full_text: List[str] = []
    boxes: List[Dict[str, Any]] = []

    engine = _get_ocr_engine()
    if not images or Image is None:
        logger.warning(f"OCR: No images or PIL not available. Images: {len(images) if images else 0}")
        return {"text": "", "boxes": []}

    if engine is None:
        logger.error("OCR: PaddleOCR engine not available - cannot process images")
        return {"text": "", "boxes": []}

    # Quality-first OCR settings (defaults chosen to be conservative but effective).
    input_long_side = _env_int("OCR_INPUT_LONG_SIDE", 4500)
    input_max_long_side = _env_int("OCR_INPUT_MAX_LONG_SIDE", 6500)
    zoom_enabled = _env_bool("OCR_ZOOM_ENABLED", True)
    zoom_factor = _env_float("OCR_ZOOM_FACTOR", 2.0)
    min_box_height_px = _env_int("OCR_MIN_BOX_HEIGHT_PX", 12)
    fallback_min_chars = _env_int("OCR_FALLBACK_MIN_CHARS", 80)
    fallback_min_boxes = _env_int("OCR_FALLBACK_MIN_BOXES", 15)

    tile_enable = _env_bool("OCR_TILE_ENABLE", True)
    tile_grid = max(1, _env_int("OCR_TILE_GRID", 2))
    tile_overlap = _clamp(_env_float("OCR_TILE_OVERLAP", 0.15), 0.0, 0.5)

    logger.info(f"OCR: Processing {len(images)} images")
    for img_path in images:
        logger.info(f"OCR: Processing image {img_path}")
        prepared_dir = (img_path.parent / "_ocr_prepared").resolve()

        def append_detection(
            text_value: Any,
            polygon: Any,
            confidence: Any,
            *,
            base_width: int,
            base_height: int,
            offset_x: float = 0.0,
            offset_y: float = 0.0,
            text_out: List[str],
            boxes_out: List[Dict[str, Any]],
        ) -> None:
            if text_value is None or polygon is None:
                return
            try:
                text_str = str(text_value).strip()
            except Exception:
                text_str = str(text_value)
            if not text_str:
                return
            points = []
            for pt in polygon:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    try:
                        px = float(pt[0]) + float(offset_x)
                        py = float(pt[1]) + float(offset_y)
                    except (TypeError, ValueError):
                        continue
                    points.append((px, py))
            if len(points) < 2 or not base_width or not base_height:
                return
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            if max_x <= min_x or max_y <= min_y:
                return

            x_norm = min_x / base_width
            y_norm = min_y / base_height
            w_norm = (max_x - min_x) / base_width
            h_norm = (max_y - min_y) / base_height

            if base_width > base_height:
                rotated_x = y_norm
                rotated_y = 1.0 - x_norm - w_norm
                rotated_w = h_norm
                rotated_h = w_norm
                x_norm, y_norm, w_norm, h_norm = rotated_x, rotated_y, rotated_w, rotated_h

            x_norm = max(min(x_norm, 1.0), 0.0)
            y_norm = max(min(y_norm, 1.0), 0.0)
            w_norm = max(min(w_norm, 1.0), 0.0)
            h_norm = max(min(h_norm, 1.0), 0.0)

            text_out.append(text_str)
            boxes_out.append(
                {
                    "field": text_str,
                    "confidence": float(confidence) if confidence is not None else None,
                    "x": x_norm,
                    "y": y_norm,
                    "w": w_norm,
                    "h": h_norm,
                }
            )

        def run_engine(
            ocr_img_path: Path,
            *,
            base_width: int,
            base_height: int,
            offset_x: float = 0.0,
            offset_y: float = 0.0,
        ) -> tuple[List[str], List[Dict[str, Any]]]:
            """Run PaddleOCR on a single image path and normalize results."""
            local_text: List[str] = []
            local_boxes: List[Dict[str, Any]] = []
            try:
                ocr_result = engine.ocr(str(ocr_img_path)) or []
            except Exception as e:
                logger.error("OCR: Failed to run OCR on %s: %s", ocr_img_path, e)
                return local_text, local_boxes

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
                                append_detection(
                                    text_value,
                                    polygon,
                                    confidence,
                                    base_width=base_width,
                                    base_height=base_height,
                                    offset_x=offset_x,
                                    offset_y=offset_y,
                                    text_out=local_text,
                                    boxes_out=local_boxes,
                                )
                            handled = True
                if not handled and isinstance(ocr_result_item, dict):
                    res = ocr_result_item.get("res")
                    if isinstance(res, dict):
                        rec_texts = res.get("rec_texts", [])
                        rec_polys = res.get("rec_polys", [])
                        rec_scores = res.get("rec_scores", [])
                        for i, text_value in enumerate(rec_texts):
                            if i >= len(rec_polys):
                                continue
                            polygon = rec_polys[i]
                            confidence = rec_scores[i] if i < len(rec_scores) else None
                            append_detection(
                                text_value,
                                polygon,
                                confidence,
                                base_width=base_width,
                                base_height=base_height,
                                offset_x=offset_x,
                                offset_y=offset_y,
                                text_out=local_text,
                                boxes_out=local_boxes,
                            )
                        handled = True
                if handled:
                    continue

                sequence: list[Any] = []
                if isinstance(ocr_result_item, (list, tuple)):
                    sequence = list(ocr_result_item)
                elif isinstance(ocr_result_item, dict):
                    maybe_sequence = ocr_result_item.get("data") or ocr_result_item.get("result")
                    if isinstance(maybe_sequence, (list, tuple)):
                        sequence = list(maybe_sequence)

                for entry in sequence:
                    polygon = None
                    text_value = None
                    confidence = None

                    if isinstance(entry, dict):
                        polygon = entry.get("box") or entry.get("points") or entry.get("poly")
                        text_value = entry.get("text") or entry.get("value") or entry.get("field")
                        confidence = entry.get("score") or entry.get("confidence")
                    elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        polygon = entry[0]
                        info = entry[1]
                        if isinstance(info, (list, tuple)):
                            if info:
                                text_value = info[0]
                            if len(info) > 1:
                                confidence = info[1]
                        elif isinstance(info, dict):
                            text_value = info.get("text") or info.get("value") or info.get("field")
                            confidence = info.get("score") or info.get("confidence")
                        else:
                            text_value = info

                    append_detection(
                        text_value,
                        polygon,
                        confidence,
                        base_width=base_width,
                        base_height=base_height,
                        offset_x=offset_x,
                        offset_y=offset_y,
                        text_out=local_text,
                        boxes_out=local_boxes,
                    )

            return local_text, local_boxes

        # Pass 1: normalized to target long-side.
        try:
            prepared_path, prep_w, prep_h = _prepare_image_for_ocr(
                img_path,
                output_dir=prepared_dir,
                target_long_side=input_long_side,
                max_long_side=input_max_long_side,
                zoom_factor=1.0,
            )
        except Exception as e:
            logger.error("OCR: Failed to prepare image %s: %s", img_path, e)
            continue

        texts_1, boxes_1 = run_engine(prepared_path, base_width=prep_w, base_height=prep_h)
        char_count_1 = sum(len(t) for t in texts_1)
        heights_1 = [(b.get("h") or 0.0) * float(prep_h) for b in boxes_1 if b.get("h") is not None]
        median_h_1 = _median([float(v) for v in heights_1]) or 0.0

        use_texts, use_boxes, used_zoom = texts_1, boxes_1, False

        should_zoom = (
            zoom_enabled
            and (median_h_1 > 0 and median_h_1 < float(min_box_height_px))
            or (char_count_1 < fallback_min_chars)
            or (len(boxes_1) < fallback_min_boxes)
        )
        if zoom_enabled and should_zoom:
            try:
                zoomed_path, zoom_w, zoom_h = _prepare_image_for_ocr(
                    img_path,
                    output_dir=prepared_dir,
                    target_long_side=input_long_side,
                    max_long_side=input_max_long_side,
                    zoom_factor=zoom_factor,
                )
                texts_2, boxes_2 = run_engine(zoomed_path, base_width=zoom_w, base_height=zoom_h)
                char_count_2 = sum(len(t) for t in texts_2)
                if char_count_2 > char_count_1 or len(boxes_2) > len(boxes_1):
                    use_texts, use_boxes, used_zoom = texts_2, boxes_2, True
                    prepared_path, prep_w, prep_h = zoomed_path, zoom_w, zoom_h
            except Exception as e:
                logger.warning("OCR: zoom fallback preparation failed for %s: %s", img_path, e)

        # Pass 3: Tile fallback for dense receipts (last resort).
        if tile_enable:
            char_count = sum(len(t) for t in use_texts)
            if char_count < fallback_min_chars or len(use_boxes) < fallback_min_boxes:
                try:
                    from PIL import Image as PILImage  # type: ignore

                    tile_texts: List[str] = []
                    tile_boxes: List[Dict[str, Any]] = []
                    with PILImage.open(prepared_path) as im:  # type: ignore[attr-defined]
                        base_w, base_h = im.size
                        if base_w and base_h:
                            step_x = base_w / float(tile_grid)
                            step_y = base_h / float(tile_grid)
                            overlap_x = step_x * tile_overlap
                            overlap_y = step_y * tile_overlap
                            tiles_dir = (prepared_dir / f"{img_path.stem}__tiles").resolve()
                            tiles_dir.mkdir(parents=True, exist_ok=True)
                            for row in range(tile_grid):
                                for col in range(tile_grid):
                                    left = int(max(0, round(col * step_x - overlap_x)))
                                    upper = int(max(0, round(row * step_y - overlap_y)))
                                    right = int(min(base_w, round((col + 1) * step_x + overlap_x)))
                                    lower = int(min(base_h, round((row + 1) * step_y + overlap_y)))
                                    if right <= left or lower <= upper:
                                        continue
                                    tile = im.crop((left, upper, right, lower))
                                    tile_path = (tiles_dir / f"tile_{row}_{col}.png").resolve()
                                    tile.save(tile_path, format="PNG", optimize=False)
                                    t_texts, t_boxes = run_engine(
                                        tile_path,
                                        base_width=base_w,
                                        base_height=base_h,
                                        offset_x=float(left),
                                        offset_y=float(upper),
                                    )
                                    tile_texts.extend(t_texts)
                                    tile_boxes.extend(t_boxes)
                    if sum(len(t) for t in tile_texts) > sum(len(t) for t in use_texts):
                        use_texts, use_boxes = tile_texts, tile_boxes
                except Exception as e:
                    logger.warning("OCR: tile fallback failed for %s: %s", img_path, e)

        full_text.extend(use_texts)
        boxes.extend(use_boxes)

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
