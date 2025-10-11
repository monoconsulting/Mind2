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


def _receipt_dir(base: str | Path, receipt_id: str) -> Path:
    return Path(base).resolve() / receipt_id


def _write_boxes(base: str | Path, receipt_id: str, boxes: List[Dict[str, Any]]) -> None:
    root = _receipt_dir(base, receipt_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=2), encoding="utf-8")


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
        use_angle_cls = os.getenv("OCR_USE_ANGLE_CLS", "true").lower() in ("true", "1", "t")
        show_log = os.getenv("OCR_SHOW_LOG", "false").lower() in ("true", "1", "t")
        try:
            logger.info("Initializing PaddleOCR with lang=%s, use_angle_cls=%s", lang, use_angle_cls)
            # Note: show_log parameter has been removed in newer versions of PaddleOCR
            _OCR_ENGINE = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang)
        except TypeError as exc:
            logger.warning("PaddleOCR init failed with use_angle_cls parameter: %s; retrying without angle classifier", exc)
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

    logger.info(f"OCR: Processing {len(images)} images")
    for img_path in images:
        logger.info(f"OCR: Processing image {img_path}")
        try:
            with Image.open(img_path) as image:
                width, height = image.size
                logger.info(f"OCR: Image size {width}x{height}")
        except Exception as e:
            logger.error(f"OCR: Failed to open image {img_path}: {e}")
            continue

        try:
            logger.info(f"OCR: About to call engine.ocr() on {img_path}")
            ocr_result = engine.ocr(str(img_path)) or []
            logger.info(f"OCR: Got {len(ocr_result)} results from engine")
        except Exception as e:
            logger.error(f"OCR: Failed to run OCR on {img_path}: {e}")
            import traceback
            logger.error(f"OCR: Full traceback: {traceback.format_exc()}")
            continue



        def append_detection(text_value, polygon, confidence):
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
                        px = float(pt[0])
                        py = float(pt[1])
                    except (TypeError, ValueError):
                        continue
                    points.append((px, py))
            if len(points) < 2 or not width or not height:
                return
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            if max_x <= min_x or max_y <= min_y:
                return

            x_norm = min_x / width
            y_norm = min_y / height
            w_norm = (max_x - min_x) / width
            h_norm = (max_y - min_y) / height

            if width > height:
                rotated_x = y_norm
                rotated_y = 1.0 - x_norm - w_norm
                rotated_w = h_norm
                rotated_h = w_norm
                x_norm, y_norm, w_norm, h_norm = rotated_x, rotated_y, rotated_w, rotated_h

            x_norm = max(min(x_norm, 1.0), 0.0)
            y_norm = max(min(y_norm, 1.0), 0.0)
            w_norm = max(min(w_norm, 1.0), 0.0)
            h_norm = max(min(h_norm, 1.0), 0.0)

            full_text.append(text_str)
            boxes.append(
                {
                    "field": text_str,
                    "confidence": float(confidence) if confidence is not None else None,
                    "x": x_norm,
                    "y": y_norm,
                    "w": w_norm,
                    "h": h_norm,
                }
            )

        for ocr_result_item in ocr_result:
            handled = False
            if hasattr(ocr_result_item, 'json'):
                result_data = getattr(ocr_result_item, 'json', None)
                if result_data and isinstance(result_data, dict):
                    res = result_data.get('res')
                    if isinstance(res, dict):
                        rec_texts = res.get('rec_texts', [])
                        rec_polys = res.get('rec_polys', [])
                        rec_scores = res.get('rec_scores', [])
                        for i, text_value in enumerate(rec_texts):
                            if i >= len(rec_polys):
                                continue
                            polygon = rec_polys[i]
                            confidence = rec_scores[i] if i < len(rec_scores) else None
                            append_detection(text_value, polygon, confidence)
                        handled = True
            if not handled and isinstance(ocr_result_item, dict):
                res = ocr_result_item.get('res')
                if isinstance(res, dict):
                    rec_texts = res.get('rec_texts', [])
                    rec_polys = res.get('rec_polys', [])
                    rec_scores = res.get('rec_scores', [])
                    for i, text_value in enumerate(rec_texts):
                        if i >= len(rec_polys):
                            continue
                        polygon = rec_polys[i]
                        confidence = rec_scores[i] if i < len(rec_scores) else None
                        append_detection(text_value, polygon, confidence)
                    handled = True
            if handled:
                continue

            sequence = []
            if isinstance(ocr_result_item, (list, tuple)):
                sequence = list(ocr_result_item)
            elif isinstance(ocr_result_item, dict):
                maybe_sequence = ocr_result_item.get('data') or ocr_result_item.get('result')
                if isinstance(maybe_sequence, (list, tuple)):
                    sequence = list(maybe_sequence)

            for entry in sequence:
                polygon = None
                text_value = None
                confidence = None

                if isinstance(entry, dict):
                    polygon = entry.get('box') or entry.get('points') or entry.get('poly')
                    text_value = entry.get('text') or entry.get('value') or entry.get('field')
                    confidence = entry.get('score') or entry.get('confidence')
                elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    polygon = entry[0]
                    info = entry[1]
                    if isinstance(info, (list, tuple)):
                        if info:
                            text_value = info[0]
                        if len(info) > 1:
                            confidence = info[1]
                    elif isinstance(info, dict):
                        text_value = info.get('text') or info.get('value') or info.get('field')
                        confidence = info.get('score') or info.get('confidence')
                    else:
                        text_value = info
                append_detection(text_value, polygon, confidence)

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
