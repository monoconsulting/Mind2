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

from observability.events import log_event
from services.ocr import run_ocr
from services.pdf_conversion import pdf_to_png_pages
from services.storage import FileStorage
from models.ai_processing import CreditCardInvoiceHeader, CreditCardInvoiceLine

from ..common import DuplicateFileError, db_cursor, insert_unified_file, update_other_data
from ..history import _history, _update_file_fields, _update_file_status
from .invoice_utils import _enforce_file_metadata
from services.invoice_status import InvoiceLineMatchStatus

logger = logging.getLogger(__name__)


def _persist_invoice_lines(invoice_id: str, parsed_lines: list[dict[str, Any]]) -> int:
    if db_cursor is None:
        return 0
    inserted = 0
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
            for line in parsed_lines:
                try:
                    amount = Decimal(str(line.get("amount", 0))).quantize(Decimal("0.01"))
                except Exception:
                    amount = Decimal("0.00")
                transaction_date = line.get("transaction_date")
                merchant_name = line.get("merchant_name") or line.get("description") or ""
                description = line.get("description") or merchant_name
                confidence = line.get("confidence")
                ocr_text = line.get("raw_text") or ""
                cur.execute(
                    (
                        "INSERT INTO invoice_lines "
                        "(invoice_id, transaction_date, amount, merchant_name, description, match_status, extraction_confidence, ocr_source_text) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        invoice_id,
                        transaction_date,
                        amount,
                        merchant_name,
                        description,
                        InvoiceLineMatchStatus.PENDING.value,
                        confidence,
                        ocr_text,
                    ),
                )
                inserted += 1
    except Exception:
        return inserted
    return inserted


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _format_date_for_db(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Support ``date`` objects without importing separately
        return value.strftime("%Y-%m-%d")  # type: ignore[attr-defined]
    except Exception:
        try:
            return str(value)
        except Exception:
            return None


def _persist_creditcard_invoice_ocr(
    invoice_id: str,
    ocr_text: str,
    metadata: dict[str, Any] | None = None,
) -> Optional[int]:
    """Persist merged OCR text into creditcard_invoices_main."""
    if db_cursor is None or not ocr_text:
        return None

    metadata = metadata or {}
    fallback_number = f"INV-{invoice_id}"

    meta_main_id = metadata.get("creditcard_main_id")
    meta_main_id_int: Optional[int]
    try:
        meta_main_id_int = int(meta_main_id) if meta_main_id is not None else None
    except (TypeError, ValueError):
        meta_main_id_int = None

    candidate_numbers: list[str] = []
    summary = metadata.get("invoice_summary")
    if isinstance(summary, dict):
        summary_number = summary.get("invoice_number")
        if summary_number:
            candidate_numbers.append(str(summary_number))
    stored_number = metadata.get("creditcard_invoice_number")
    if stored_number:
        candidate_numbers.append(str(stored_number))
    candidate_numbers.append(fallback_number)

    ordered_numbers: list[str] = []
    seen_numbers: set[str] = set()
    for number in candidate_numbers:
        if number and number not in seen_numbers:
            seen_numbers.add(number)
            ordered_numbers.append(number)

    try:
        with db_cursor() as cur:
            if meta_main_id_int:
                cur.execute(
                    "UPDATE creditcard_invoices_main SET ocr_raw=%s WHERE id=%s",
                    (ocr_text, meta_main_id_int),
                )
                if cur.rowcount > 0:
                    return meta_main_id_int

            for invoice_number in ordered_numbers:
                cur.execute(
                    "SELECT id FROM creditcard_invoices_main WHERE invoice_number=%s",
                    (invoice_number,),
                )
                row = cur.fetchone()
                if row:
                    main_id = int(row[0])
                    cur.execute(
                        "UPDATE creditcard_invoices_main SET ocr_raw=%s WHERE id=%s",
                        (ocr_text, main_id),
                    )
                    return main_id

            cur.execute(
                """
                INSERT INTO creditcard_invoices_main (invoice_number, ocr_raw)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE ocr_raw=VALUES(ocr_raw)
                """,
                (fallback_number, ocr_text),
            )
            main_id = cur.lastrowid
            if not main_id:
                cur.execute(
                    "SELECT id FROM creditcard_invoices_main WHERE invoice_number=%s",
                    (fallback_number,),
                )
                row = cur.fetchone()
                if row:
                    main_id = int(row[0])
            return int(main_id) if main_id else None
    except Exception as exc:
        logger.warning(
            "Failed to persist merged OCR text for invoice %s: %s",
            invoice_id,
            exc,
        )
        return None


def _persist_creditcard_invoice_main(
    invoice_id: str,
    header: CreditCardInvoiceHeader,
    ocr_text: str,
) -> int:
    """Insert or update creditcard_invoices_main and return the row id."""
    if db_cursor is None:
        return 0

    try:
        with db_cursor() as cur:
            fallback_invoice_number = f"INV-{invoice_id}"
            invoice_number = header.invoice_number or fallback_invoice_number
            if invoice_number != fallback_invoice_number:
                try:
                    cur.execute(
                        "UPDATE creditcard_invoices_main SET invoice_number=%s WHERE invoice_number=%s",
                        (invoice_number, fallback_invoice_number),
                    )
                except Exception as exc:  # pragma: no cover - protective logging
                    if "Duplicate entry" not in str(exc):
                        raise

            address = "\n".join(header.billing_address) if header.billing_address else None
            notes = list(header.notes or [])
            while len(notes) < 5:
                notes.append(None)

            sum_value = header.card_total or header.invoice_total
            columns = [
                "invoice_number",
                "ocr_raw",
                "invoice_print_time",
                "card_type",
                "card_name",
                "card_number_masked",
                "card_holder",
                "cost_center",
                "customer_name",
                "co",
                "address",
                "bank_name",
                "bank_org_no",
                "bank_vat_no",
                "bank_fi_no",
                "invoice_date",
                "customer_number",
                "invoice_number_long",
                "due_date",
                "invoice_total",
                "payment_plusgiro",
                "payment_bankgiro",
                "payment_iban",
                "payment_bic",
                "payment_ocr",
                "payment_due",
                "card_total",
                "sum",
                "vat_25",
                "vat_12",
                "vat_6",
                "vat_0",
                "amount_to_pay",
                "reported_vat",
                "next_invoice",
                "note_1",
                "note_2",
                "note_3",
                "note_4",
                "note_5",
                "currency",
            ]
            values = [
                invoice_number,
                ocr_text,
                _format_date_for_db(header.invoice_print_time),
                header.card_type,
                header.card_name,
                header.card_number_masked,
                header.card_holder,
                header.cost_center,
                header.customer_name,
                header.co,
                address,
                header.bank_name,
                header.bank_org_no,
                header.bank_vat_no,
                header.bank_fi_no,
                _format_date_for_db(header.invoice_date),
                header.customer_number,
                header.invoice_number_long,
                _format_date_for_db(header.due_date),
                _to_decimal(header.invoice_total),
                header.plusgiro,
                header.bankgiro,
                header.iban,
                header.bic,
                header.ocr,
                _format_date_for_db(header.payment_due),
                _to_decimal(header.card_total),
                _to_decimal(sum_value),
                _to_decimal(header.vat_25),
                _to_decimal(header.vat_12),
                _to_decimal(header.vat_6),
                _to_decimal(header.vat_0),
                _to_decimal(header.amount_to_pay),
                _to_decimal(header.reported_vat),
                _format_date_for_db(header.next_invoice),
                notes[0],
                notes[1],
                notes[2],
                notes[3],
                notes[4],
                header.currency,
            ]

            def _quote(column: str) -> str:
                return f"`{column}`" if column.lower() in {"sum"} else column

            column_sql = ", ".join(_quote(col) for col in columns)
            placeholders = ", ".join(["%s"] * len(columns))
            update_sql = ", ".join(
                f"{_quote(col)}=VALUES({_quote(col)})"
                for col in columns
                if col != "invoice_number"
            )

            cur.execute(
                f"""
                INSERT INTO creditcard_invoices_main ({column_sql})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE
                {update_sql}
                """,
                values,
            )
            main_id = cur.lastrowid
            if not main_id:
                cur.execute(
                    "SELECT id FROM creditcard_invoices_main WHERE invoice_number=%s",
                    (invoice_number,),
                )
                row = cur.fetchone()
                if row:
                    main_id = int(row[0])
            return int(main_id or 0)
    except Exception:
        logger.exception(
            "Failed to persist credit card invoice main for invoice %s", invoice_id
        )
        return 0


def _persist_creditcard_invoice_items(
    main_id: int,
    lines: list[CreditCardInvoiceLine],
) -> int:
    if db_cursor is None or not main_id:
        return 0

    inserted = 0
    try:
        with db_cursor() as cur:
            cur.execute(
                "DELETE FROM creditcard_invoice_items WHERE main_id=%s",
                (main_id,),
            )
            for line in lines:
                line_no = line.line_no if line.line_no and line.line_no > 0 else inserted + 1
                matched_flag = 1 if getattr(line, "matched", False) else 0
                cur.execute(
                    """
                    INSERT INTO creditcard_invoice_items (
                        main_id,
                        line_no,
                        transaction_id,
                        purchase_date,
                        posting_date,
                        merchant_name,
                        merchant_city,
                        merchant_country,
                        mcc,
                        description,
                        currency_original,
                        amount_original,
                        exchange_rate,
                        amount_sek,
                        vat_rate,
                        vat_amount,
                        net_amount,
                        gross_amount,
                        cost_center_override,
                        project_code,
                        matched
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        main_id,
                        line_no,
                        line.transaction_id,
                        _format_date_for_db(line.purchase_date),
                        _format_date_for_db(line.posting_date),
                        line.merchant_name,
                        line.merchant_city,
                        line.merchant_country,
                        line.mcc,
                        line.description,
                        line.currency_original,
                        _to_decimal(line.amount_original),
                        _to_decimal(line.exchange_rate),
                        _to_decimal(line.amount_sek),
                        _to_decimal(line.vat_rate),
                        _to_decimal(line.vat_amount),
                        _to_decimal(line.net_amount),
                        _to_decimal(line.gross_amount),
                        line.cost_center_override,
                        line.project_code,
                        matched_flag,
                    ),
                )
                inserted += 1
    except Exception:
        return inserted
    return inserted


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
            pages = pdf_to_png_pages(data, converted_root, file_id, dpi=300)
            if not pages:
                raise RuntimeError("PDF conversion resulted in no pages.")

            safe_filename = original_filename or original_path.name
            page_refs = []
            for page in pages:
                page_number = page.index + 1
                page_id = str(uuid.uuid4())
                page_hash = hashlib.sha256(page.bytes).hexdigest()
                try:
                    insert_unified_file(
                        file_id=page_id,
                        file_type="cc_image",
                        workflow_type="creditcard_invoice",
                        content_hash=page_hash,
                        submitted_by="workflow",
                        original_filename=f"{safe_filename}-page-{page_number:04d}.png",
                        ai_status="uploaded",
                        mime_type="image/png",
                        file_suffix=".png",
                        original_file_id=file_id,
                        original_file_name=safe_filename,
                        original_file_size=len(page.bytes),
                        other_data={
                            "detected_kind": "invoice_page",
                            "page_number": page_number,
                            "source_pdf": file_id,
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
                model_name="fitz-dpi-300",
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
            model_name="fitz-dpi-300",
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
                _update_file_status(page_id, "ocr_done")
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
    _update_file_status(file_id, "ocr_done")

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
    """Fetch credit card invoice items and normalise data for matching."""
    data = metadata or (_load_invoice_metadata(document_id) or {})
    main_id_raw = data.get("creditcard_main_id")
    try:
        main_id = int(main_id_raw) if main_id_raw is not None else None
    except (TypeError, ValueError):
        main_id = None
    if main_id is None or db_cursor is None:
        return (None, [])

    items: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       line_no,
                       purchase_date,
                       amount_original,
                       amount_sek,
                       gross_amount,
                       net_amount,
                       merchant_name,
                       description,
                       matched
                  FROM creditcard_invoice_items
                 WHERE main_id=%s
                 ORDER BY line_no ASC, id ASC
                """,
                (main_id,),
            )
            rows = cur.fetchall() or []
    except Exception:
        return (main_id, [])

    for row in rows:
        (
            item_id,
            line_no,
            purchase_date,
            amount_original,
            amount_sek,
            gross_amount,
            net_amount,
            merchant_name,
            description,
            matched_flag,
        ) = row
        items.append(
            {
                "id": int(item_id),
                "line_no": int(line_no) if line_no is not None else None,
                "purchase_date": purchase_date,
                "amount_original": _to_decimal(amount_original),
                "amount_sek": _to_decimal(amount_sek),
                "gross_amount": _to_decimal(gross_amount),
                "net_amount": _to_decimal(net_amount),
                "merchant": (merchant_name or description or "").strip(),
                "matched_flag": int(matched_flag or 0),
                "used": False,
            }
        )

    return (main_id, items)


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
