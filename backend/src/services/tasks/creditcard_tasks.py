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
    get_unified_file_by_hash,
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
from services.ocr import OCR_MIN_NONWHITESPACE_CHARS
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
AMBIGUOUS_AMOUNT_DELTA = Decimal("2")
AMBIGUOUS_DATE_DELTA_DAYS = 1


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
                    existing = get_unified_file_by_hash(page_hash)
                    if not existing:
                        raise
                    page_id = existing.id

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
                model_name=f"fitz-dpi-{pdf_dpi if 'pdf_dpi' in locals() else 300}",
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
            model_name=f"fitz-dpi-{pdf_dpi if 'pdf_dpi' in locals() else 300}",
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

    # Calculate non-whitespace character count for OCR quality check
    nonwhitespace_count = len(combined_text.replace(" ", "").replace("\n", "").replace("\t", ""))
    ocr_is_meaningful = nonwhitespace_count >= OCR_MIN_NONWHITESPACE_CHARS

    if not combined_text or not ocr_is_meaningful:
        logger.warning(
            "Credit card invoice %s produced insufficient OCR text (chars=%d, nonws=%d, threshold=%d).",
            file_id,
            len(combined_text or ""),
            nonwhitespace_count,
            OCR_MIN_NONWHITESPACE_CHARS,
        )
        log_event(
            logger,
            "convert.creditcard.ocr_insufficient",
            file_id=file_id,
            page_count=len(page_refs) or 1,
            char_count=len(combined_text or ""),
            nonwhitespace_count=nonwhitespace_count,
            threshold=OCR_MIN_NONWHITESPACE_CHARS,
        )

        # Mark parent file as OCR_FAILED
        _update_file_status(file_id, AiStatus.OCR_FAILED.value)

        # Mark individual pages as OCR_FAILED if they had no/little text
        for page in page_refs:
            page_id = page.get("file_id")
            if page_id:
                _update_file_status(page_id, AiStatus.OCR_FAILED.value)

        # Persist metadata about the failure for manual review
        other_data["combined_ocr_text"] = combined_text
        other_data["ocr_failed"] = True
        other_data["ocr_failure_reason"] = "insufficient_text"
        other_data["ocr_char_count"] = len(combined_text or "")
        other_data["ocr_nonwhitespace_count"] = nonwhitespace_count
        other_data["ocr_threshold"] = OCR_MIN_NONWHITESPACE_CHARS
        update_other_data(file_id, other_data)

        _history(
            file_id,
            "ocr",
            "failed",
            ai_stage_name="OCR",
            log_text=f"OCR produced insufficient text ({nonwhitespace_count} non-whitespace chars, threshold={OCR_MIN_NONWHITESPACE_CHARS})",
            error_message="OCR text below minimum threshold",
        )

        return combined_text, other_data

    # OCR succeeded with meaningful text
    other_data["combined_ocr_text"] = combined_text
    other_data["ocr_failed"] = False
    other_data["ocr_char_count"] = len(combined_text)
    other_data["ocr_nonwhitespace_count"] = nonwhitespace_count
    update_other_data(file_id, other_data)
    _update_file_status(file_id, InvoiceProcessingStatus.OCR_DONE.value)

    # Mark pages as OCR_DONE
    for page in page_refs:
        page_id = page.get("file_id")
        if page_id:
            _update_file_status(page_id, AiStatus.OCR_DONE.value)

    log_event(
        logger,
        "convert.creditcard.ocr_completed",
        file_id=file_id,
        page_count=len(page_refs) or 1,
        characters=len(combined_text),
        nonwhitespace_count=nonwhitespace_count,
    )

    _history(
        file_id,
        "ocr",
        "success",
        ai_stage_name="OCR",
        log_text=f"OCR completed successfully ({len(combined_text)} chars, {nonwhitespace_count} non-whitespace)",
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

    def _is_ambiguous_pair(primary: dict[str, Any], secondary: dict[str, Any]) -> bool:
        try:
            amount_diff_1 = primary.get("amount_diff")
            amount_diff_2 = secondary.get("amount_diff")
            date_diff_1 = primary.get("date_diff")
            date_diff_2 = secondary.get("date_diff")
            if amount_diff_1 is None or amount_diff_2 is None or date_diff_1 is None or date_diff_2 is None:
                return False
            amount_gap = abs(Decimal(str(amount_diff_1)) - Decimal(str(amount_diff_2)))
            date_gap = abs(int(date_diff_1) - int(date_diff_2))
        except Exception:
            return False
        return amount_gap <= AMBIGUOUS_AMOUNT_DELTA and date_gap <= AMBIGUOUS_DATE_DELTA_DAYS

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
                        AND uf.file_type = 'receipt'
                        AND uf.expense_type = 'corporate'
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

        sorted_candidates = sorted(
            candidates, key=lambda c: (c["amount_diff"], c["date_diff"])
        )
        if len(sorted_candidates) >= 2 and _is_ambiguous_pair(
            sorted_candidates[0], sorted_candidates[1]
        ):
            log_event(
                logger,
                "matching.auto.ambiguous_candidates",
                invoice_id=document_id,
                line_id=line_id,
                primary_receipt_id=sorted_candidates[0].get("receipt_id"),
                secondary_receipt_id=sorted_candidates[1].get("receipt_id"),
                primary_amount_diff=str(sorted_candidates[0].get("amount_diff")),
                secondary_amount_diff=str(sorted_candidates[1].get("amount_diff")),
                primary_date_diff=sorted_candidates[0].get("date_diff"),
                secondary_date_diff=sorted_candidates[1].get("date_diff"),
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

        for candidate in sorted_candidates:
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
