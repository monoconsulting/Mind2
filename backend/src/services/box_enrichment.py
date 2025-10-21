from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from services.db.connection import db_cursor
except Exception:
    db_cursor = None  # type: ignore

logger = logging.getLogger(__name__)

CANONICAL_FIELDS: Set[str] = {
    "company.name",
    "company.orgnr",
    "company.address",
    "company.zip",
    "company.city",
    "company.country",
    "company.phone",
    "company.www",
    "company.email",
    "receipt.gross_amount",
    "receipt.net_amount",
    "receipt.currency",
    "receipt.purchase_datetime",
    "receipt.payment_type",
    "receipt.expense_type",
    "receipt.receipt_number",
    "receipt.total_vat_25",
    "receipt.total_vat_12",
    "receipt.total_vat_6",
}


def _receipt_dir(base: str | Path | None, receipt_id: str) -> Path:
    root = Path(base or os.getenv("STORAGE_DIR", "/data/storage")).resolve()
    return root / receipt_id


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace(",", ".")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_numeric_tokens(*values: str) -> Set[str]:
    tokens: Set[str] = set()
    for text in values:
        if not text:
            continue
        for match in re.findall(r"\d+(?:[.,]\d+)?", text):
            candidate = match.replace(",", ".")
            digits_only = re.sub(r"\D", "", candidate)
            if len(digits_only) >= 3:
                tokens.add(candidate)
        sanitized = re.sub(r"[^\d]", "", text)
        if len(sanitized) >= 3:
            tokens.add(sanitized)
    return {token for token in tokens if token}


def _extract_word_tokens(text: str) -> Set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if token and len(token) >= 3
    }


def _decimal_variants(value: Any) -> List[str]:
    variants: Set[str] = set()
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return []

    for fmt in ("f", ".2f"):
        try:
            rendered = format(dec, fmt)
        except Exception:
            continue
        if rendered:
            variants.add(rendered)
            variants.add(rendered.replace(".", ","))
    plain = str(dec)
    if plain:
        variants.add(plain)
        variants.add(plain.replace(".", ","))
    return [variant for variant in variants if variant]


def _datetime_variants(value: Any) -> List[str]:
    variants: Set[str] = set()
    dt: Optional[datetime] = None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if text:
            variants.add(text)
            if "T" in text:
                variants.add(text.replace("T", " "))
            if len(text) >= 10:
                variants.add(text[:10])
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                dt = None
    if dt:
        variants.add(dt.isoformat())
        variants.add(dt.strftime("%Y-%m-%d %H:%M"))
        variants.add(dt.strftime("%Y-%m-%d"))
    return [variant for variant in variants if variant]


def _string_variants(field: str, value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        variants: List[str] = []
        for item in value:
            variants.extend(_string_variants(field, item))
        return variants
    if isinstance(value, (int, float, Decimal)):
        return _decimal_variants(value)
    if isinstance(value, datetime):
        return _datetime_variants(value)
    text = str(value).strip()
    if not text:
        return []
    variants: Set[str] = {text}
    if field in {"company.orgnr", "company.phone", "company.zip"}:
        sanitized = re.sub(r"\s+", "", text)
        if sanitized:
            variants.add(sanitized)
        digits_only = re.sub(r"[^\d]", "", text)
        if digits_only:
            variants.add(digits_only)
    if field == "company.address":
        variants.add(text.replace("\n", " "))
    if field.startswith("receipt.") and field.endswith("_datetime"):
        variants.update(_datetime_variants(text))
    return [variant for variant in variants if variant]


def _build_candidate(field: str, variant: str) -> Dict[str, Any]:
    normalized = _normalize_text(variant)
    if not normalized:
        return {}
    numeric_tokens = _extract_numeric_tokens(variant, normalized)
    word_tokens = _extract_word_tokens(normalized)
    return {
        "field": field,
        "raw": variant,
        "normalized": normalized,
        "numeric_tokens": numeric_tokens,
        "word_tokens": word_tokens,
    }


def _load_receipt(rid: str) -> Dict[str, Any]:
    if not db_cursor:
        return {}
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT gross_amount,
                       net_amount,
                       gross_amount_sek,
                       net_amount_sek,
                       purchase_datetime,
                       receipt_number,
                       payment_type,
                       expense_type,
                       currency,
                       exchange_rate,
                       total_vat_25,
                       total_vat_12,
                       total_vat_6
                  FROM unified_files
                 WHERE id=%s
            """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            cols = [d[0] for d in cur.description]
            return {k: v for k, v in dict(zip(cols, row)).items() if v is not None}
    except Exception as exc:
        logger.warning("Failed to load receipt %s for box enrichment: %s", rid, exc)
        return {}


def _load_company(rid: str) -> Dict[str, Any]:
    if not db_cursor:
        return {}
    try:
        with db_cursor() as cur:
            cur.execute(
                """
               SELECT c.name, c.orgnr, c.address, c.address2, c.zip, c.city, c.country,
                      c.phone, c.www, c.email
                 FROM companies c JOIN unified_files u ON u.company_id=c.id
                WHERE u.id=%s
            """,
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                return {}
            cols = [d[0] for d in cur.description]
            return {k: v for k, v in dict(zip(cols, row)).items() if v is not None}
    except Exception as exc:
        logger.warning("Failed to load company for %s: %s", rid, exc)
        return {}


def _collect_candidates(receipt: Dict[str, Any], company: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []

    if company:
        company_mapping = {
            "company.name": company.get("name"),
            "company.orgnr": company.get("orgnr"),
            "company.address": company.get("address"),
            "company.zip": company.get("zip"),
            "company.city": company.get("city"),
            "company.country": company.get("country"),
            "company.phone": company.get("phone"),
            "company.www": company.get("www"),
            "company.email": company.get("email"),
        }
        for field, value in company_mapping.items():
            for variant in _string_variants(field, value):
                candidate = _build_candidate(field, variant)
                if candidate:
                    candidates.append(candidate)

    if receipt:
        gross_amount = receipt.get("gross_amount")
        if gross_amount is None:
            gross_amount = receipt.get("gross_amount_sek")
        net_amount = receipt.get("net_amount")
        if net_amount is None:
            net_amount = receipt.get("net_amount_sek")
        receipt_mapping = {
            "receipt.gross_amount": gross_amount,
            "receipt.net_amount": net_amount,
            "receipt.currency": receipt.get("currency"),
            "receipt.purchase_datetime": receipt.get("purchase_datetime"),
            "receipt.payment_type": receipt.get("payment_type"),
            "receipt.expense_type": receipt.get("expense_type"),
            "receipt.receipt_number": receipt.get("receipt_number"),
            "receipt.total_vat_25": receipt.get("total_vat_25"),
            "receipt.total_vat_12": receipt.get("total_vat_12"),
            "receipt.total_vat_6": receipt.get("total_vat_6"),
        }
        for field, value in receipt_mapping.items():
            for variant in _string_variants(field, value):
                candidate = _build_candidate(field, variant)
                if candidate:
                    candidates.append(candidate)

    return candidates


def _score_match(ocr_normalized: str, ocr_numeric: Set[str], ocr_words: Set[str], candidate: Dict[str, Any]) -> float:
    score = 0.0
    candidate_norm = candidate["normalized"]

    if not ocr_normalized or not candidate_norm:
        return score

    if ocr_normalized == candidate_norm:
        return 1.0

    if candidate_norm in ocr_normalized and len(candidate_norm) >= 3:
        score = max(score, 0.85)
    if ocr_normalized in candidate_norm and len(ocr_normalized) >= 3:
        score = max(score, 0.8)

    if ocr_numeric and candidate["numeric_tokens"]:
        if ocr_numeric & candidate["numeric_tokens"]:
            score = max(score, 0.82)

    shared_words = ocr_words & candidate["word_tokens"]
    if shared_words:
        longest = max(len(word) for word in shared_words)
        if longest >= 4:
            score = max(score, 0.7)
        else:
            score = max(score, 0.65)

    return min(score, 1.0)


def _try_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_unit(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _transform_box_coordinates(
    x: Any, y: Any, w: Any, h: Any, rotate_90_ccw: bool
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    x_f = _try_float(x)
    y_f = _try_float(y)
    w_f = _try_float(w)
    h_f = _try_float(h)

    if rotate_90_ccw and None not in (x_f, y_f, w_f, h_f):
        new_x = 1.0 - y_f - h_f
        new_y = x_f
        new_w = h_f
        new_h = w_f
    else:
        new_x, new_y, new_w, new_h = x_f, y_f, w_f, h_f

    return (
        _clamp_unit(new_x),
        _clamp_unit(new_y),
        _clamp_unit(new_w),
        _clamp_unit(new_h),
    )


def _coerce_float(value: Any) -> Any:
    if value in (None, ""):
        return None if value is None else value
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def run_box_enrichment(receipt_id: str, storage_dir: str | Path | None = None) -> Dict[str, Any]:
    receipt_dir = _receipt_dir(storage_dir, receipt_id)
    ocr_path = receipt_dir / "ocr_boxes.json"
    boxes_path = receipt_dir / "boxes.json"

    stats: Dict[str, Any] = {
        "success": True,
        "total_boxes": 0,
        "matched_boxes": 0,
        "unmatched_boxes": 0,
        "match_rate": 0.0,
    }

    if not ocr_path.exists():
        try:
            receipt_dir.mkdir(parents=True, exist_ok=True)
            boxes_path.write_text("[]", encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to create empty boxes.json for %s: %s", receipt_id, exc)
            stats.update({"success": False, "error": "write_error"})
        return stats

    try:
        raw = json.loads(ocr_path.read_text(encoding="utf-8"))
    except Exception:
        stats.update({"success": False, "error": "read_error"})
        return stats

    if not isinstance(raw, list):
        raw = []

    receipt = _load_receipt(receipt_id)
    company = _load_company(receipt_id)
    candidates = _collect_candidates(receipt, company)

    rotate_boxes = False
    orientation_samples = 0
    tall_boxes = 0
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        w_val = _try_float(entry.get("w"))
        h_val = _try_float(entry.get("h"))
        if w_val is None or h_val is None or w_val <= 0 or h_val <= 0:
            continue
        orientation_samples += 1
        if h_val > w_val:
            tall_boxes += 1
    if orientation_samples and tall_boxes / orientation_samples >= 0.6:
        rotate_boxes = True

    enriched_boxes: List[Dict[str, Any]] = []
    total = 0
    matched = 0

    for entry in raw:
        if not isinstance(entry, dict):
            continue
        total += 1

        ocr_text = str(entry.get("field") or "").strip()
        normalized = _normalize_text(ocr_text)
        ocr_numeric = _extract_numeric_tokens(ocr_text, normalized)
        ocr_words = _extract_word_tokens(normalized)

        best_score = 0.0
        best_field: Optional[str] = None

        for candidate in candidates:
            score = _score_match(normalized, ocr_numeric, ocr_words, candidate)
            if score > best_score:
                best_score = score
                best_field = candidate["field"]

        target_field = ocr_text
        if best_field in CANONICAL_FIELDS and best_score >= 0.60:
            target_field = best_field
            matched += 1
        else:
            best_score = 0.0

        box_out = {k: v for k, v in entry.items() if k != "field"}
        x_val, y_val, w_val, h_val = _transform_box_coordinates(
            entry.get("x"),
            entry.get("y"),
            entry.get("w"),
            entry.get("h"),
            rotate_boxes,
        )
        box_out.update(
            {
                "x": _coerce_float(x_val),
                "y": _coerce_float(y_val),
                "w": _coerce_float(w_val),
                "h": _coerce_float(h_val),
                "confidence": _coerce_float(entry.get("confidence")),
                "ocr_text": ocr_text,
                "field": target_field,
                "match_confidence": round(best_score, 4),
            }
        )
        enriched_boxes.append(box_out)

    stats["total_boxes"] = total
    stats["matched_boxes"] = matched
    stats["unmatched_boxes"] = max(total - matched, 0)
    stats["match_rate"] = round((matched / total) if total else 0.0, 4)
    stats["rotated"] = rotate_boxes

    try:
        receipt_dir.mkdir(parents=True, exist_ok=True)
        boxes_path.write_text(json.dumps(enriched_boxes, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to write boxes.json for %s: %s", receipt_id, exc)
        stats.update({"success": False, "error": "write_error"})
        return stats

    return stats


__all__ = ["run_box_enrichment"]
