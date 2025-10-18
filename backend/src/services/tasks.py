from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


from services.queue_manager import get_celery
from celery import chain, group, chord
import uuid
import hashlib
from services.storage import FileStorage
from services.pdf_conversion import pdf_to_png_pages
try:
    from services.db.files import insert_unified_file, update_other_data, DuplicateFileError
except ImportError:
    # Stub for linting if the file is not yet created
    insert_unified_file = lambda **kwargs: None
    update_other_data = lambda **kwargs: None
    class DuplicateFileError(Exception): pass
from observability.metrics import record_invoice_decision, track_task
from services.ocr import run_ocr
from services.enrichment import enrich_receipt, provider_from_env
from services.validation import validate_receipt
from services.accounting import propose_accounting_entries
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    InvoiceLineMatchStatus,
    transition_document_status,
    transition_processing_status,
    transition_line_status,
    transition_line_status_and_link,
)
from services.invoice_parser import parse_credit_card_statement
from models.accounting import AccountingRule
from models.ai_processing import (
    AccountingClassificationRequest,
    CreditCardInvoiceExtractionRequest,
    CreditCardInvoiceExtractionResponse,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
    CreditCardMatchRequest,
    DataExtractionRequest,
    DocumentClassificationRequest,
    ExpenseClassificationRequest,
    ReceiptItem,
)
from models.receipts import AccountingEntry, Receipt, ReceiptStatus
from api.ai_processing import (
    classify_accounting_internal,
    classify_document_internal,
    classify_expense_internal,
    extract_data_internal,
    match_credit_card_internal,
)


logger = logging.getLogger(__name__)

_INVOICE_PAGE_COMPLETE_STATUSES = {
    "ocr_done",
    InvoiceProcessingStatus.OCR_DONE.value,
    InvoiceProcessingStatus.READY_FOR_MATCHING.value,
    InvoiceProcessingStatus.MATCHING_COMPLETED.value,
    InvoiceProcessingStatus.COMPLETED.value,
}

celery_app = get_celery()


INSERT_HISTORY_SQL = """
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def _history(
    file_id: str,
    job: str,
    status: str,
    ai_stage_name: str | None = None,
    log_text: str | None = None,
    error_message: str | None = None,
    confidence: float | None = None,
    processing_time_ms: int | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> None:
    """Log processing history with detailed information.

    Args:
        file_id: The file being processed
        job: Job type (e.g., 'ai1', 'ai2', 'ocr', 'classification')
        status: 'success' or 'error'
        ai_stage_name: Human-readable stage name (e.g., 'AI1-DocumentClassification')
        log_text: Detailed explanation of what happened
        error_message: Error details if status is 'error'
        confidence: Confidence score for this stage
        processing_time_ms: Time taken in milliseconds
        provider: AI provider used (e.g., 'rule-based', 'openai')
        model_name: Model name used
    """
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                INSERT_HISTORY_SQL,
                (
                    file_id,
                    job,
                    status,
                    ai_stage_name,
                    log_text,
                    error_message,
                    confidence,
                    processing_time_ms,
                    provider,
                    model_name,
                ),
            )
    except Exception:
        # best-effort history
        pass


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
    ocr_raw: str | None = None,
) -> bool:
    """Update ONLY OCR raw text. All business data set by AI, not OCR."""
    if db_cursor is None:
        return False
    try:
        if ocr_raw is None:
            return False
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET ocr_raw=%s, updated_at=NOW() WHERE id=%s",
                (ocr_raw, file_id)
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


def _load_unified_file_info(file_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, file_type, workflow_type, original_file_id, other_data, mime_type, "
                    "original_filename, original_file_name "
                    "FROM unified_files WHERE id=%s"
                ),
                (file_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    (
        uid,
        file_type,
        workflow_type,
        original_file_id,
        raw_other,
        mime_type,
        original_filename,
        original_file_name,
    ) = row
    other_data: dict[str, Any]
    if raw_other:
        try:
            other_data = json.loads(raw_other)
        except Exception:
            other_data = {}
    else:
        other_data = {}
    return {
        "id": uid,
        "file_type": file_type or "",
        "workflow_type": workflow_type or "",
        "original_file_id": original_file_id,
        "other_data": other_data,
        "mime_type": mime_type,
        "original_filename": original_filename,
        "original_file_name": original_file_name,
    }


def _get_invoice_parent_id(file_id: str) -> Optional[str]:
    info = _load_unified_file_info(file_id)
    if not info:
        return None
    file_type = str(info.get("file_type") or "").lower()
    if file_type in {"invoice_page", "cc_image"}:
        parent = info.get("original_file_id")
        return str(parent) if isinstance(parent, str) and parent else None
    if file_type in {"invoice", "cc_pdf"}:
        identifier = info.get("id")
        return str(identifier) if isinstance(identifier, str) and identifier else None
    return None


def _load_invoice_metadata(invoice_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    payload = row[0]
    if not payload:
        return {}
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except Exception:
            payload = payload.decode("latin1", errors="ignore")
    try:
        return json.loads(payload)
    except Exception:
        return {}


def _update_invoice_metadata(invoice_id: str, metadata: dict[str, Any]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE invoice_documents SET metadata_json=%s WHERE id=%s",
                (json.dumps(metadata or {}), invoice_id),
            )
        return True
    except Exception:
        return False


def _set_invoice_metadata_field(invoice_id: str, field: str, value: Any) -> dict[str, Any] | None:
    metadata = _load_invoice_metadata(invoice_id)
    if metadata is None:
        return None
    metadata[field] = value
    if _update_invoice_metadata(invoice_id, metadata):
        return metadata
    return None


def _invoice_page_progress(invoice_id: str, metadata: dict[str, Any] | None = None) -> dict[str, int]:
    data = metadata if metadata is not None else (_load_invoice_metadata(invoice_id) or {})
    page_ids = data.get("page_ids")
    if not isinstance(page_ids, list):
        page_ids = []
    page_status = data.get("page_status")
    if not isinstance(page_status, dict):
        page_status = {}
    completed = 0
    for pid in page_ids:
        status = (page_status.get(pid) or "").lower()
        if status in _INVOICE_PAGE_COMPLETE_STATUSES:
            completed += 1
    if not page_ids and page_status:
        completed = sum(
            1
            for status in page_status.values()
            if (status or "").lower() in _INVOICE_PAGE_COMPLETE_STATUSES
        )
    total = data.get("page_count")
    if not isinstance(total, int) or total <= 0:
        fallback = len(page_ids) or len(page_status)
        total = fallback if fallback > 0 else 0
    pending = max(total - completed, 0)
    return {"total": total, "completed": completed, "pending": pending}


def _enqueue_invoice_document(invoice_id: str) -> bool:
    try:
        task = process_invoice_document  # type: ignore[name-defined]
    except NameError:
        return False
    try:
        if hasattr(task, "delay"):
            task.delay(invoice_id)  # type: ignore[attr-defined]
        else:
            task(invoice_id)  # type: ignore[misc]
        return True
    except Exception:
        return False


def _load_invoice_file_records(invoice_id: str) -> list[tuple[Any, ...]]:
    if db_cursor is None:
        return []
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, file_type, ai_status, other_data, ocr_raw "
                    "FROM unified_files "
                    "WHERE id=%s OR original_file_id=%s "
                    "ORDER BY created_at ASC"
                ),
                (invoice_id, invoice_id),
            )
            return cur.fetchall() or []
    except Exception:
        return []


def _collect_invoice_ocr_text(invoice_id: str) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for record in _load_invoice_file_records(invoice_id):
        if not record:
            continue
        file_id = str(record[0])
        ocr_raw = ""
        if len(record) >= 5 and record[4]:
            try:
                ocr_raw = record[4]
            except Exception:
                ocr_raw = ""
        if ocr_raw:
            texts.append((file_id, ocr_raw))
    return texts


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
    other_data = dict(parent_info.get("other_data", {}) or {})
    existing_combined = other_data.get("combined_ocr_text")
    if existing_combined:
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

        data = original_path.read_bytes()
        converted_root = (fs.base / "converted" / file_id).resolve()
        converted_root.mkdir(parents=True, exist_ok=True)

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
    else:
        logger.info(
            "WF3 creditcard invoice %s reusing %d existing page image(s).",
            file_id,
            len(page_refs),
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
    else:
        result = run_ocr(file_id, storage_dir)
        text = (result or {}).get("text") or ""
        if text:
            texts.append(text)
            _update_file_fields(file_id, ocr_raw=text)

    combined_text = "\n\n--- PAGE BREAK ---\n\n".join(texts).strip()
    if not combined_text:
        logger.warning("Credit card invoice %s produced no OCR text.", file_id)
    other_data["combined_ocr_text"] = combined_text
    update_other_data(file_id, other_data)
    _update_file_status(file_id, "ocr_done")

    return combined_text, other_data

def _auto_match_invoice_lines(document_id: str) -> tuple[int, int]:
    if db_cursor is None:
        return (0, 0)

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
        return (0, 0)

    if not pending_rows:
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
    candidate_order: list[str] = []
    candidate_map: dict[str, dict[str, Any]] = {}

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
                           uf.purchase_datetime,
                           uf.gross_amount,
                           c.name
                      FROM unified_files AS uf
                 LEFT JOIN creditcard_receipt_matches AS m ON m.receipt_id = uf.id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                     WHERE uf.purchase_datetime IS NOT NULL
                       AND uf.gross_amount IS NOT NULL
                       AND DATE(uf.purchase_datetime) = %s
                       AND ABS(uf.gross_amount - %s) <= 5
                       AND (uf.credit_card_match IS NULL OR uf.credit_card_match = 0)
                       AND m.receipt_id IS NULL
                  ORDER BY ABS(uf.gross_amount - %s) ASC, uf.created_at DESC
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
        }
        if amount is None or tx_date is None:
            continue
        for candidate in _fetch_receipt_candidates(tx_date, amount):
            receipt_id = str(candidate[0])
            existing = candidate_map.get(receipt_id)
            if not existing:
                existing = {
                    "receipt_id": receipt_id,
                    "purchase_datetime": candidate[1],
                    "amount": _safe_decimal(candidate[2]),
                    "company_name": candidate[3],
                }
                candidate_map[receipt_id] = existing
                candidate_order.append(receipt_id)

    matched = 0
    used_receipts: set[str] = set()

    for receipt_id in candidate_order:
        if receipt_id in used_receipts:
            continue
        candidate = candidate_map.get(receipt_id)
        if not candidate:
            continue
        receipt_amount = candidate.get("amount")
        if receipt_amount is None:
            continue
        try:
            request = CreditCardMatchRequest(
                file_id=receipt_id,
                purchase_date=candidate.get("purchase_datetime"),
                amount=receipt_amount,
                invoice_id=document_id,
                merchant_name=candidate.get("company_name"),
            )
        except Exception:
            continue
        try:
            response = match_credit_card_internal(request)
        except Exception:
            continue
        if not response.matched or response.credit_card_invoice_item_id is None:
            continue
        line_id = int(response.credit_card_invoice_item_id)
        line_ctx = pending.get(line_id)
        if not line_ctx or line_ctx.get("matched"):
            continue
        updated = transition_line_status_and_link(
            line_id,
            receipt_id,
            response.confidence,
            InvoiceLineMatchStatus.AUTO,
            (
                InvoiceLineMatchStatus.PENDING,
                InvoiceLineMatchStatus.UNMATCHED,
            ),
        )
        if not updated:
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
        record_invoice_decision("matched")

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

    return (matched, len(pending_rows))


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
    page_status[file_id] = "ocr_done" if success else "ocr_failed"
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
            purchase_at: Optional[datetime] = (
                purchase_dt if purchase_dt.tzinfo is not None else purchase_dt.replace(tzinfo=timezone.utc)
            )
        elif isinstance(purchase_dt, str):
            try:
                parsed = datetime.fromisoformat(purchase_dt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                purchase_at = parsed
            except Exception:
                purchase_at = None
        else:
            purchase_at = None

        gross_dec = Decimal(str(gross)) if gross is not None else None
        net_dec = Decimal(str(net)) if net is not None else None
        confidence = float(ai_conf) if ai_conf is not None else None

        return Receipt(
            id=rid,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            merchant_name=company_name,  # From companies table via JOIN
            orgnr=orgnr,
            purchase_datetime=purchase_at,
            gross_amount=gross_dec,
            net_amount=net_dec,
            vat_breakdown={},
            tags=tags,
            location_opt_in=False,
            company_card_flag=False,
            status=ReceiptStatus.PROCESSING,
            confidence_summary=confidence,
        )
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


def _load_accounting_inputs(file_id: str):
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT gross_amount_sek, net_amount_sek,
                       (gross_amount_sek - net_amount_sek) AS vat_amount,
                       c.name AS vendor_name
                  FROM unified_files uf
             LEFT JOIN companies c ON uf.company_id = c.id
                 WHERE uf.id = %s
                """,
                (file_id,),
            )
            return cur.fetchone()
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
    except Exception:
        return []


########################################
# Workflow Tracking & Dispatcher
########################################


def get_workflow_run(workflow_run_id: int) -> dict[str, Any] | None:
    """Load workflow_run by ID.

    Returns:
        Dict with keys: id, workflow_key, status, current_stage, file_id, content_hash, ...
        None if not found or db unavailable
    """
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, workflow_key, source_channel, file_id, content_hash,
                       current_stage, status, created_at, updated_at
                FROM workflow_runs
                WHERE id = %s
                """,
                (workflow_run_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "workflow_key": row[1],
            "source_channel": row[2],
            "file_id": row[3],
            "content_hash": row[4],
            "current_stage": row[5],
            "status": row[6],
            "created_at": row[7],
            "updated_at": row[8],
        }
    except Exception:
        return None


def get_workflow_stage(workflow_run_id: int, stage_key: str) -> dict[str, Any] | None:
    """Load a specific workflow_stage_run by workflow_run_id and stage_key."""
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, stage_key, status, started_at, finished_at, message FROM workflow_stage_runs WHERE workflow_run_id = %s AND stage_key = %s",
                (workflow_run_id, stage_key),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "stage_key": row[1],
            "status": row[2],
            "started_at": row[3],
            "finished_at": row[4],
            "message": row[5],
        }
    except Exception:
        return None


def mark_stage(
    workflow_run_id: int,
    stage_key: str,
    status: str,
    message: str | None = None,
    start: bool = False,
    end: bool = False,
    update_workflow_status: bool = True,
    workflow_status_override: str | None = None,
) -> bool:
    """Insert/update workflow_stage_runs and bump workflow_runs.current_stage/status.

    Args:
        workflow_run_id: The workflow run being processed
        stage_key: Stage identifier (e.g., 'pdf_to_png', 'ocr', 'ai1', etc.)
        status: Stage status ('queued', 'running', 'succeeded', 'failed', 'skipped')
        message: Optional short message (max 200 chars recommended)
        start: If True, set started_at to NOW()
        end: If True, set finished_at to NOW()
        update_workflow_status: When False, skip updating workflow_runs.status/current_stage
        workflow_status_override: Optional explicit status to persist on workflow_runs

    Returns:
        True if successful, False otherwise
    """
    if db_cursor is None:
        return False

    try:
        with db_cursor() as cur:
            # Insert or update workflow_stage_runs
            # First check if stage already exists
            cur.execute(
                "SELECT id FROM workflow_stage_runs WHERE workflow_run_id=%s AND stage_key=%s",
                (workflow_run_id, stage_key),
            )
            existing = cur.fetchone()

            if existing:
                # Update existing stage
                stage_id = existing[0]
                updates = ["status=%s"]
                params: list[Any] = [status]

                if message is not None:
                    updates.append("message=%s")
                    params.append(message[:200] if message else None)
                if start:
                    updates.append("started_at=NOW()")
                if end:
                    updates.append("finished_at=NOW()")

                params.extend([stage_id])
                cur.execute(
                    f"UPDATE workflow_stage_runs SET {', '.join(updates)} WHERE id=%s",
                    tuple(params),
                )
            else:
                # Insert new stage
                started_at_val = "NOW()" if start else "NULL"
                finished_at_val = "NOW()" if end else "NULL"
                cur.execute(
                    f"""
                    INSERT INTO workflow_stage_runs
                    (workflow_run_id, stage_key, status, started_at, finished_at, message)
                    VALUES (%s, %s, %s, {started_at_val}, {finished_at_val}, %s)
                    """,
                    (workflow_run_id, stage_key, status, message[:200] if message else None),
                )

            # Update workflow_runs.current_stage and status
            # Map stage status to workflow status
            workflow_status = workflow_status_override
            if workflow_status is None:
                workflow_status = "running"
                if status == "failed":
                    workflow_status = "failed"
                elif status == "skipped":
                    workflow_status = "skipped"

            if update_workflow_status:
                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET current_stage=%s, status=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (stage_key, workflow_status, workflow_run_id),
                )

        return True
    except Exception:
        return False


def dispatch_workflow(workflow_run_id: int) -> bool:
    """Dispatch workflow based on workflow_key.

    Builds the correct Celery chain based on workflow_key:
    - WF1_RECEIPT → receipt processing chain (AI1-AI4 pipeline)
    - WF2_PDF_SPLIT → PDF split + credit card invoice processing chain (AI6 pipeline)

    Args:
        workflow_run_id: ID of the workflow_run to dispatch

    Returns:
        True if dispatched successfully, False otherwise
    """
    wfr = get_workflow_run(workflow_run_id)
    if not wfr:
        return False

    workflow_key = wfr.get("workflow_key")

    if not workflow_key:
        mark_stage(workflow_run_id, "dispatch", "failed", message="Workflow key is missing.")
        return False

    try:
        if workflow_key == "WF1_RECEIPT":
            # WF1: Build the new, separated task chain
            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF1 dispatched to new wf1.* chain.")
            (wf1_run_ocr.s(workflow_run_id) | wf1_run_ai_pipeline.s() | wf1_finalize.s()).apply_async()
            return True

        elif workflow_key == "WF2_PDF_SPLIT":
            # WF2: Start the PDF processing chain
            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF2 dispatched to new wf2.* chain.")
            wf2_prepare_pdf_pages.s(workflow_run_id).apply_async()
            return True

        elif workflow_key == "WF3_FIRSTCARD_INVOICE":
            # WF3: Start the FirstCard invoice processing chain
            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF3 dispatched to new wf3.* chain.")
            wf3_firstcard_invoice.s(workflow_run_id).apply_async()
            return True

        else:
            # Unknown workflow_key
            mark_stage(
                workflow_run_id,
                "dispatch",
                "failed",
                message=f"Unknown workflow_key: {workflow_key}",
            )
            return False

    except Exception as e:
        mark_stage(workflow_run_id, "dispatch", "failed", message=f"Dispatch exception: {e}")
        return False


def ensure_workflow(workflow_run_id: int, expected_prefix: str) -> dict[str, Any]:
    """
    Guard to ensure a task is running in the correct workflow.

    Fetches the workflow_run and verifies its workflow_key starts with the
    expected prefix. If it mismatches, it logs a 'skipped' stage and raises
    an error to stop the task.

    Args:
        workflow_run_id: The ID of the current workflow run.
        expected_prefix: The required prefix for the workflow_key (e.g., "WF1_").

    Returns:
        The workflow run dictionary if validation passes.

    Raises:
        RuntimeError: If the workflow_key does not match the expected prefix.
    """
    wfr = get_workflow_run(workflow_run_id)
    if not wfr:
        # This case is unlikely if the dispatcher is correct, but it's a safeguard.
        raise ValueError(f"Workflow run {workflow_run_id} not found.")

    workflow_key = wfr.get("workflow_key", "")
    if not workflow_key.startswith(expected_prefix):
        task_name = "unknown_task"
        try:
            # Try to get the current task's name for better logging
            from celery import current_task
            if current_task:
                task_name = current_task.name
        except Exception:
            pass

        message = (
            f"Task '{task_name}' belongs to '{expected_prefix}' "
            f"but was triggered by workflow '{workflow_key}' ({workflow_run_id})."
        )
        mark_stage(
            workflow_run_id=workflow_run_id,
            stage_key="guard",
            status="skipped",
            message=message,
        )
        raise RuntimeError("Workflow/task mismatch.")

    return wfr


########################################
# Workflow Tasks
########################################


@celery_app.task(name="wf1.run_ocr")
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

    mark_stage(workflow_run_id, "ocr", "running", start=True)
    start_time = time.time()

    result: dict[str, Any] | None = None
    error_msg: str | None = None

    try:
        result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"

    elapsed = int((time.time() - start_time) * 1000)

    if result:
        _update_file_fields(file_id, ocr_raw=result.get("text"))
        text_len = len(result.get("text", ""))
        message = f"OCR succeeded, extracted {text_len} chars in {elapsed}ms."
        mark_stage(workflow_run_id, "ocr", "succeeded", message=message, end=True)
    else:
        message = f"OCR failed: {error_msg or 'OCR returned no results'}"
        mark_stage(workflow_run_id, "ocr", "failed", message=message, end=True)
        # Do not raise an exception, allow the workflow to be inspected.
        # A failed stage will already halt the workflow chain by default.

    return workflow_run_id


@celery_app.task(name="wf1.run_ai_pipeline")
def wf1_run_ai_pipeline(workflow_run_id: int) -> int:
    """
    Workflow 1: AI Pipeline Task (AI1-AI4).

    - Ensures the task is part of a WF1 workflow.
    - Marks the 'ai_pipeline' stage as running.
    - Executes the AI pipeline (_run_ai_pipeline).
    - Marks the 'ai_pipeline' stage as 'succeeded' or 'failed'.
    - Returns the workflow_run_id for the next task.
    """
    import time
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF1_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "ai_pipeline", "failed", message="File ID missing in workflow run.")
        raise ValueError("File ID is missing.")

    # Check if previous stage succeeded
    ocr_stage = get_workflow_stage(workflow_run_id, "ocr")
    if not ocr_stage or ocr_stage.get('status') != 'succeeded':
        mark_stage(workflow_run_id, "ai_pipeline", "skipped", message="Skipping AI pipeline because OCR stage did not succeed.")
        return workflow_run_id

    mark_stage(workflow_run_id, "ai_pipeline", "running", start=True)
    start_time = time.time()

    try:
        steps = _run_ai_pipeline(file_id)
        elapsed = int((time.time() - start_time) * 1000)
        message = f"AI pipeline completed {len(steps)} stages in {elapsed}ms: {', '.join(steps)}"
        mark_stage(workflow_run_id, "ai_pipeline", "succeeded", message=message, end=True)
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        message = f"AI pipeline failed after {elapsed}ms: {error_msg}"
        mark_stage(workflow_run_id, "ai_pipeline", "failed", message=message, end=True)
        # Do not re-raise, let the workflow system handle the failed state.

    return workflow_run_id


@celery_app.task(name="wf1.finalize")
def wf1_finalize(workflow_run_id: int) -> int:
    """
    Workflow 1: Finalize Task.

    - Ensures the task is part of a WF1 workflow.
    - Marks the 'finalize' stage as running.
    - Checks the status of previous stages.
    - Marks the entire workflow run as 'succeeded' or 'failed'.
    - Returns the workflow_run_id.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF1_")

    mark_stage(workflow_run_id, "finalize", "running", start=True)

    # Check status of the AI pipeline stage
    ai_stage = get_workflow_stage(workflow_run_id, "ai_pipeline")
    
    final_status = "succeeded"
    message = "Workflow completed successfully."

    if not ai_stage or ai_stage.get('status') != 'succeeded':
        final_status = "failed"
        message = "Workflow failed because a critical stage (ai_pipeline) did not succeed."

    # Update the main workflow_run status
    if db_cursor:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE workflow_runs SET status=%s, updated_at=NOW() WHERE id=%s",
                    (final_status, workflow_run_id),
                )
        except Exception as e:
            message = f"Finalize failed to update workflow status: {e}"
            final_status = "failed"


    mark_stage(
        workflow_run_id,
        "finalize",
        final_status,
        message=message,
        end=True,
        workflow_status_override=final_status,
    )

    return workflow_run_id


@celery_app.task(name="wf2.prepare_pdf_pages")
def wf2_prepare_pdf_pages(workflow_run_id: int) -> int:
    """
    Workflow 2: Prepare PDF Pages Task.
    - Splits the source PDF into individual PNG pages.
    - Creates a unified_file record for each page.
    - Triggers the parallel OCR tasks for each page.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "prepare_pages", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "prepare_pages", "running", start=True)

    parent_info = _load_unified_file_info(file_id) or {}
    mime_type = str(parent_info.get("mime_type") or "").lower()
    file_type = str(parent_info.get("file_type") or "").lower()
    if mime_type and mime_type != "application/pdf":
        message = f"Unsupported mime_type for WF2: {mime_type}"
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=message, end=True)
        raise ValueError(message)
    if not mime_type and file_type not in {"pdf", "invoice"}:
        message = f"Unsupported file_type for WF2: {file_type or 'unknown'}"
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=message, end=True)
        raise ValueError(message)

    storage_dir = os.getenv("STORAGE_DIR", "/data/storage")
    fs = FileStorage(storage_dir)

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

        data = original_path.read_bytes()
        safe_filename = original_filename or original_path.name

        converted_root = (fs.base / "converted" / file_id).resolve()
        converted_root.mkdir(parents=True, exist_ok=True)

        # Convert PDF to PNG pages
        pages = pdf_to_png_pages(data, converted_root, file_id, dpi=300)
        if not pages:
            raise RuntimeError("PDF conversion resulted in no pages.")

        page_refs = []
        for page in pages:
            page_number = page.index + 1
            page_id = str(uuid.uuid4())
            page_hash = hashlib.sha256(page.bytes).hexdigest()

            insert_unified_file(
                file_id=page_id,
                file_type="pdf_page",
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
                    "detected_kind": "pdf_page",
                    "page_number": page_number,
                    "source_pdf": file_id,
                },
            )

            stored_page_name = f"page-{page_number:04d}.png"
            fs.adopt(page_id, stored_page_name, page.path)
            page_refs.append({"file_id": page_id, "page_number": page_number})

        # Update the parent PDF unified_file with page info
        other_data = dict(parent_info.get("other_data", {}) or {})
        other_data.update({"page_count": len(page_refs), "pages": page_refs})
        update_other_data(file_id, other_data)

        mark_stage(
            workflow_run_id,
            "prepare_pages",
            "succeeded",
            message=f"Split PDF into {len(page_refs)} pages.",
            end=True,
        )

        # Now, trigger the parallel OCR
        if page_refs:
            ocr_tasks = group(
                wf2_run_page_ocr.s(workflow_run_id, page["file_id"]) for page in page_refs
            )
            callback = wf2_merge_ocr_results.s(workflow_run_id)
            chord(ocr_tasks)(callback)

    except DuplicateFileError as dup_exc:
        mark_stage(
            workflow_run_id,
            "prepare_pages",
            "failed",
            message=f"Duplicate page detected: {dup_exc}",
            end=True,
        )
        raise
    except Exception as e:
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=str(e), end=True)
        raise

    return workflow_run_id


@celery_app.task(name="wf2.run_page_ocr")
def wf2_run_page_ocr(workflow_run_id: int, page_file_id: str) -> tuple[int, str, str]:
    """
    Workflow 2: OCR Task for a single page.
    - Runs OCR and returns the text.
    """
    import time
    ensure_workflow(workflow_run_id, expected_prefix="WF2_")

    page_info = _load_unified_file_info(page_file_id)
    page_number = page_info.get("other_data", {}).get("page_number", "unknown") if page_info else "unknown"
    stage_key = f"ocr_page_{page_number}"

    mark_stage(workflow_run_id, stage_key, "running", start=True)
    start_time = time.time()

    result: dict[str, Any] | None = None
    error_msg: str | None = None
    text = ""

    try:
        result = run_ocr(page_file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"

    elapsed = int((time.time() - start_time) * 1000)

    if result:
        text = result.get("text", "")
        _update_file_fields(page_file_id, ocr_raw=text)
        message = f"OCR succeeded for page {page_number}, extracted {len(text)} chars in {elapsed}ms."
        mark_stage(workflow_run_id, stage_key, "succeeded", message=message, end=True)
    else:
        message = f"OCR failed for page {page_number}: {error_msg or 'OCR returned no results'}"
        mark_stage(workflow_run_id, stage_key, "failed", message=message, end=True)

    return (workflow_run_id, page_file_id, text)


@celery_app.task(name="wf2.merge_ocr_results")
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

    # Trigger the next step
    wf2_run_invoice_analysis.s(workflow_run_id).apply_async()

    return workflow_run_id


@celery_app.task(name="wf2.run_invoice_analysis")
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

        # Trigger finalization
        wf2_finalize.s(workflow_run_id).apply_async()

    except Exception as e:
        mark_stage(workflow_run_id, "invoice_analysis", "failed", message=str(e), end=True)
        raise

    return workflow_run_id


@celery_app.task(name="wf2.finalize")
def wf2_finalize(workflow_run_id: int) -> int:
    """
    Workflow 2: Finalize Task.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    mark_stage(workflow_run_id, "finalize", "running", start=True)

    analysis_stage = get_workflow_stage(workflow_run_id, "invoice_analysis")
    
    final_status = "succeeded"
    message = "Workflow completed successfully."

    if not analysis_stage or analysis_stage.get('status') != 'succeeded':
        final_status = "failed"
        message = "Workflow failed because a critical stage (invoice_analysis) did not succeed."

    if db_cursor:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE workflow_runs SET status=%s, updated_at=NOW() WHERE id=%s",
                    (final_status, workflow_run_id),
                )
        except Exception as e:
            message = f"Finalize failed to update workflow status: {e}"
            final_status = "failed"

    mark_stage(
        workflow_run_id,
        "finalize",
        final_status,
        message=message,
        end=True,
        workflow_status_override=final_status,
    )

    return workflow_run_id


@celery_app.task(name="wf3.firstcard_invoice")
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
        raise ValueError("Workflow run missing file_id")

    metadata = _load_invoice_metadata(file_id) or {}

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
        raise

    try:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.AI_PROCESSING,
            (
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
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

    transition_processing_status(
        file_id,
        InvoiceProcessingStatus.READY_FOR_MATCHING,
        (
            InvoiceProcessingStatus.AI_PROCESSING,
            InvoiceProcessingStatus.OCR_DONE,
        ),
    )
    transition_document_status(
        file_id,
        InvoiceDocumentStatus.MATCHING,
        (
            InvoiceDocumentStatus.IMPORTED,
            InvoiceDocumentStatus.MATCHING,
        ),
    )

    mark_stage(
        workflow_run_id,
        "firstcard_invoice",
        "succeeded",
        message=f"Parsed credit card invoice: main_id={main_id}, lines={items_inserted}/{inserted_invoice_lines}",
        end=True,
        workflow_status_override="succeeded",
    )
    return workflow_run_id


########################################
# AI Pipeline Functions
########################################


def _run_ai_pipeline(file_id: str) -> List[str]:
    """Run the complete AI pipeline (AI1-AI4) with detailed logging."""
    import time
    from services.ai_service import AIService

    if db_cursor is None:
        raise RuntimeError("Database unavailable for AI pipeline")

    steps: List[str] = []
    ai_service = AIService()

    context = _load_ai_context(file_id)
    if context is None:
        error_msg = f"File {file_id} not found in unified_files"
        _history(
            file_id,
            "ai_pipeline",
            "error",
            ai_stage_name="Pipeline-Initialization",
            log_text="Failed to load file context from database",
            error_message=error_msg,
        )
        raise ValueError(error_msg)
    ocr_text, document_type, expense_type = context

    # AI1 - Document Classification
    start_time = time.time()
    ai1_provider = ai_service.prompt_provider_names.get("document_analysis", "unknown")
    ai1_model = ai_service.prompt_model_names.get("document_analysis", "unknown")
    try:
        result = classify_document_internal(
            DocumentClassificationRequest(file_id=file_id, ocr_text=ocr_text or "")
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI1")

        ai1_prompt = ai_service.prompts.get("document_analysis", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Classified document as '{result.document_type}'",
            f"OCR text length: {len(ocr_text or '')} characters",
            f"--- PROMPT ---\n{ai1_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]
        if result.reasoning:
            log_parts.append(f"Reasoning: {result.reasoning}")

        _history(
            file_id,
            "ai1",
            "success",
            ai_stage_name="AI1-DocumentClassification",
            log_text="; ".join(log_parts),
            confidence=result.confidence,
            processing_time_ms=elapsed,
            provider=ai1_provider,
            model_name=ai1_model,
        )

        # Update file_type column with classified document_type
        if db_cursor is not None and result.document_type:
            try:
                with db_cursor() as cur:
                    cur.execute(
                        "UPDATE unified_files SET file_type=%s, updated_at=NOW() WHERE id=%s",
                        (result.document_type, file_id),
                    )
            except Exception:
                pass  # Best-effort update, don't fail the pipeline
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        _history(
            file_id,
            "ai1",
            "error",
            ai_stage_name="AI1-DocumentClassification",
            log_text=f"Failed to classify document type from OCR text ({len(ocr_text or '')} chars)",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai1_provider,
            model_name=ai1_model,
        )
        raise

    # Reload context after AI1
    context = _load_ai_context(file_id) or context
    ocr_text, document_type, expense_type = context

    # AI2 - Expense Classification
    start_time = time.time()
    ai2_provider = ai_service.prompt_provider_names.get("expense_classification", "unknown")
    ai2_model = ai_service.prompt_model_names.get("expense_classification", "unknown")
    try:
        result = classify_expense_internal(
            ExpenseClassificationRequest(
                file_id=file_id,
                ocr_text=ocr_text or "",
                document_type=document_type or "other",
            )
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI2")

        ai2_prompt = ai_service.prompts.get("expense_classification", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Classified expense as '{result.expense_type}'",
            f"Document type: {document_type or 'other'}",
            f"--- PROMPT ---\n{ai2_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]
        if result.card_identifier:
            log_parts.append(f"Card identifier: {result.card_identifier}")
        if result.reasoning:
            log_parts.append(f"Reasoning: {result.reasoning}")

        _history(
            file_id,
            "ai2",
            "success",
            ai_stage_name="AI2-ExpenseClassification",
            log_text="; ".join(log_parts),
            confidence=result.confidence,
            processing_time_ms=elapsed,
            provider=ai2_provider,
            model_name=ai2_model,
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        _history(
            file_id,
            "ai2",
            "error",
            ai_stage_name="AI2-ExpenseClassification",
            log_text=f"Failed to classify expense type for document_type='{document_type}'",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai2_provider,
            model_name=ai2_model,
        )
        raise

    # Reload context after AI2
    context = _load_ai_context(file_id) or context
    ocr_text, document_type, expense_type = context

    # AI3 - Data Extraction
    start_time = time.time()
    ai3_provider = ai_service.prompt_provider_names.get("data_extraction", "unknown")
    ai3_model = ai_service.prompt_model_names.get("data_extraction", "unknown")
    try:
        result = extract_data_internal(
            DataExtractionRequest(
                file_id=file_id,
                ocr_text=ocr_text or "",
                document_type=document_type or "other",
                expense_type=expense_type or "personal",
            )
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI3")

        # Comprehensive extraction logging - include ALL fields
        extracted = []
        if result.unified_file:
            uf = result.unified_file
            # Financial data
            if uf.gross_amount_original:
                extracted.append(f"gross={uf.gross_amount_original}")
            if uf.net_amount_original:
                extracted.append(f"net={uf.net_amount_original}")
            if uf.gross_amount_sek:
                extracted.append(f"gross_sek={uf.gross_amount_sek}")
            if uf.net_amount_sek:
                extracted.append(f"net_sek={uf.net_amount_sek}")
            if uf.currency:
                extracted.append(f"currency={uf.currency}")
            if uf.exchange_rate:
                extracted.append(f"exchange_rate={uf.exchange_rate}")
            # Business data
            if uf.orgnr:
                extracted.append(f"orgnr={uf.orgnr}")
            if uf.purchase_datetime:
                extracted.append(f"purchase_date={uf.purchase_datetime}")
            if uf.payment_type:
                extracted.append(f"payment_type={uf.payment_type}")
            if uf.expense_type:
                extracted.append(f"expense_type={uf.expense_type}")
            if uf.receipt_number:
                extracted.append(f"receipt_number={uf.receipt_number}")

        item_count = len(result.receipt_items or [])

        # Detailed company extraction logging
        company_details = []
        if result.company:
            if result.company.name:
                company_details.append(f"name='{result.company.name}'")
            if result.company.orgnr:
                company_details.append(f"orgnr='{result.company.orgnr}'")
            if result.company.address:
                company_details.append(f"address='{result.company.address}'")
            if result.company.city:
                company_details.append(f"city='{result.company.city}'")
            if result.company.zip:
                company_details.append(f"zip='{result.company.zip}'")
            if result.company.country:
                company_details.append(f"country='{result.company.country}'")

        # Receipt items summary
        items_summary = []
        if result.receipt_items and len(result.receipt_items) > 0:
            for idx, item in enumerate(result.receipt_items[:3], 1):  # Show first 3 items
                items_summary.append(f"{item.name}@{item.item_total_price_inc_vat}")
            if len(result.receipt_items) > 3:
                items_summary.append(f"... +{len(result.receipt_items) - 3} more")

        ai3_prompt = ai_service.prompts.get("data_extraction", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Extracted data: {', '.join(extracted) if extracted else 'NO DATA'}",
            f"--- PROMPT ---\n{ai3_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]
        if company_details:
            log_parts.append(f"Company: {'; '.join(company_details)}")
        else:
            log_parts.append("Company: NO COMPANY DATA EXTRACTED")

        # Critical: Warn if no receipt_items were extracted
        if item_count == 0:
            log_parts.append("WARNING: 0 receipt_items extracted from LLM - check prompt and LLM response!")
        else:
            log_parts.append(f"Items: {item_count} total")
            if items_summary:
                log_parts.append(f"Sample items: [{', '.join(items_summary)}]")

        _history(
            file_id,
            "ai3",
            "success",
            ai_stage_name="AI3-DataExtraction",
            log_text="; ".join(log_parts),
            confidence=result.confidence,
            processing_time_ms=elapsed,
            provider=ai3_provider,
            model_name=ai3_model,
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        _history(
            file_id,
            "ai3",
            "error",
            ai_stage_name="AI3-DataExtraction",
            log_text=f"Failed to extract structured data from document_type='{document_type}', expense_type='{expense_type}'",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai3_provider,
            model_name=ai3_model,
        )
        raise

    # AI4 - Accounting Classification
    accounting_inputs = _load_accounting_inputs(file_id)
    if accounting_inputs:
        gross, net, vat_amount, vendor_name = accounting_inputs
        receipt_items = _load_receipt_items(file_id)
        start_time = time.time()
        ai4_provider = ai_service.prompt_provider_names.get("accounting_classification", "unknown")
        ai4_model = ai_service.prompt_model_names.get("accounting_classification", "unknown")
        try:
            result = classify_accounting_internal(
                AccountingClassificationRequest(
                    file_id=file_id,
                    document_type=document_type or "other",
                    expense_type=expense_type or "personal",
                    gross_amount=Decimal(str(gross or 0)),
                    net_amount=Decimal(str(net or 0)),
                    vat_amount=Decimal(str(vat_amount or 0)),
                    vendor_name=vendor_name or "",
                    receipt_items=receipt_items,
                )
            )
            elapsed = int((time.time() - start_time) * 1000)
            steps.append("AI4")

            proposal_count = len(result.proposals or [])

            # Add detailed proposal breakdown
            proposal_details = []
            for proposal in (result.proposals or [])[:5]:  # Show first 5 proposals
                proposal_details.append(
                    f"account={proposal.account_code}, "
                    f"debit={proposal.debit}, credit={proposal.credit}"
                )
            if len(result.proposals or []) > 5:
                proposal_details.append(f"... +{len(result.proposals) - 5} more")

            ai4_prompt = ai_service.prompts.get("accounting_classification", "")
            raw_response = ai_service.last_raw_response or ""
            log_parts = [
                f"Generated {proposal_count} accounting proposals",
                f"Vendor: {vendor_name or 'N/A'}",
                f"Amounts: gross={gross}, net={net}, vat={vat_amount}",
                f"--- PROMPT ---\n{ai4_prompt}",
                f"--- RAW RESPONSE ---\n{raw_response}",
            ]
            if result.based_on_bas2025:
                log_parts.append("Based on BAS 2025 chart of accounts")
            if proposal_details:
                log_parts.append(f"Proposals: [{'; '.join(proposal_details)}]")

            _history(
                file_id,
                "ai4",
                "success",
                ai_stage_name="AI4-AccountingClassification",
                log_text="; ".join(log_parts),
                confidence=result.confidence,
                processing_time_ms=elapsed,
                provider=ai4_provider,
                model_name=ai4_model,
            )
        except Exception as exc:
            elapsed = int((time.time() - start_time) * 1000)
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            _history(
                file_id,
                "ai4",
                "error",
                ai_stage_name="AI4-AccountingClassification",
                log_text=f"Failed to classify accounting for vendor='{vendor_name}', gross={gross}, net={net}, vat={vat_amount}",
                error_message=error_msg,
                processing_time_ms=elapsed,
                provider=ai4_provider,
                model_name=ai4_model,
            )
            raise
    else:
        _history(
            file_id,
            "ai4",
            "skipped",
            ai_stage_name="AI4-AccountingClassification",
            log_text="Skipped: No accounting inputs available (missing gross_amount_sek, net_amount_sek, or company_id)",
        )

    return steps


def _infer_document_type(
    file_type: Optional[str],
    merchant: Optional[str],
    tags: List[str],
    text_blob: str,
    company_card: bool,
) -> str:
    if company_card:
        return "receipt"
    ft = (file_type or "").lower()
    if ft:
        if any(token in ft for token in ("receipt", "expense", "company_card")):
            return "receipt"
        if any(token in ft for token in ("invoice", "supplier", "statement")):
            return "invoice"
    tags_lower = {t.lower() for t in (tags or [])}
    if tags_lower & {"receipt", "expense", "meal", "travel"}:
        return "receipt"
    if tags_lower & {"invoice", "statement", "supplier"}:
        return "invoice"
    text = " ".join(filter(None, [merchant or "", text_blob])).lower()
    invoice_keywords = [
        "invoice", "due date", "pay by", "bankgiro", "plusgiro", "ocr", "statement"
    ]
    for kw in invoice_keywords:
        if kw in text:
            return "invoice"
    receipt_keywords = [
        "receipt", "thank you", "cashier", "order", "sale total", "subtotal", "vat"
    ]
    for kw in receipt_keywords:
        if kw in text:
            return "receipt"
    return "other"


def _rules_file() -> Path:
    return Path(os.getenv("RULES_FILE", "/data/storage/rules.json"))


def _load_rules() -> List[AccountingRule]:
    path = _rules_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    rules: List[AccountingRule] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        matcher = str(item.get("matcher") or "").strip()
        account = str(item.get("account") or "").strip()
        if not matcher or not account:
            continue
        rules.append(
            AccountingRule(
                id=item.get("id"),
                name=str(item.get("note") or matcher),
                condition_type="merchant_contains",
                condition_value=matcher,
                account_code=account,
                vat_account_code=None,
            )
        )
    return rules


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
    except Exception:
        return False





























