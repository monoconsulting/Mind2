from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


AMBIGUOUS_AMOUNT_ALIGNMENT = "AMBIGUOUS_AMOUNT_ALIGNMENT"


@dataclass(frozen=True)
class FcOcrToken:
    """Single OCR token in normalized coordinates.

    Attributes:
        text: OCR token text.
        x0: Left X coordinate (0..1).
        y0: Top Y coordinate (0..1).
        x1: Right X coordinate (0..1).
        y1: Bottom Y coordinate (0..1).
        confidence: OCR confidence (0..1).
        token_index: Stable index in the input list.
    """

    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float
    token_index: int

    @property
    def cx(self) -> float:
        """Return the X center for the token.

        Returns:
            X center in normalized coordinates.
        """
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        """Return the Y center for the token.

        Returns:
            Y center in normalized coordinates.
        """
        return (self.y0 + self.y1) / 2.0

    @property
    def w(self) -> float:
        """Return token width in normalized coordinates.

        Returns:
            Width value.
        """
        return max(0.0, self.x1 - self.x0)

    @property
    def h(self) -> float:
        """Return token height in normalized coordinates.

        Returns:
            Height value.
        """
        return max(0.0, self.y1 - self.y0)


@dataclass
class FcStatementRowEvidence:
    """Evidence payload for a reconstructed row.

    Attributes:
        token_indices: Token indices included in the row.
        date_token_index: Token index for the date token, if found.
        amount_token_index: Token index for the amount token, if found.
        row_bbox: Bounding box for all row tokens.
        amount_bbox: Bounding box for the selected amount token.
        date_bbox: Bounding box for the selected date token.
        row_y_center: Row center Y coordinate.
        row_height: Row height in normalized coordinates.
    """

    token_indices: list[int]
    date_token_index: Optional[int]
    amount_token_index: Optional[int]
    row_bbox: dict[str, float]
    amount_bbox: Optional[dict[str, float]]
    date_bbox: Optional[dict[str, float]]
    row_y_center: float
    row_height: float


@dataclass
class FcStatementRow:
    """Structured statement row reconstructed from OCR tokens.

    Attributes:
        row_index: 1-based row index within the page.
        date_raw: Raw date token text.
        date_iso: Normalized ISO date (YYYY-MM-DD).
        merchant_raw: Concatenated merchant text.
        merchant_city: Optional city text.
        amount_raw: Raw amount token text.
        amount_value: Parsed SEK amount, if available.
        currency_original: Parsed currency code for foreign amounts.
        amount_original_value: Parsed foreign amount, if available.
        exchange_rate: Parsed exchange rate, if available.
        warnings: Row-level warnings.
        row_confidence: Confidence score for this row.
        evidence: Evidence metadata for debugging.
    """

    row_index: int
    date_raw: str
    date_iso: str
    merchant_raw: str
    merchant_city: str
    amount_raw: str
    amount_value: Optional[float]
    currency_original: Optional[str]
    amount_original_value: Optional[float]
    exchange_rate: Optional[float]
    warnings: list[str]
    row_confidence: float
    evidence: FcStatementRowEvidence


@dataclass
class FcStatementPage:
    """Reconstructed FC statement page.

    Attributes:
        page_index: 0-based index within the document.
        page_file_id: Unified file id for the page.
        rows: Reconstructed statement rows.
        warnings: Page-level warnings.
        amount_band: Detected amount band metadata.
    """

    page_index: int
    page_file_id: str
    rows: list[FcStatementRow]
    warnings: list[str]
    amount_band: dict[str, float]


def _normalize_text(value: str) -> str:
    """Normalize text by trimming and collapsing whitespace.

    Args:
        value: Input text value.

    Returns:
        Normalized text string.
    """
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _normalize_match_text(value: str) -> str:
    """Normalize text for keyword matching.

    Args:
        value: Input text value.

    Returns:
        Uppercase normalized string.
    """
    return _normalize_text(value).upper()


def _is_strict_swe_amount(value: str) -> bool:
    """Check if a string is a strict Swedish amount format.

    Args:
        value: Input text value.

    Returns:
        True if the value matches Swedish amount formats.
    """
    text = _normalize_text(value)
    if not text:
        return False
    pattern = r"^(\d{1,3}([ .]\d{3})*,\d{2}|\d+,\d{2})$"
    return bool(re.match(pattern, text))


def _parse_swe_decimal_to_float(value: str) -> Optional[float]:
    """Parse a Swedish decimal string into float.

    Args:
        value: String like '2.579,80'.

    Returns:
        Parsed float, or None if invalid.
    """
    if not _is_strict_swe_amount(value):
        return None
    cleaned = value.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_swe_decimal_lenient(value: str) -> Optional[float]:
    """Parse a Swedish decimal string leniently (for exchange rates).

    Accepts formats like '11,0297' with more than 2 decimal places.

    Args:
        value: String like '11,0297' or '2.579,80'.

    Returns:
        Parsed float, or None if invalid.
    """
    text = _normalize_text(value)
    if not text:
        return None
    # Match Swedish format with any number of decimal places
    pattern = r"^(\d{1,3}([ .]\d{3})*,\d+|\d+,\d+)$"
    if not re.match(pattern, text):
        return None
    cleaned = text.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_yymmdd_to_iso(value: str) -> str:
    """Convert YYMMDD into ISO date.

    Args:
        value: Date string like '250305'.

    Returns:
        ISO date string or empty string if invalid.
    """
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 6:
        return ""
    yy = int(digits[0:2])
    mm = int(digits[2:4])
    dd = int(digits[4:6])
    yyyy = 2000 + yy if yy <= 79 else 1900 + yy
    try:
        return date(yyyy, mm, dd).isoformat()
    except ValueError:
        return ""


def _looks_like_fc_date(value: str) -> bool:
    """Return True if a token resembles a YYMMDD date.

    Args:
        value: Token text.

    Returns:
        True when the token appears to be a date.
    """
    digits = re.sub(r"\D", "", value or "")
    return len(digits) == 6


def _extract_currency_amount(text: str) -> tuple[Optional[str], Optional[float]]:
    """Extract currency code and amount from freeform text.

    Args:
        text: Merchant text that may include currency and amount.

    Returns:
        Tuple of currency code and parsed amount, or (None, None).
    """
    upper = text.upper()
    patterns = [
        re.compile(r"\b([A-Z]{3})\s*([0-9][0-9 .]*,[0-9]{2})\b"),
        re.compile(r"\b([0-9][0-9 .]*,[0-9]{2})\s*([A-Z]{3})\b"),
    ]
    for pattern in patterns:
        match = pattern.search(upper)
        if not match:
            continue
        if pattern.pattern.startswith(r"\b([A-Z]{3})"):
            currency = match.group(1)
            amount_text = match.group(2)
        else:
            amount_text = match.group(1)
            currency = match.group(2)
        amount = _parse_swe_decimal_to_float(amount_text)
        return currency, amount
    return None, None


def _clean_exchange_rate_token(value: str) -> str:
    """Normalize OCR exchange-rate strings by fixing common OCR swaps.

    Args:
        value: Raw exchange-rate token text.

    Returns:
        Cleaned string with OCR swaps fixed.
    """
    cleaned = re.sub(r"[^0-9ILlOo,\.]", "", value or "")
    cleaned = cleaned.replace("I", "1").replace("l", "1").replace("L", "1").replace("|", "1")
    cleaned = cleaned.replace("O", "0").replace("o", "0")
    return cleaned


def _extract_exchange_rate(tokens: list[FcOcrToken]) -> Optional[float]:
    """Extract exchange rate from a row that includes 'Valutakurs'.

    Args:
        tokens: Tokens in the row.

    Returns:
        Parsed exchange rate, or None if not found.
    """
    joined = " ".join(t.text for t in tokens)
    if "VALUTAKURS" not in _normalize_match_text(joined):
        return None

    match = re.search(r"VALUTAKURS\s*([0-9ILlOo,\.]+)", _normalize_match_text(joined))
    if match:
        candidate = _clean_exchange_rate_token(match.group(1))
        # Use lenient parser for exchange rates (may have 4+ decimal places)
        parsed = _parse_swe_decimal_lenient(candidate)
        if parsed is not None:
            return parsed

    for token in tokens:
        if "VALUTAKURS" not in _normalize_match_text(token.text):
            continue
        candidate = _clean_exchange_rate_token(token.text)
        # Use lenient parser for exchange rates (may have 4+ decimal places)
        parsed = _parse_swe_decimal_lenient(candidate)
        if parsed is not None:
            return parsed

    return None


def _cluster_rows_by_y(tokens: list[FcOcrToken], row_gap: float) -> list[list[FcOcrToken]]:
    """Cluster tokens into row bands using Y-center proximity.

    Args:
        tokens: OCR tokens to cluster.
        row_gap: Maximum Y-center distance to join a row.

    Returns:
        List of row token lists.
    """
    if not tokens:
        return []
    rows: list[list[FcOcrToken]] = []
    current: list[FcOcrToken] = []
    current_center: Optional[float] = None

    for token in sorted(tokens, key=lambda t: (t.cy, t.cx)):
        if current_center is None:
            current = [token]
            current_center = token.cy
            rows.append(current)
            continue
        if abs(token.cy - current_center) <= row_gap:
            current.append(token)
            current_center = sum(t.cy for t in current) / len(current)
        else:
            current = [token]
            current_center = token.cy
            rows.append(current)
    return rows


def _row_bbox(tokens: list[FcOcrToken]) -> dict[str, float]:
    """Compute a bounding box for the provided tokens.

    Args:
        tokens: Tokens to bound.

    Returns:
        Bounding box dictionary.
    """
    xs0 = [t.x0 for t in tokens]
    ys0 = [t.y0 for t in tokens]
    xs1 = [t.x1 for t in tokens]
    ys1 = [t.y1 for t in tokens]
    return {
        "x0": min(xs0) if xs0 else 0.0,
        "y0": min(ys0) if ys0 else 0.0,
        "x1": max(xs1) if xs1 else 0.0,
        "y1": max(ys1) if ys1 else 0.0,
    }


def _contains_header_keywords(text: str) -> bool:
    """Check if text contains FC header/total keywords.

    Args:
        text: Row text.

    Returns:
        True if the text appears to be a header/total row.
    """
    normalized = _normalize_match_text(text)
    header_keywords = {
        "KORTTOTAL",
        "ATT BETALA",
        "SUMMA",
        "TOTAL",
        "TRANSPORT",
        "KOSTNADSSTALLE",
        "KORTNR",
        "REDOVISAD",
        "MOMS",
        "DARAV",
    }
    return any(keyword in normalized for keyword in header_keywords)


def _detect_amount_band(tokens: list[FcOcrToken]) -> tuple[dict[str, float], list[str]]:
    """Detect the right-aligned amount band from tokens.

    Args:
        tokens: OCR tokens.

    Returns:
        Tuple of band metadata and warnings.
    """
    warnings: list[str] = []
    money_tokens = [t for t in tokens if _is_strict_swe_amount(t.text)]
    if len(money_tokens) < 2:
        warnings.append("MISSING_AMOUNT_BAND")
        return {"min_x1": 1.0, "max_x1": 1.0, "count": 0.0}, warnings

    right_edges = sorted(t.x1 for t in money_tokens)
    max_right = right_edges[-1]
    if len(right_edges) >= 5:
        idx = max(int(len(right_edges) * 0.8) - 1, 0)
        threshold = right_edges[idx]
        band_min = max(threshold - 0.01, max_right - 0.05)
    else:
        band_min = max_right - 0.05

    band_tokens = [t for t in money_tokens if t.x1 >= band_min]
    if not band_tokens:
        warnings.append("MISSING_AMOUNT_BAND")
        return {"min_x1": 1.0, "max_x1": max_right, "count": 0.0}, warnings

    return {
        "min_x1": min(t.x1 for t in band_tokens),
        "max_x1": max_right,
        "count": float(len(band_tokens)),
    }, warnings


def _is_amount_ambiguous(
    token: FcOcrToken,
    row_index: int,
    row_centers: list[float],
    row_gap: float,
) -> bool:
    """Return True if an amount token is ambiguous for the given row.

    Args:
        token: Amount token candidate.
        row_index: Index of the current row.
        row_centers: List of row centers.
        row_gap: Row gap threshold.

    Returns:
        True if alignment is ambiguous.
    """
    distances = [(abs(token.cy - center), idx) for idx, center in enumerate(row_centers)]
    distances.sort()
    if not distances:
        return True
    if distances[0][1] != row_index:
        return True
    if len(distances) > 1 and abs(distances[0][0] - distances[1][0]) <= row_gap * 0.35:
        return True
    if abs(token.cy - row_centers[row_index]) > row_gap:
        return True
    return False


def _build_tokens_from_boxes(boxes: Iterable[dict[str, Any]]) -> list[FcOcrToken]:
    """Convert raw OCR boxes into FcOcrToken objects.

    Args:
        boxes: Iterable of OCR box dictionaries.

    Returns:
        List of tokens with normalized coordinates.
    """
    tokens: list[FcOcrToken] = []
    for idx, item in enumerate(boxes):
        text = _normalize_text(item.get("field") or item.get("text") or "")
        if not text:
            continue
        try:
            x = float(item.get("x") or 0.0)
            y = float(item.get("y") or 0.0)
            w = float(item.get("w") or 0.0)
            h = float(item.get("h") or 0.0)
            confidence = float(item.get("confidence") or 0.0)
        except Exception:
            x, y, w, h, confidence = 0.0, 0.0, 0.0, 0.0, 0.0
        tokens.append(
            FcOcrToken(
                text=text,
                x0=x,
                y0=y,
                x1=x + w,
                y1=y + h,
                confidence=confidence,
                token_index=idx,
            )
        )
    return tokens


def load_fc_cards_boxes_from_storage_or_payload(
    storage_dir: str,
    file_id: str,
    payload: Optional[Any] = None,
) -> dict[str, Any]:
    """Load FC OCR boxes from payload or storage.

    Args:
        storage_dir: Storage root directory.
        file_id: Unified file id to search.
        payload: Optional payload that may include OCR boxes.

    Returns:
        Dictionary with keys: boxes, source, warnings.
    """
    warnings: list[str] = []
    if isinstance(payload, list):
        return {"boxes": payload, "source": "payload_list", "warnings": warnings}
    if isinstance(payload, dict):
        if isinstance(payload.get("ocr_boxes"), list):
            return {"boxes": payload.get("ocr_boxes"), "source": "payload.ocr_boxes", "warnings": warnings}
        if isinstance(payload.get("boxes"), list):
            return {"boxes": payload.get("boxes"), "source": "payload.boxes", "warnings": warnings}
        if isinstance(payload.get("ocr_boxes_by_page"), dict):
            page_boxes = payload.get("ocr_boxes_by_page", {}).get(file_id)
            if isinstance(page_boxes, list):
                return {"boxes": page_boxes, "source": "payload.ocr_boxes_by_page", "warnings": warnings}
        pages = payload.get("pages") if isinstance(payload.get("pages"), list) else []
        for page in pages:
            if not isinstance(page, dict):
                continue
            if page.get("file_id") == file_id and isinstance(page.get("ocr_boxes"), list):
                return {"boxes": page.get("ocr_boxes"), "source": "payload.pages.ocr_boxes", "warnings": warnings}

    root = Path(storage_dir) / file_id
    candidates = [root / "boxes.json", root / "ocr_boxes.json"]
    for path in candidates:
        if path.exists() and path.stat().st_size > 0:
            try:
                boxes = json.loads(path.read_text(encoding="utf-8"))
                return {"boxes": boxes, "source": str(path), "warnings": warnings}
            except Exception:
                warnings.append(f"FAILED_TO_READ:{path.name}")
                return {"boxes": [], "source": str(path), "warnings": warnings}

    boxes_dir = root / "boxes"
    if boxes_dir.exists() and boxes_dir.is_dir():
        json_files = sorted(boxes_dir.glob("*.json"))
        if json_files:
            path = json_files[0]
            try:
                boxes = json.loads(path.read_text(encoding="utf-8"))
                warnings.append("BOXES_DIR_USED_FIRST_FILE")
                return {"boxes": boxes, "source": str(path), "warnings": warnings}
            except Exception:
                warnings.append(f"FAILED_TO_READ:{path.name}")

    warnings.append("NO_OCR_BOXES_FOUND")
    return {"boxes": [], "source": None, "warnings": warnings}


def has_fc_cards_boxes(storage_dir: str, file_id: str) -> bool:
    """Return True if OCR boxes exist for a file id.

    Args:
        storage_dir: Storage root directory.
        file_id: Unified file id to check.

    Returns:
        True if OCR boxes were found.
    """
    result = load_fc_cards_boxes_from_storage_or_payload(storage_dir, file_id)
    return bool(result.get("boxes"))


def reconstruct_fc_cards_table_from_boxes(
    page_file_id: str,
    page_index: int,
    boxes: list[dict[str, Any]],
) -> FcStatementPage:
    """Reconstruct FC statement rows from OCR boxes.

    Args:
        page_file_id: Unified file id for the page.
        page_index: 0-based page index.
        boxes: OCR boxes for the page.

    Returns:
        FcStatementPage with reconstructed rows.
    """
    tokens = _build_tokens_from_boxes(boxes)
    if not tokens:
        return FcStatementPage(
            page_index=page_index,
            page_file_id=page_file_id,
            rows=[],
            warnings=["NO_TOKENS"],
            amount_band={"min_x1": 1.0, "max_x1": 1.0, "count": 0.0},
        )

    heights = sorted(t.h for t in tokens if t.h > 0)
    median_height = heights[len(heights) // 2] if heights else 0.01
    row_gap = max(median_height * 0.55, 0.004)

    row_bands = _cluster_rows_by_y(tokens, row_gap)
    row_centers = [sum(t.cy for t in band) / len(band) for band in row_bands]

    amount_band, band_warnings = _detect_amount_band(tokens)

    rows: list[FcStatementRow] = []
    warnings: list[str] = list(band_warnings)
    current_exchange_rate: Optional[float] = None
    last_fx_row: Optional[FcStatementRow] = None

    row_number = 0
    for band_index, band in enumerate(row_bands):
        band_sorted = sorted(band, key=lambda t: t.x0)
        row_text = " ".join(t.text for t in band_sorted)

        if _contains_header_keywords(row_text):
            continue

        exchange_rate = _extract_exchange_rate(band_sorted)
        if exchange_rate is not None:
            current_exchange_rate = exchange_rate
            # Always apply Valutakurs rate to preceding FX row (authoritative source)
            if last_fx_row and last_fx_row.currency_original not in (None, "SEK"):
                last_fx_row.exchange_rate = exchange_rate
            continue

        date_candidates = [
            t for t in band_sorted if _looks_like_fc_date(t.text) and t.cx <= 0.25
        ]
        date_token = date_candidates[0] if date_candidates else None
        date_iso = _parse_yymmdd_to_iso(date_token.text) if date_token else ""
        if not date_iso:
            continue

        amount_candidates = [
            t
            for t in band_sorted
            if _is_strict_swe_amount(t.text) and t.x1 >= amount_band.get("min_x1", 1.0)
        ]
        amount_token: Optional[FcOcrToken] = None
        row_warnings: list[str] = []
        if amount_candidates:
            non_ambiguous = []
            for token in amount_candidates:
                if _is_amount_ambiguous(token, band_index, row_centers, row_gap):
                    row_warnings.append(AMBIGUOUS_AMOUNT_ALIGNMENT)
                    continue
                non_ambiguous.append(token)
            if non_ambiguous:
                amount_token = sorted(non_ambiguous, key=lambda t: (t.x1, t.confidence))[-1]
            else:
                amount_token = None
        else:
            row_warnings.append("NO_AMOUNT_IN_BAND")

        amount_raw = _normalize_text(amount_token.text) if amount_token else ""
        amount_value = _parse_swe_decimal_to_float(amount_raw) if amount_raw else None

        merchant_tokens = [
            t for t in band_sorted if t is not date_token and t is not amount_token
        ]
        merchant_text_for_fx = " ".join(t.text for t in merchant_tokens).strip()
        merchant_text = " ".join(t.text for t in merchant_tokens).strip()
        merchant_city = ""
        if merchant_tokens:
            city_tokens = [t for t in merchant_tokens if t.x0 >= 0.45]
            if city_tokens:
                merchant_city = " ".join(t.text for t in sorted(city_tokens, key=lambda t: t.x0))
                merchant_text = " ".join(
                    t.text for t in merchant_tokens if t not in city_tokens
                ).strip()
                if not merchant_text:
                    merchant_text = " ".join(t.text for t in merchant_tokens).strip()

        currency_original, amount_original = _extract_currency_amount(merchant_text_for_fx)
        resolved_exchange_rate = current_exchange_rate if currency_original else None

        if amount_value is not None and not currency_original:
            currency_original = "SEK"
            amount_original = amount_value
            resolved_exchange_rate = 0.0
        elif (
            currency_original
            and currency_original != "SEK"
            and resolved_exchange_rate is None
            and amount_value is not None
            and amount_original not in (None, 0)
        ):
            try:
                resolved_exchange_rate = float(amount_value) / float(amount_original)
            except Exception:
                resolved_exchange_rate = None

        row_number += 1
        bbox = _row_bbox(band_sorted)
        evidence = FcStatementRowEvidence(
            token_indices=[t.token_index for t in band_sorted],
            date_token_index=date_token.token_index if date_token else None,
            amount_token_index=amount_token.token_index if amount_token else None,
            row_bbox=bbox,
            amount_bbox={
                "x0": amount_token.x0,
                "y0": amount_token.y0,
                "x1": amount_token.x1,
                "y1": amount_token.y1,
            }
            if amount_token
            else None,
            date_bbox={
                "x0": date_token.x0,
                "y0": date_token.y0,
                "x1": date_token.x1,
                "y1": date_token.y1,
            }
            if date_token
            else None,
            row_y_center=row_centers[band_index],
            row_height=bbox["y1"] - bbox["y0"],
        )

        row_confidence = 0.9
        if amount_value is None:
            row_confidence -= 0.4
        if row_warnings:
            row_confidence -= 0.1

        row = FcStatementRow(
            row_index=row_number,
            date_raw=_normalize_text(date_token.text) if date_token else "",
            date_iso=date_iso,
            merchant_raw=merchant_text,
            merchant_city=merchant_city,
            amount_raw=amount_raw,
            amount_value=amount_value,
            currency_original=currency_original,
            amount_original_value=amount_original,
            exchange_rate=resolved_exchange_rate,
            warnings=row_warnings,
            row_confidence=max(0.0, row_confidence),
            evidence=evidence,
        )
        rows.append(row)

        if currency_original:
            last_fx_row = row

    return FcStatementPage(
        page_index=page_index,
        page_file_id=page_file_id,
        rows=rows,
        warnings=warnings,
        amount_band=amount_band,
    )


def build_fc_cards_document_payload(pages: list[FcStatementPage]) -> dict[str, Any]:
    """Build a serializable document payload from reconstructed pages.

    Args:
        pages: Reconstructed pages.

    Returns:
        Serializable dictionary payload.
    """
    all_warnings = [warning for page in pages for warning in page.warnings]
    return {
        "document_type": "FC_CARDS_STATEMENT",
        "pages": [dataclasses.asdict(page) for page in pages],
        "warnings": all_warnings,
        "page_count": len(pages),
        "row_count": sum(len(page.rows) for page in pages),
    }


def store_fc_cards_table_in_db(file_id: str, table_payload: dict[str, Any]) -> bool:
    """Persist the reconstructed table into unified_files.other_data.

    Args:
        file_id: Unified file id for the source PDF.
        table_payload: Document payload to store under fc_cards_table_v1.

    Returns:
        True if the update succeeded.
    """
    if db_cursor is None:
        return False

    try:
        with db_cursor(dictionary=True) as cur:
            cur.execute("SELECT other_data FROM unified_files WHERE id=%s LIMIT 1", (file_id,))
            row = cur.fetchone() or {}
        other_data_raw = row.get("other_data") if isinstance(row, dict) else None
        if isinstance(other_data_raw, str):
            try:
                other_data = json.loads(other_data_raw) if other_data_raw else {}
            except Exception:
                other_data = {}
        elif isinstance(other_data_raw, dict):
            other_data = dict(other_data_raw)
        else:
            other_data = {}

        other_data["fc_cards_table_v1"] = table_payload
        serialized = json.dumps(other_data, ensure_ascii=False)
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET other_data=%s, updated_at=NOW() WHERE id=%s",
                (serialized, file_id),
            )
        return True
    except Exception:
        return False


__all__ = [
    "AMBIGUOUS_AMOUNT_ALIGNMENT",
    "FcOcrToken",
    "FcStatementRowEvidence",
    "FcStatementRow",
    "FcStatementPage",
    "load_fc_cards_boxes_from_storage_or_payload",
    "has_fc_cards_boxes",
    "reconstruct_fc_cards_table_from_boxes",
    "build_fc_cards_document_payload",
    "store_fc_cards_table_in_db",
]
