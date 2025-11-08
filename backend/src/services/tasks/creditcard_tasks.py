from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from models.ai_processing import (
    CreditCardInvoiceExtractionRequest,
    CreditCardInvoiceExtractionResponse,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
)
from models.receipts import Receipt
from observability.events import log_event
from observability.metrics import record_invoice_decision
from services.box_enrichment import run_box_enrichment
from services.invoice_parser import parse_credit_card_statement
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_line_status,
    transition_line_status_and_link,
    transition_processing_status,
)
from services.ocr import run_ocr
from services.pdf_conversion import pdf_to_png_pages
from services.storage import FileStorage
from services.db.files import (
    DuplicateFileError,
    insert_unified_file,
    set_ai_status,
    update_other_data,
)

from .base import db_cursor, logger
from .file_management_tasks import (
    begin_import_stage,
    complete_import_stage,
    ensure_workflow,
    log_finalize_failure,
    log_import_decision,
    log_import_event,
    mark_stage,
)
from .history import _history
from .utils.invoice_utils import (
    _invoice_page_progress,
    _load_invoice_file_records,
    _load_invoice_metadata,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from .utils.metadata_utils import (
    _enforce_file_metadata,
    _load_unified_file_info,
    _update_file_fields,
)
from .utils.status_utils import _update_file_status
from .utils.value_utils import _to_decimal

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
                   AND (match_status IS NULL OR match_status IN ('pending','unmatched'))
                """,
                (document_id,),
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
                                   uf.gross_amount,
                                   NULLIF(uf.gross_amount_sek, 0),
                                   uf.net_amount,
                                   NULLIF(uf.net_amount_sek, 0)
                               ) AS DECIMAL(13, 2)
                           ) AS match_amount,
                           c.name
                      FROM unified_files AS uf
                 LEFT JOIN creditcard_receipt_matches AS m ON m.receipt_id = uf.id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                      WHERE COALESCE(uf.purchase_datetime, uf.created_at) IS NOT NULL
                        AND DATE(COALESCE(uf.purchase_datetime, uf.created_at)) = %s
                        AND COALESCE(
                            uf.gross_amount,
                            NULLIF(uf.gross_amount_sek, 0),
                            uf.net_amount,
                            NULLIF(uf.net_amount_sek, 0)
                        ) IS NOT NULL
                        AND ABS(
                            COALESCE(
                                uf.gross_amount,
                                NULLIF(uf.gross_amount_sek, 0),
                                uf.net_amount,
                                NULLIF(uf.net_amount_sek, 0)
                            ) - %s
                        ) <= 5
                        AND (uf.credit_card_match IS NULL OR uf.credit_card_match = 0)
                        AND m.receipt_id IS NULL
                  ORDER BY ABS(
                               COALESCE(
                                   uf.gross_amount,
                                   NULLIF(uf.gross_amount_sek, 0),
                                   uf.net_amount,
                                   NULLIF(uf.net_amount_sek, 0)
                               ) - %s
                           ) ASC,
                           COALESCE(uf.purchase_datetime, uf.created_at) DESC
                      LIMIT 10
                    """,
                    (date_value, amount, amount),
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
                        "SELECT COUNT(*), SUM(CASE WHEN match_status IN ('auto','manual','confirmed') "
                        "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%s"
                    ),
                    (document_id,),
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
                    "SELECT COUNT(*), SUM(CASE WHEN match_status IN ('auto','manual','confirmed') "
                    "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%s"
                ),
                (document_id,),
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

def wf3_firstcard_invoice(workflow_run_id: int) -> int:
    """
    Workflow 3: FirstCard Invoice Processing.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF3_")
    mark_stage(workflow_run_id, "firstcard_invoice", "running", start=True)

    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message="Workflow run missing file_id.",
            end=True,
            workflow_status_override="failed",
        )
        log_finalize_failure(workflow_run_id, "Workflow run saknar file_id")
        raise ValueError("Workflow run missing file_id")

    metadata = _load_invoice_metadata(file_id) or {}

    begin_import_stage(
        workflow_run_id,
        "fc_ocr",
        message=f"Förbereder OCR för FirstCard {file_id}",
    )
    try:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.OCR_PENDING,
            (
                InvoiceProcessingStatus.UPLOADED,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
    except Exception:
        pass

    parent_info = _load_unified_file_info(file_id) or {}

    try:
        combined_text, other_data = _ensure_creditcard_pages_and_ocr(file_id, parent_info)
        parent_file_type = parent_info.get("file_type") or "unknown"
        parent_workflow_type = parent_info.get("workflow_type") or "unknown"
        page_count = len(other_data.get("pages") or [])
        logger.info(
            "WF3 run %s prepared invoice %s (file_type=%s, workflow_type=%s, pages=%d)",
            workflow_run_id,
            file_id,
            parent_file_type,
            parent_workflow_type,
            page_count,
        )
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "running",
            message=f"file_type={parent_file_type}; workflow_type={parent_workflow_type}; pages={page_count}",
        )
        mark_stage(
            workflow_run_id,
            "ocr_merge",
            "running",
            start=True,
            update_workflow_status=False,
        )

        merged_main_id: Optional[int] = None
        if combined_text:
            merged_main_id = _persist_creditcard_invoice_ocr(file_id, combined_text, metadata)

        ocr_length = len(combined_text or "")
        if merged_main_id:
            if not metadata.get("creditcard_main_id"):
                metadata["creditcard_main_id"] = merged_main_id
            metadata.setdefault("creditcard_invoice_number", f"INV-{file_id}")
            mark_stage(
                workflow_run_id,
                "ocr_merge",
                "succeeded",
                message=f"Persisted merged OCR ({ocr_length} chars) to creditcard_invoices_main id={merged_main_id}",
                end=True,
                update_workflow_status=False,
            )
            logger.info(
                "WF3 run %s persisted %d merged OCR chars for invoice %s (main_id=%s)",
                workflow_run_id,
                ocr_length,
                file_id,
                merged_main_id,
            )
        else:
            if not combined_text:
                mark_stage(
                    workflow_run_id,
                    "ocr_merge",
                    "skipped",
                    message="No OCR text available to persist",
                    end=True,
                    update_workflow_status=False,
                )
            else:
                mark_stage(
                    workflow_run_id,
                    "ocr_merge",
                    "failed",
                    message="Failed to persist merged OCR text to creditcard_invoices_main",
                    end=True,
                    update_workflow_status=False,
                )
                logger.error(
                    "WF3 run %s could not persist merged OCR text for invoice %s",
                    workflow_run_id,
                    file_id,
                )
                raise RuntimeError("Unable to persist merged OCR text to creditcard_invoices_main")

        metadata.update(
            {
                "page_count": page_count,
                "processing_status": InvoiceProcessingStatus.OCR_DONE.value,
                "combined_ocr_text": combined_text,
                "merged_ocr_length": ocr_length,
            }
        )
        _update_invoice_metadata(file_id, metadata)
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.OCR_DONE,
            (
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
    except Exception as exc:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.UPLOADED,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message=f"OCR preparation failed: {exc}",
            end=True,
            workflow_status_override="failed",
        )
        complete_import_stage(
            workflow_run_id,
            "fc_ocr",
            success=False,
            message=str(exc),
        )
        log_finalize_failure(workflow_run_id, f"OCR-misslyckande: {exc}")
        raise
    else:
        complete_import_stage(
            workflow_run_id,
            "fc_ocr",
            success=True,
            message=f"OCR klar ({ocr_length} tecken)",
        )

    if combined_text:
        classification = classify_document_internal(
            DocumentClassificationRequest(file_id=file_id, ocr_text=combined_text)
        )
        doc_type_norm = (classification.document_type or "").strip().lower()
        is_fc_invoice = doc_type_norm == "fc_invoice"
        log_import_decision(
            workflow_run_id,
            "fc_is_fc",
            success=is_fc_invoice,
            message=f"AI1 identifierade dokumenttyp: {classification.document_type}",
        )
        if not is_fc_invoice:
            reason = (
                f"AI1 klassificerade dokumentet som '{classification.document_type}' "
                "men endast FC-fakturor tillåts i detta flöde."
            )
            log_import_event(workflow_run_id, "manual_review", message=reason)
            _move_to_manual_review(file_id, reason)
            log_finalize_failure(workflow_run_id, reason)
            mark_stage(
                workflow_run_id,
                "firstcard_invoice",
                "failed",
                message=reason,
                end=True,
                workflow_status_override="failed",
            )
            raise UnsupportedDocumentTypeError(reason)

    try:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.AI_PROCESSING,
            (
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                InvoiceProcessingStatus.COMPLETED,
            ),
        )
    except Exception:
        pass

    page_ids = [page.get("file_id") for page in (other_data.get("pages") or []) if page.get("file_id")]

    from services.ai_service import AIService

    ai_service = AIService()
    request = CreditCardInvoiceExtractionRequest(
        invoice_id=file_id,
        ocr_text=combined_text,
        page_ids=page_ids,
    )

    import time
    start_time = time.time()
    ai6_provider = ai_service.prompt_provider_names.get("credit_card_invoice_parsing", "unknown")
    ai6_model = ai_service.prompt_model_names.get("credit_card_invoice_parsing", "unknown")
    begin_import_stage(workflow_run_id, "fc_parse", message="AI6 tolkning av faktura")
    try:
        extraction = ai_service.parse_credit_card_invoice(request)
        elapsed = int((time.time() - start_time) * 1000)

        ai6_prompt = ai_service.prompts.get("credit_card_invoice_parsing", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Successfully parsed credit card invoice.",
            f"--- PROMPT ---\n{ai6_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]

        _history(
            file_id,
            "ai6",
            "success",
            ai_stage_name="AI6-CreditCardInvoiceParsing",
            log_text="; ".join(log_parts),
            confidence=extraction.overall_confidence,
            processing_time_ms=elapsed,
            provider=ai6_provider,
            model_name=ai6_model,
        )
        complete_import_stage(
            workflow_run_id,
            "fc_parse",
            success=True,
            message=f"Tolkade {len(extraction.lines)} rader",
        )
        ai7_stats = run_box_enrichment(file_id)
        if not ai7_stats.get("success"):
            logger.warning(
                "AI7 box enrichment failed for %s after AI6: %s",
                file_id,
                ai7_stats.get("error", "unknown"),
            )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {exc}"

        _history(
            file_id,
            "ai6",
            "error",
            ai_stage_name="AI6-CreditCardInvoiceParsing",
            log_text="Failed to parse credit card invoice.",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai6_provider,
            model_name=ai6_model,
        )
        complete_import_stage(
            workflow_run_id,
            "fc_parse",
            success=False,
            message=error_msg,
        )
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message=f"AI6 parsing failed: {type(exc).__name__}: {exc}",
            end=True,
            workflow_status_override="failed",
        )
        log_finalize_failure(workflow_run_id, f"AI6 misslyckades: {exc}")
        raise

    main_id = _persist_creditcard_invoice_main(file_id, extraction.header, combined_text)
    if not main_id:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message="Failed to persist credit card invoice header.",
            end=True,
            workflow_status_override="failed",
        )
        log_finalize_failure(workflow_run_id, "Misslyckades att spara huvuddata")
        raise RuntimeError("Failed to persist credit card invoice header")

    items_inserted = _persist_creditcard_invoice_items(main_id, extraction.lines)

    invoice_line_payloads: list[dict[str, Any]] = []
    for line in extraction.lines:
        amount_candidate = (
            line.amount_sek
            or line.gross_amount
            or line.amount_original
            or Decimal("0.00")
        )
        amount_float = float(amount_candidate) if amount_candidate is not None else 0.0
        invoice_line_payloads.append(
            {
                "transaction_date": line.purchase_date.isoformat() if hasattr(line.purchase_date, "isoformat") else None,
                "merchant_name": line.merchant_name or "",
                "description": line.description or (line.merchant_name or ""),
                "amount": amount_float,
                "confidence": line.confidence,
                "raw_text": line.source_text or "",
            }
        )

    inserted_invoice_lines = _persist_invoice_lines(file_id, invoice_line_payloads)

    metadata = _load_invoice_metadata(file_id) or {}
    metadata.setdefault("processing_status", InvoiceProcessingStatus.AI_PROCESSING.value)
    metadata["creditcard_main_id"] = main_id
    metadata["overall_confidence"] = extraction.overall_confidence
    metadata["invoice_summary"] = {
        "invoice_number": extraction.header.invoice_number,
        "card_holder": extraction.header.card_holder,
        "currency": extraction.header.currency,
        "amount_to_pay": float(extraction.header.amount_to_pay)
        if extraction.header.amount_to_pay is not None
        else None,
    }
    actual_invoice_number = (
        extraction.header.invoice_number
        or metadata.get("creditcard_invoice_number")
        or f"INV-{file_id}"
    )
    metadata["creditcard_invoice_number"] = actual_invoice_number
    if extraction.header.period_start:
        metadata["period_start"] = extraction.header.period_start.isoformat()
    if extraction.header.period_end:
        metadata["period_end"] = extraction.header.period_end.isoformat()
    metadata["line_counts"] = {
        "total": len(extraction.lines),
        "matched": 0,
        "unmatched": len(extraction.lines),
    }
    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
    _update_invoice_metadata(file_id, metadata)

    begin_import_stage(
        workflow_run_id,
        "fc_ready",
        message="Förbereder fakturan för matchning",
    )
    transition_processing_status(
        file_id,
        InvoiceProcessingStatus.READY_FOR_MATCHING,
        (
            InvoiceProcessingStatus.AI_PROCESSING,
            InvoiceProcessingStatus.OCR_DONE,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            InvoiceProcessingStatus.MATCHING_COMPLETED,
            InvoiceProcessingStatus.COMPLETED,
        ),
    )
    transition_document_status(
        file_id,
        InvoiceDocumentStatus.MATCHING,
        (
            InvoiceDocumentStatus.IMPORTED,
            InvoiceDocumentStatus.MATCHING,
            InvoiceDocumentStatus.MATCHED,
            InvoiceDocumentStatus.PARTIALLY_MATCHED,
            InvoiceDocumentStatus.COMPLETED,
        ),
    )
    complete_import_stage(
        workflow_run_id,
        "fc_ready",
        success=True,
        message="Fakturan redo för AI5",
    )

    try:
        mark_stage(
            workflow_run_id,
            "auto_match",
            "running",
            start=True,
            update_workflow_status=False,
        )
        begin_import_stage(
            workflow_run_id,
            "ai5",
            message="AI5 kortmatchning startar",
        )
        matched_auto, evaluated = auto_match_invoice_lines(file_id)
        total_lines, matched_lines = refresh_invoice_match_state(file_id)
        mark_stage(
            workflow_run_id,
            "auto_match",
            "succeeded",
            message=f"Auto-matched {matched_lines} of {total_lines} lines (new matches: {matched_auto})",
            end=True,
            update_workflow_status=False,
        )
        complete_import_stage(
            workflow_run_id,
            "ai5",
            success=True,
            message=f"AI5 matchade {matched_lines}/{total_lines} rader",
        )
        has_match = matched_lines > 0
        log_import_decision(
            workflow_run_id,
            "m_found",
            success=has_match,
            message="Match hittad" if has_match else "Inga automatiska matchningar",
        )
        if has_match:
            begin_import_stage(
                workflow_run_id,
                "m_link",
                message="Länkar kvitton till fakturarader",
            )
            complete_import_stage(
                workflow_run_id,
                "m_link",
                success=True,
                message=f"{matched_lines} rader länkade",
            )
        unmatched_count = max(total_lines - matched_lines, 0)
        if unmatched_count > 0:
            begin_import_stage(
                workflow_run_id,
                "m_unmatched",
                message="Flaggar omatchade rader",
            )
            complete_import_stage(
                workflow_run_id,
                "m_unmatched",
                success=True,
                message=f"{unmatched_count} rader kvar att hantera",
            )
    except Exception as exc:
        mark_stage(
            workflow_run_id,
            "auto_match",
            "failed",
            message=f"Auto-match failed: {exc}",
            end=True,
            update_workflow_status=False,
        )
        complete_import_stage(
            workflow_run_id,
            "ai5",
            success=False,
            message=f"AI5 misslyckades: {exc}",
        )

    mark_stage(
        workflow_run_id,
        "firstcard_invoice",
        "succeeded",
        message=f"Parsed credit card invoice: main_id={main_id}, lines={items_inserted}/{inserted_invoice_lines}",
        end=True,
        workflow_status_override="succeeded",
    )
    begin_import_stage(
        workflow_run_id,
        "finalize_ok",
        message="FirstCard-flödet klart",
    )
    complete_import_stage(
        workflow_run_id,
        "finalize_ok",
        success=True,
        message="Fakturaflödet avslutades utan fel",
    )
    log_import_event(
        workflow_run_id,
        "KLAR",
        message="WF3 slutförd",
    )
    return workflow_run_id

__all__ = [
    '_persist_creditcard_invoice_ocr',
    '_persist_creditcard_invoice_main',
    '_persist_creditcard_invoice_items',
    '_ensure_creditcard_pages_and_ocr',
    '_load_credit_items_for_invoice',
    '_select_credit_item_for_line',
    'auto_match_invoice_lines',
    'refresh_invoice_match_state',
    'wf3_firstcard_invoice',
]
