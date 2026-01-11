from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from ._compat import get_override
from .common import (
    AccountingEntry,
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    AiStatus,
    Receipt,
    ReceiptItem,
    ReceiptStatus,
    db_cursor,
    log_event,
    set_ai_status,
    transition_document_status,
    transition_processing_status,
)
from .history import _history as _base_history
from .utils.invoice_utils import (
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_metadata,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from api.reconciliation_firstcard.utils.db_helpers import ensure_invoice_document

logger = logging.getLogger(__name__)

_VAT_CONTEXT_RE = re.compile(r"\b(momsbelopp|moms|vat)\b", re.IGNORECASE)
_VAT_TOKEN_DIAG_RE = re.compile(
    r"\b(momsbelopp|moms|m0ms|vat|moms%)\b|brutto\s+moms\s+moms%",
    re.IGNORECASE,
)
_VAT_FREE_RE = re.compile(r"\b(momsfri|momsfritt|momsfrit)\b|(?:\b0\s*%\s*moms\b)|(?:\bmoms\s*0[,\.]?\b)|(?:\bvat\s*0[,\.]?\b)", re.IGNORECASE)
_VAT_RATE_RE = re.compile(r"(?<!\d)(25|12|6|0)\s*%")
_VAT_RATE_AMOUNT_RE = re.compile(r"(?<!\d)(25|12|6|0)\s*%\s*[:\-]?\s*([0-9][0-9\s.,]*)")
_VAT_AMOUNT_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{2})|\d+[.,]\d{2})(?!\d)")
_GROSS_TOKEN_RE = re.compile(r"\b(total|summa|att\s+betala|brutto)\b", re.IGNORECASE)
_BRUTTO_MOMS_TABLE_RE = re.compile(
    r"brutto\s+moms\s+moms%\s*([0-9][0-9\s.,]*)\s+([0-9][0-9\s.,]*)\s+(25|12|6|0)\s*%",
    re.IGNORECASE,
)


def _parse_decimal_amount(value: str) -> Decimal | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    raw = raw.replace("\u00a0", "").replace(" ", "")
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", ".")
    try:
        return Decimal(raw)
    except Exception:
        return None


def _extract_gross_total_from_text(text: str) -> Decimal | None:
    if not text:
        return None
    lines = [ln.strip() for ln in text.replace("\r", "\n").splitlines() if ln.strip()]
    candidates: list[Decimal] = []
    for idx, line in enumerate(lines):
        window = " ".join(lines[idx:idx + 2])
        match = _BRUTTO_MOMS_TABLE_RE.search(window)
        if match:
            gross_amount = _parse_decimal_amount(match.group(1))
            if gross_amount is not None:
                candidates.append(gross_amount.quantize(Decimal("0.01")))

        if not _GROSS_TOKEN_RE.search(line):
            continue
        amounts = [_parse_decimal_amount(m) for m in _VAT_AMOUNT_RE.findall(line)]
        if not amounts and idx + 1 < len(lines):
            amounts = [_parse_decimal_amount(m) for m in _VAT_AMOUNT_RE.findall(lines[idx + 1])]
        for amount in amounts:
            if amount is not None:
                candidates.append(amount.quantize(Decimal("0.01")))

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    counts: dict[Decimal, int] = {}
    for value in candidates:
        counts[value] = counts.get(value, 0) + 1
    sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    if sorted_counts and sorted_counts[0][1] >= 2:
        if len(sorted_counts) == 1 or sorted_counts[0][1] > sorted_counts[1][1]:
            return sorted_counts[0][0]
    return None


def _extract_vat_total_from_text(text: str) -> tuple[Decimal, int] | None:
    if not text:
        return None
    lines = [ln.strip() for ln in text.replace("\r", "\n").splitlines() if ln.strip()]
    if not lines:
        return None

    for idx in range(len(lines) - 5):
        if "brutto" in lines[idx].lower() and "moms" in lines[idx + 1].lower() and "moms%" in lines[idx + 2].lower():
            gross_vals = [_parse_decimal_amount(m) for m in _VAT_AMOUNT_RE.findall(lines[idx + 3])]
            vat_vals = [_parse_decimal_amount(m) for m in _VAT_AMOUNT_RE.findall(lines[idx + 4])]
            rate_match = _VAT_RATE_RE.search(lines[idx + 5])
            if gross_vals and vat_vals and rate_match:
                vat_amount = vat_vals[0]
                if vat_amount is None:
                    continue
                return (vat_amount.quantize(Decimal("0.01")), int(rate_match.group(1)))

    keyword_lines = {idx for idx, line in enumerate(lines) if _VAT_CONTEXT_RE.search(line)}

    for idx in range(len(lines)):
        window = " ".join(lines[idx:idx + 3])
        match = _BRUTTO_MOMS_TABLE_RE.search(window)
        if match:
            vat_amount = _parse_decimal_amount(match.group(2))
            if vat_amount is None:
                continue
            return (vat_amount.quantize(Decimal("0.01")), int(match.group(3)))

    rate_candidates: dict[int, set[Decimal]] = {}
    for idx, line in enumerate(lines):
        has_keyword = _VAT_CONTEXT_RE.search(line) is not None
        has_adj_keyword = has_keyword or (idx - 1 in keyword_lines) or (idx + 1 in keyword_lines)
        if not has_adj_keyword:
            continue
        for match in _VAT_RATE_AMOUNT_RE.finditer(line):
            rate_val = int(match.group(1))
            amount_val = _parse_decimal_amount(match.group(2))
            if amount_val is None:
                continue
            rate_candidates.setdefault(rate_val, set()).add(amount_val.quantize(Decimal("0.01")))

    if not rate_candidates:
        return None

    resolved: list[tuple[int, Decimal]] = []
    for rate, values in rate_candidates.items():
        if len(values) == 1:
            resolved.append((rate, next(iter(values))))
        else:
            return None

    if len(resolved) != 1:
        return None

    return (resolved[0][1], resolved[0][0])


def _extract_single_vat_rate_from_text(text: str) -> int | None:
    if not text:
        return None
    rates = [int(match.group(1)) for match in _VAT_RATE_RE.finditer(text)]
    if not rates:
        return None
    unique_rates = {rate for rate in rates if rate in {25, 12, 6}}
    if len(unique_rates) != 1:
        return None
    return next(iter(unique_rates))

def _extract_vat_totals_from_text(text: str) -> dict[str, Any]:
    if not text:
        return {"by_rate": {}, "generic": None, "ambiguous": False, "tokens_found": False}

    lines = [ln.strip() for ln in text.replace("\r", "\n").splitlines() if ln.strip()]
    if not lines:
        return {"by_rate": {}, "generic": None, "ambiguous": False, "tokens_found": False}

    keyword_lines = set()
    tokens_found = False
    for idx, line in enumerate(lines):
        if _VAT_TOKEN_DIAG_RE.search(line):
            keyword_lines.add(idx)
            tokens_found = True
        if _VAT_RATE_RE.search(line):
            tokens_found = True

    rate_candidates: dict[int, set[Decimal]] = {25: set(), 12: set(), 6: set(), 0: set()}
    generic_candidates: set[Decimal] = set()
    ambiguous = False

    for idx, line in enumerate(lines):
        line_lower = line.lower()
        if "inkl" in line_lower and "moms" in line_lower:
            continue

        has_keyword = _VAT_CONTEXT_RE.search(line) is not None
        has_adj_keyword = has_keyword or (idx - 1 in keyword_lines) or (idx + 1 in keyword_lines)

        for match in _VAT_RATE_AMOUNT_RE.finditer(line):
            rate_val = int(match.group(1))
            amount_val = _parse_decimal_amount(match.group(2))
            if amount_val is None:
                continue
            if has_keyword or has_adj_keyword:
                rate_candidates.setdefault(rate_val, set()).add(amount_val)

        if has_keyword:
            if _VAT_FREE_RE.search(line_lower):
                generic_candidates.add(Decimal("0.00"))
                continue

            if not _VAT_RATE_RE.search(line):
                amounts = [_parse_decimal_amount(m) for m in _VAT_AMOUNT_RE.findall(line)]
                amounts = [a for a in amounts if a is not None]
                if len(amounts) == 1:
                    generic_candidates.add(amounts[0])
                elif len(amounts) > 1:
                    ambiguous = True

        if not has_keyword and has_adj_keyword:
            for match in _VAT_RATE_AMOUNT_RE.finditer(line):
                rate_val = int(match.group(1))
                amount_val = _parse_decimal_amount(match.group(2))
                if amount_val is not None:
                    rate_candidates.setdefault(rate_val, set()).add(amount_val)

    by_rate: dict[int, Decimal] = {}
    for rate, values in rate_candidates.items():
        if not values:
            continue
        if len(values) > 1:
            ambiguous = True
            continue
        by_rate[rate] = next(iter(values))

    generic = None
    if generic_candidates:
        if len(generic_candidates) > 1:
            ambiguous = True
        else:
            generic = next(iter(generic_candidates))

    return {"by_rate": by_rate, "generic": generic, "ambiguous": ambiguous, "tokens_found": tokens_found}


def _update_file_status(file_id: str, status: str, confidence: float | None = None) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            if confidence is None:
                cur.execute(
                    "UPDATE unified_files SET ai_status=%s, updated_at=NOW() WHERE id=%s",
                    (status, file_id),
                )
            else:
                cur.execute(
                    "UPDATE unified_files SET ai_status=%s, ai_confidence=%s, updated_at=NOW() "
                    "WHERE id=%s",
                    (status, confidence, file_id),
                )
            return cur.rowcount > 0
    except Exception:
        return False


def _update_file_fields(
    file_id: str,
    *,
    ocr_raw: str | None = None,
    merchant: str | None = None,
    gross: float | None = None,
    purchase_iso: str | None = None,
) -> bool:
    """Update allowed unified_file fields (currently OCR text; others are ignored)."""

    if db_cursor is None:
        return False
    try:
        if ocr_raw is None:
            return False
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET ocr_raw=%s, updated_at=NOW() WHERE id=%s",
                (ocr_raw, file_id),
            )
            return cur.rowcount > 0
    except Exception:
        return False


def _enforce_file_metadata(
    file_id: str,
    *,
    file_type: str | None = None,
    workflow_type: str | None = None,
) -> None:
    """Best-effort update of file_type/workflow_type for a file record."""
    if db_cursor is None:
        return
    updates: list[str] = []
    params: list[Any] = []
    if file_type is not None:
        updates.append("file_type=%s")
        params.append(file_type)
    if workflow_type is not None:
        updates.append("workflow_type=%s")
        params.append(workflow_type)
    if not updates:
        return
    updates.append("updated_at=NOW()")
    params.append(file_id)
    try:
        with db_cursor() as cur:
            cur.execute(
                f"UPDATE unified_files SET {', '.join(updates)} WHERE id=%s",
                tuple(params),
            )
    except Exception:
        logger.warning("Failed to enforce metadata for file %s", file_id, exc_info=True)


def _enqueue_invoice_document(invoice_id: str) -> bool:
    try:
        from .invoice_tasks import process_invoice_document  # Local import to avoid cycles
    except Exception:
        return False
    try:
        if hasattr(process_invoice_document, "delay"):
            process_invoice_document.delay(invoice_id)  # type: ignore[attr-defined]
        else:
            process_invoice_document(invoice_id)  # type: ignore[misc]
        return True
    except Exception:
        return False


def _move_to_manual_review(file_id: str, reason: str | None = None) -> None:
    """Best-effort helper that marks a file as requiring manual review."""

    try:
        set_ai_status(file_id, AiStatus.MANUAL_REVIEW.value)
    except Exception:
        logger.debug("Failed to set manual review status for %s", file_id)
    if reason:
        log_event(logger, "ai.manual_review", file_id=file_id, reason=reason)


def _fail_invoice_processing(invoice_id: str | None, error_message: str | None = None) -> None:
    """Transition an invoice to FAILED and capture the reason in history."""

    if not invoice_id:
        return

    processing_transition = get_override("transition_processing_status", transition_processing_status)
    document_transition = get_override("transition_document_status", transition_document_status)
    history_logger = get_override("_history", _base_history)

    try:
        processing_transitioned = processing_transition(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.UPLOADED,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
            ),
        )
    except Exception:
        processing_transitioned = False

    if processing_transitioned:
        try:
            document_transition(
                invoice_id,
                InvoiceDocumentStatus.FAILED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.MATCHED,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    InvoiceDocumentStatus.COMPLETED,
                ),
            )
        except Exception:
            logger.debug("Failed to transition document status for %s", invoice_id, exc_info=True)

    try:
        history_logger(
            invoice_id,
            job="invoice_processing",
            status="error",
            error_message=error_message,
        )
    except Exception:
        logger.debug("Failed to log invoice failure for %s", invoice_id, exc_info=True)

def _maybe_advance_invoice_from_file(file_id: str, success: bool) -> None:
    invoice_id = _get_invoice_parent_id(file_id)
    if not invoice_id:
        return

    metadata = _load_invoice_metadata(invoice_id) or {}
    page_ids = metadata.get("page_ids")
    if not isinstance(page_ids, list):
        page_ids = []
    if file_id not in page_ids:
        page_ids.append(file_id)
        metadata["page_ids"] = page_ids

    page_status = metadata.get("page_status")
    if not isinstance(page_status, dict):
        page_status = {}
    page_status[file_id] = AiStatus.OCR_DONE.value if success else AiStatus.OCR_FAILED.value
    metadata["page_status"] = page_status

    progress = _invoice_page_progress(invoice_id, metadata)
    metadata["ocr_completed_pages"] = progress["completed"]
    existing_count = metadata.get("page_count")
    if isinstance(existing_count, int) and existing_count > 0:
        metadata["page_count"] = max(existing_count, progress["total"])
    else:
        metadata["page_count"] = progress["total"]

    should_schedule = False
    if success and progress["total"] > 0 and progress["completed"] >= progress["total"]:
        metadata["processing_status"] = InvoiceProcessingStatus.OCR_DONE.value
        next_state = InvoiceProcessingStatus.OCR_DONE
        allowed_states = (
            InvoiceProcessingStatus.UPLOADED,
            InvoiceProcessingStatus.OCR_PENDING,
            InvoiceProcessingStatus.OCR_DONE,
        )
        should_schedule = not metadata.get("invoice_document_scheduled")
    elif success:
        metadata["processing_status"] = InvoiceProcessingStatus.OCR_PENDING.value
        next_state = InvoiceProcessingStatus.OCR_PENDING
        allowed_states = (
            InvoiceProcessingStatus.UPLOADED,
            InvoiceProcessingStatus.OCR_PENDING,
        )
    else:
        metadata["processing_status"] = InvoiceProcessingStatus.FAILED.value
        next_state = InvoiceProcessingStatus.FAILED
        allowed_states = (
            InvoiceProcessingStatus.UPLOADED,
            InvoiceProcessingStatus.OCR_PENDING,
            InvoiceProcessingStatus.OCR_DONE,
            InvoiceProcessingStatus.AI_PROCESSING,
        )

    _update_invoice_metadata(invoice_id, metadata)
    if not ensure_invoice_document(invoice_id, invoice_type="credit_card_invoice"):
        logger.error(
            "Skipping invoice state advance for %s (file %s): missing invoice_documents row",
            invoice_id,
            file_id,
        )
        return

    transition_processing_status(invoice_id, next_state, allowed_states)

    if should_schedule and _enqueue_invoice_document(invoice_id):
        _set_invoice_metadata_field(invoice_id, "invoice_document_scheduled", True)


def _load_receipt_model(file_id: str) -> Optional[Receipt]:
    """Load receipt model with company name from companies table, not merchant_name."""
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT uf.id, uf.submitted_by, uf.created_at, c.name AS company_name,
                       uf.orgnr, uf.purchase_datetime, uf.gross_amount, uf.net_amount,
                       uf.ai_confidence
                FROM unified_files uf
                LEFT JOIN companies c ON uf.company_id = c.id
                WHERE uf.id = %s
                """,
                (file_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        (
            rid,
            submitted_by,
            created_at,
            company_name,
            orgnr,
            purchase_dt,
            gross,
            net,
            ai_conf,
        ) = row

        tags: List[str] = []
        try:
            with db_cursor() as cur:
                cur.execute("SELECT tag FROM file_tags WHERE file_id=%s", (file_id,))
                tags = [tag for (tag,) in cur.fetchall() or []]
        except Exception:
            tags = []

        submitted_at = created_at or datetime.now(timezone.utc)
        if isinstance(submitted_at, datetime):
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
        else:
            submitted_at = datetime.now(timezone.utc)

        if isinstance(purchase_dt, datetime):
            purchase_at = purchase_dt
        elif isinstance(purchase_dt, str):
            try:
                purchase_at = datetime.fromisoformat(purchase_dt.replace("Z", "+00:00"))
            except Exception:
                purchase_at = None
        else:
            purchase_at = None

        receipt = Receipt(
            id=rid,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            company_name=company_name or "",
            orgnr=orgnr or "",
            purchase_datetime=purchase_at,
            gross_amount=Decimal(str(gross or 0)),
            net_amount=Decimal(str(net or 0)),
            ai_confidence=float(ai_conf or 0),
            status=ReceiptStatus.PROCESSED,
            tags=tags,
        )
        return receipt
    except Exception:
        return None


def _get_file_type(file_id: str) -> Optional[str]:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute("SELECT file_type FROM unified_files WHERE id=%s", (file_id,))
            row = cur.fetchone()
            if row:
                (file_type,) = row
                return file_type
    except Exception:
        return None
    return None


def _collect_text_hints(file_id: str) -> str:
    base = Path(os.getenv("STORAGE_DIR", "/data/storage"))
    hints: List[str] = []
    line_items_path = base / "line_items" / f"{file_id}.json"
    if line_items_path.exists():
        try:
            data = json.loads(line_items_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if data is not None:
            def _consume(value: Any) -> None:
                if isinstance(value, str) and value.strip():
                    hints.append(value.strip().lower())
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for v in item.values():
                            _consume(v)
                    else:
                        _consume(item)
            elif isinstance(data, dict):
                for v in data.values():
                    _consume(v)
            else:
                _consume(data)
    return " ".join(hints)


def _load_ai_context(file_id: str):
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT ocr_raw, file_type, expense_type FROM unified_files WHERE id=%s",
                (file_id,),
            )
            return cur.fetchone()
    except Exception:
        return None


def _load_accounting_inputs(file_id: str) -> dict[str, Any] | None:
    """Load and normalize deterministic accounting inputs for AI4.

    Returns a dict with normalized values and a boolean gate `ai4_ready`.

    IMPORTANT: AI4 must not run when totals are missing/invalid. When deterministic
    inputs exist (e.g. currency=SEK and *_original is set), this function fills
    missing SEK totals and exchange_rate and persists them back to unified_files.
    """

    if db_cursor is None:
        return None

    try:
        with db_cursor() as cur:
            vendor_expr = "c.name"
            vat_columns = ["total_vat_25", "total_vat_12", "total_vat_6", "vat"]
            try:
                cur.execute(
                    """
                    SELECT COLUMN_NAME
                      FROM information_schema.COLUMNS
                     WHERE TABLE_SCHEMA = DATABASE()
                       AND TABLE_NAME = 'unified_files'
                       AND COLUMN_NAME IN ('merchant_name', 'total_vat_25', 'total_vat_12', 'total_vat_6', 'vat')
                    """
                )
                existing_columns = {row[0] for row in (cur.fetchall() or [])}
                if "merchant_name" in existing_columns:
                    vendor_expr = "COALESCE(c.name, uf.merchant_name)"
                vat_selects = [
                    f"uf.{col}" if col in existing_columns else f"NULL AS {col}"
                    for col in vat_columns
                ]
            except Exception:
                vat_selects = [f"uf.{col}" for col in vat_columns]
                vendor_expr = "c.name"
            cur.execute(
                f"""
                SELECT
                    uf.gross_amount_sek,
                    uf.net_amount_sek,
                    uf.gross_amount_original,
                    uf.net_amount_original,
                    uf.gross_amount,
                    uf.net_amount,
                    uf.currency,
                    uf.exchange_rate,
                    {vendor_expr} AS vendor_name,
                    uf.ocr_raw,
                    uf.other_data,
                    (
                        SELECT COUNT(*)
                          FROM receipt_items ri
                         WHERE ri.main_id = uf.id
                    ) AS receipt_item_count
                    {"," if vat_selects else ""}
                    {", ".join(vat_selects)}
                FROM unified_files uf
                LEFT JOIN companies c ON uf.company_id = c.id
                WHERE uf.id = %s
                """,
                (file_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            (
                gross_amount_sek,
                net_amount_sek,
                gross_amount_original,
                net_amount_original,
                gross_amount_legacy,
                net_amount_legacy,
                currency,
                exchange_rate,
                vendor_name,
                ocr_raw,
                other_data_raw,
                receipt_item_count,
                total_vat_25,
                total_vat_12,
                total_vat_6,
                total_vat,
            ) = row

            vendor_name_norm = (vendor_name or "").strip()
            item_count = int(receipt_item_count or 0)
            other_data: dict[str, Any] = {}
            if other_data_raw:
                try:
                    if isinstance(other_data_raw, (bytes, bytearray)):
                        other_data_raw = other_data_raw.decode("utf-8")
                    other_data = json.loads(other_data_raw)
                except Exception:
                    other_data = {}
            parsed_text = (
                other_data.get("combined_ocr_text")
                or other_data.get("parsed_text")
                or other_data.get("ocr_text")
            )
            ocr_text = parsed_text or (ocr_raw or "")

            currency_norm = str(currency or "").strip().upper()
            if currency_norm in {"KR", "KR.", "SEK.", "SEK"}:
                currency_norm = "SEK"
            updates: list[str] = []
            params: list[Any] = []

            def _to_decimal(value: Any) -> Decimal | None:
                if value is None:
                    return None
                try:
                    return Decimal(str(value))
                except Exception:
                    return None

            def _vat_total_from_items() -> tuple[Decimal | None, str | None]:
                if item_count <= 0:
                    return (None, None)
                try:
                    cur.execute(
                        """
                        SELECT item_vat_total,
                               vat,
                               vat_percentage,
                               item_total_price_inc_vat,
                               item_total_price_ex_vat,
                               item_price_inc_vat,
                               item_price_ex_vat,
                               number
                        FROM receipt_items
                        WHERE main_id = %s
                        """,
                        (file_id,),
                    )
                    rows = cur.fetchall() or []
                except Exception:
                    return (None, None)

                if not rows:
                    return (None, None)

                vat_sum = Decimal("0.00")
                used_rate = False
                for (
                    item_vat_total,
                    item_vat,
                    vat_percentage,
                    total_inc,
                    total_ex,
                    price_inc,
                    price_ex,
                    number,
                ) in rows:
                    item_vat_value: Decimal | None = None
                    if item_vat_total is not None:
                        item_vat_value = _to_decimal(item_vat_total)
                    elif item_vat is not None:
                        item_vat_value = _to_decimal(item_vat)
                    elif total_inc is not None and total_ex is not None:
                        item_vat_value = _to_decimal(total_inc) - _to_decimal(total_ex)
                    elif price_inc is not None and price_ex is not None and number is not None:
                        item_vat_value = (_to_decimal(price_inc) - _to_decimal(price_ex)) * _to_decimal(number)
                    elif vat_percentage is not None and total_inc is not None:
                        rate = _to_decimal(vat_percentage)
                        if rate is not None:
                            divisor = Decimal("1") + (rate / Decimal("100"))
                            if divisor != 0:
                                item_vat_value = _to_decimal(total_inc) - (_to_decimal(total_inc) / divisor)
                                used_rate = True
                    elif vat_percentage is not None and total_ex is not None:
                        rate = _to_decimal(vat_percentage)
                        if rate is not None:
                            item_vat_value = _to_decimal(total_ex) * rate / Decimal("100")
                            used_rate = True

                    if item_vat_value is None:
                        return (None, None)
                    vat_sum += item_vat_value

                if vat_sum < 0:
                    return (None, None)
                return (
                    vat_sum.quantize(Decimal("0.01")),
                    "receipt_items_vat_rate" if used_rate else "receipt_items_vat_amount",
                )

            def _item_totals() -> tuple[Decimal | None, Decimal | None, Decimal | None]:
                if item_count <= 0:
                    return (None, None, None)
                try:
                    cur.execute(
                        """
                        SELECT SUM(item_total_price_ex_vat),
                               SUM(item_total_price_inc_vat),
                               SUM(item_vat_total)
                        FROM receipt_items
                        WHERE main_id = %s
                        """,
                        (file_id,),
                    )
                    row = cur.fetchone() or (None, None, None)
                except Exception:
                    return (None, None, None)
                sum_ex, sum_inc, sum_vat = row
                return (_to_decimal(sum_ex), _to_decimal(sum_inc), _to_decimal(sum_vat))

            total_vat_25_dec = _to_decimal(total_vat_25)
            total_vat_12_dec = _to_decimal(total_vat_12)
            total_vat_6_dec = _to_decimal(total_vat_6)
            total_vat_dec = _to_decimal(total_vat)

            if currency_norm == "SEK":
                if gross_amount_original is None and gross_amount_legacy is not None:
                    gross_amount_original = gross_amount_legacy
                    updates.append("gross_amount_original=%s")
                    params.append(gross_amount_original)

                if net_amount_original is None and net_amount_legacy is not None:
                    net_amount_original = net_amount_legacy
                    updates.append("net_amount_original=%s")
                    params.append(net_amount_original)

                if ocr_text and (
                    gross_amount_sek is None
                    or net_amount_sek is None
                    or gross_amount_original is None
                    or net_amount_original is None
                ):
                    gross_candidate = _extract_gross_total_from_text(ocr_text)
                    vat_candidate = _extract_vat_total_from_text(ocr_text)
                    single_rate = _extract_single_vat_rate_from_text(ocr_text)

                    if gross_candidate is not None:
                        if gross_amount_original is None:
                            gross_amount_original = gross_candidate
                            updates.append("gross_amount_original=%s")
                            params.append(gross_amount_original)
                        else:
                            gross_existing = _to_decimal(gross_amount_original)
                            if gross_existing is not None and (gross_existing - gross_candidate).copy_abs() > Decimal("0.01"):
                                gross_candidate = None

                    if net_amount_sek is None and gross_amount_sek is not None and single_rate is not None:
                        gross_dec = _to_decimal(gross_amount_sek)
                        if gross_dec is not None:
                            if single_rate == 25:
                                vat_total_value = (gross_dec * Decimal("25") / Decimal("125")).quantize(Decimal("0.01"))
                            elif single_rate == 12:
                                vat_total_value = (gross_dec * Decimal("12") / Decimal("112")).quantize(Decimal("0.01"))
                            else:
                                vat_total_value = (gross_dec * Decimal("6") / Decimal("106")).quantize(Decimal("0.01"))
                            candidate_net = (gross_dec - vat_total_value).quantize(Decimal("0.01"))
                            diff = (gross_dec - (candidate_net + vat_total_value)).copy_abs()
                            if candidate_net >= 0 and diff <= Decimal("0.01"):
                                if net_amount_original is None:
                                    net_amount_original = candidate_net
                                    updates.append("net_amount_original=%s")
                                    params.append(net_amount_original)
                                if net_amount_sek is None:
                                    net_amount_sek = candidate_net
                                    updates.append("net_amount_sek=%s")
                                    params.append(net_amount_sek)
                                if single_rate == 25 and total_vat_25_dec is None:
                                    total_vat_25_dec = vat_total_value
                                    updates.append("total_vat_25=%s")
                                    params.append(total_vat_25_dec)
                                elif single_rate == 12 and total_vat_12_dec is None:
                                    total_vat_12_dec = vat_total_value
                                    updates.append("total_vat_12=%s")
                                    params.append(total_vat_12_dec)
                                elif single_rate == 6 and total_vat_6_dec is None:
                                    total_vat_6_dec = vat_total_value
                                    updates.append("total_vat_6=%s")
                                    params.append(total_vat_6_dec)

                    if vat_candidate is not None and gross_candidate is not None:
                        vat_total_value, vat_rate = vat_candidate
                        if gross_amount_original is not None:
                            gross_dec = _to_decimal(gross_amount_original)
                        else:
                            gross_dec = gross_candidate
                        if gross_dec is not None:
                            candidate_net = (gross_dec - vat_total_value).quantize(Decimal("0.01"))
                            diff = (gross_dec - (candidate_net + vat_total_value)).copy_abs()
                            if candidate_net >= 0 and diff <= Decimal("0.01"):
                                if net_amount_original is None:
                                    net_amount_original = candidate_net
                                    updates.append("net_amount_original=%s")
                                    params.append(net_amount_original)
                                if net_amount_sek is None:
                                    net_amount_sek = candidate_net
                                    updates.append("net_amount_sek=%s")
                                    params.append(net_amount_sek)
                                if gross_amount_sek is None and gross_amount_original is not None:
                                    gross_amount_sek = gross_amount_original
                                    updates.append("gross_amount_sek=%s")
                                    params.append(gross_amount_sek)
                                if vat_rate == 25 and total_vat_25_dec is None:
                                    total_vat_25_dec = vat_total_value
                                    updates.append("total_vat_25=%s")
                                    params.append(total_vat_25_dec)
                                elif vat_rate == 12 and total_vat_12_dec is None:
                                    total_vat_12_dec = vat_total_value
                                    updates.append("total_vat_12=%s")
                                    params.append(total_vat_12_dec)
                                elif vat_rate == 6 and total_vat_6_dec is None:
                                    total_vat_6_dec = vat_total_value
                                    updates.append("total_vat_6=%s")
                                    params.append(total_vat_6_dec)
                                elif vat_rate == 0 and total_vat_dec is None and total_vat is None:
                                    total_vat_dec = vat_total_value
                                    total_vat = str(total_vat_dec)
                                    updates.append("vat=%s")
                                    params.append(str(total_vat_dec))

                if net_amount_sek is None and gross_amount_sek is not None and item_count > 0:
                    sum_ex, sum_inc, sum_vat = _item_totals()
                    gross_dec = _to_decimal(gross_amount_sek)
                    if gross_dec is not None:
                        if sum_ex is not None and sum_inc is not None:
                            if (sum_inc - gross_dec).copy_abs() <= Decimal("0.01"):
                                candidate_net = sum_ex.quantize(Decimal("0.01"))
                                if net_amount_original is None:
                                    net_amount_original = candidate_net
                                    updates.append("net_amount_original=%s")
                                    params.append(net_amount_original)
                                if net_amount_sek is None:
                                    net_amount_sek = candidate_net
                                    updates.append("net_amount_sek=%s")
                                    params.append(net_amount_sek)
                        elif sum_ex is not None and sum_vat is not None:
                            if ((sum_ex + sum_vat) - gross_dec).copy_abs() <= Decimal("0.01"):
                                candidate_net = sum_ex.quantize(Decimal("0.01"))
                                if net_amount_original is None:
                                    net_amount_original = candidate_net
                                    updates.append("net_amount_original=%s")
                                    params.append(net_amount_original)
                                if net_amount_sek is None:
                                    net_amount_sek = candidate_net
                                    updates.append("net_amount_sek=%s")
                                    params.append(net_amount_sek)

                if gross_amount_original is not None and (net_amount_original is None or net_amount_sek is None):
                    vat_total_value: Decimal | None = None
                    vat_buckets = [total_vat_25_dec, total_vat_12_dec, total_vat_6_dec]
                    if any(v is not None for v in vat_buckets):
                        vat_total_value = sum((v for v in vat_buckets if v is not None), Decimal("0.00"))
                    elif total_vat_dec is not None:
                        vat_total_value = total_vat_dec
                    elif item_count > 0:
                        vat_total_value, _ = _vat_total_from_items()

                    if vat_total_value is not None:
                        gross_dec = _to_decimal(gross_amount_original)
                        if gross_dec is not None:
                            candidate_net = (gross_dec - vat_total_value).quantize(Decimal("0.01"))
                            diff = (gross_dec - (candidate_net + vat_total_value)).copy_abs()
                            if candidate_net >= 0 and diff <= Decimal("0.01"):
                                if net_amount_original is None:
                                    net_amount_original = candidate_net
                                    updates.append("net_amount_original=%s")
                                    params.append(net_amount_original)
                                if net_amount_sek is None:
                                    net_amount_sek = candidate_net
                                    updates.append("net_amount_sek=%s")
                                    params.append(net_amount_sek)

                if gross_amount_sek is None and gross_amount_original is not None:
                    gross_amount_sek = gross_amount_original
                    updates.append("gross_amount_sek=%s")
                    params.append(gross_amount_sek)

                if net_amount_sek is None and net_amount_original is not None:
                    net_amount_sek = net_amount_original
                    updates.append("net_amount_sek=%s")
                    params.append(net_amount_sek)

                if exchange_rate in (None, 0):
                    exchange_rate = 1.0
                    updates.append("exchange_rate=%s")
                    params.append(exchange_rate)

            elif currency_norm:
                # Deterministic FX conversion when SEK totals are missing but original totals + exchange_rate exist.
                # Only fill *_sek fields when they are NULL in DB to avoid overwriting validated SEK totals.
                if exchange_rate not in (None, 0) and isinstance(exchange_rate, Decimal):
                    if gross_amount_sek is None and gross_amount_original is not None:
                        gross_amount_sek = (gross_amount_original * exchange_rate).quantize(Decimal("0.01"))
                        updates.append("gross_amount_sek=%s")
                        params.append(gross_amount_sek)
                    if net_amount_sek is None and net_amount_original is not None:
                        net_amount_sek = (net_amount_original * exchange_rate).quantize(Decimal("0.01"))
                        updates.append("net_amount_sek=%s")
                        params.append(net_amount_sek)
                else:
                    # exchange_rate is missing or not a Decimal; leave SEK totals unset.
                    pass

            if updates:
                updates.append("updated_at=NOW()")
                params.append(file_id)
                cur.execute(
                    f"UPDATE unified_files SET {', '.join(updates)} WHERE id=%s",
                    tuple(params),
                )

            vat_amount_sek = None
            if gross_amount_sek is not None and net_amount_sek is not None:
                try:
                    vat_amount_sek = gross_amount_sek - net_amount_sek
                except Exception:
                    vat_amount_sek = None

            has_sek_totals = gross_amount_sek is not None and net_amount_sek is not None
            has_original_totals = gross_amount_original is not None and net_amount_original is not None

            if currency_norm and currency_norm != "SEK" and not has_sek_totals and exchange_rate in (None, 0):
                return {
                    "ai4_ready": False,
                    "reason": "missing exchange_rate for FX totals",
                    "gross_amount_sek": gross_amount_sek,
                    "net_amount_sek": net_amount_sek,
                    "vat_amount_sek": vat_amount_sek,
                    "gross_amount_original": gross_amount_original,
                    "net_amount_original": net_amount_original,
                    "currency": currency_norm or None,
                    "exchange_rate": exchange_rate,
                    "vendor_name": vendor_name_norm or None,
                    "receipt_item_count": item_count,
                    "missing_totals": False,
                }

            ai4_ready = has_sek_totals
            if not ai4_ready:
                # Controlled indicator for the caller to mark needs_review and skip AI4.
                return {
                    "ai4_ready": False,
                    "reason": "missing totals for accounting",
                    "gross_amount_sek": gross_amount_sek,
                    "net_amount_sek": net_amount_sek,
                    "vat_amount_sek": vat_amount_sek,
                    "gross_amount_original": gross_amount_original,
                    "net_amount_original": net_amount_original,
                    "currency": currency_norm or None,
                    "exchange_rate": exchange_rate,
                    "vendor_name": vendor_name_norm or None,
                    "receipt_item_count": item_count,
                    "missing_totals": not has_sek_totals and not has_original_totals,
                }

            if not vendor_name_norm:
                return {
                    "ai4_ready": False,
                    "reason": "missing vendor_name",
                    "gross_amount_sek": gross_amount_sek,
                    "net_amount_sek": net_amount_sek,
                    "vat_amount_sek": vat_amount_sek,
                    "gross_amount_original": gross_amount_original,
                    "net_amount_original": net_amount_original,
                    "currency": currency_norm or None,
                    "exchange_rate": exchange_rate,
                    "vendor_name": None,
                    "receipt_item_count": item_count,
                    "missing_totals": False,
                }

            # Guard obvious invalid totals to avoid sending nonsense to AI4.
            try:
                if gross_amount_sek is not None and net_amount_sek is not None and gross_amount_sek < net_amount_sek:
                    return {
                        "ai4_ready": False,
                        "reason": "missing totals for accounting",
                        "gross_amount_sek": gross_amount_sek,
                        "net_amount_sek": net_amount_sek,
                        "vat_amount_sek": vat_amount_sek,
                        "gross_amount_original": gross_amount_original,
                        "net_amount_original": net_amount_original,
                        "currency": currency_norm or None,
                        "exchange_rate": exchange_rate,
                        "vendor_name": vendor_name_norm or None,
                        "receipt_item_count": item_count,
                        "missing_totals": False,
                    }
            except Exception:
                return {
                    "ai4_ready": False,
                    "reason": "missing totals for accounting",
                    "gross_amount_sek": gross_amount_sek,
                    "net_amount_sek": net_amount_sek,
                    "vat_amount_sek": vat_amount_sek,
                    "gross_amount_original": gross_amount_original,
                    "net_amount_original": net_amount_original,
                    "currency": currency_norm or None,
                    "exchange_rate": exchange_rate,
                    "vendor_name": vendor_name_norm or None,
                    "receipt_item_count": item_count,
                    "missing_totals": False,
                }

            return {
                "ai4_ready": True,
                "gross_amount_sek": gross_amount_sek,
                "net_amount_sek": net_amount_sek,
                "vat_amount_sek": vat_amount_sek,
                "gross_amount_original": gross_amount_original,
                "net_amount_original": net_amount_original,
                "currency": currency_norm or None,
                "exchange_rate": exchange_rate,
                "vendor_name": vendor_name_norm or None,
                "receipt_item_count": item_count,
            }
    except Exception:
        return None


def _load_receipt_items(file_id: str):
    """Load receipt items with their IDs from the database."""
    if db_cursor is None:
        return []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, main_id, article_id, name, number,
                       item_price_ex_vat, item_price_inc_vat,
                       item_total_price_ex_vat, item_total_price_inc_vat,
                       currency, vat, vat_percentage
                FROM receipt_items
                WHERE main_id = %s
                """,
                (file_id,),
            )
            rows = cur.fetchall()
            items = []
            for row in rows:
                items.append(ReceiptItem(
                    id=row[0],
                    main_id=row[1],
                    article_id=row[2] or "",
                    name=row[3],
                    number=row[4],
                    item_price_ex_vat=Decimal(str(row[5] or 0)),
                    item_price_inc_vat=Decimal(str(row[6] or 0)),
                    item_total_price_ex_vat=Decimal(str(row[7] or 0)),
                    item_total_price_inc_vat=Decimal(str(row[8] or 0)),
                    currency=row[9] or "SEK",
                    vat=Decimal(str(row[10] or 0)),
                    vat_percentage=Decimal(str(row[11] or 0)),
                ))
            return items
    except Exception as exc:
        logger.exception("Failed to load receipt items for file_id=%s: %s", file_id, exc)
        return []


def _save_accounting_entries(file_id: str, entries: List[AccountingEntry]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (file_id,))
            for entry in entries:
                cur.execute(
                    (
                        "INSERT INTO ai_accounting_proposals "
                        "(receipt_id, item_id, account_code, debit, credit, vat_rate, notes) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        file_id,
                        entry.item_id if hasattr(entry, 'item_id') and entry.item_id else None,
                        entry.account_code,
                        float(entry.debit or 0),
                        float(entry.credit or 0),
                        (float(entry.vat_rate) if entry.vat_rate is not None else None),
                        (entry.notes[:255] if entry.notes else None),
                    ),
                )
        return True
    except Exception as exc:
        logger.exception("Failed to persist ai_accounting_proposals for file_id=%s: %s", file_id, exc)
        return False


__all__ = [
    "_update_file_status",
    "_update_file_fields",
    "_enforce_file_metadata",
    "_enqueue_invoice_document",
    "_move_to_manual_review",
    "_fail_invoice_processing",
    "_maybe_advance_invoice_from_file",
    "_load_receipt_model",
    "_get_file_type",
    "_collect_text_hints",
    "_load_ai_context",
    "_load_accounting_inputs",
    "_load_receipt_items",
    "_save_accounting_entries",
]
