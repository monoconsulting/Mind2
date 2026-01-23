from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from .common import (
    CreditCardInvoiceExtractionRequest,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    db_cursor,
    transition_document_status,
    transition_processing_status,
)
from .utils.invoice_utils import (
    _collect_invoice_ocr_text,
    _load_invoice_metadata,
    _update_invoice_metadata,
)
from .common import InvoiceLineMatchStatus

logger = logging.getLogger(__name__)

def process_invoice_document(invoice_id: str) -> dict[str, Any]:
    """Legacy-compatible processing entrypoint for credit card invoices."""
    metadata = _load_invoice_metadata(invoice_id) or {}
    try:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.AI_PROCESSING,
            (
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
    except Exception:
        pass

    ocr_entries = _collect_invoice_ocr_text(invoice_id)
    combined_text = "\n".join(text for _, text in ocr_entries if text)
    if not combined_text.strip():
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.PROCESSING,
            ),
        )
        raise ValueError("Combined OCR text is missing.")

    page_ids = [file_id for file_id, _ in ocr_entries if file_id != invoice_id]
    if page_ids:
        metadata.setdefault("page_ids", page_ids)
        metadata.setdefault("page_count", len(page_ids))
    metadata["combined_ocr_text"] = combined_text
    _update_invoice_metadata(invoice_id, metadata)

    from services.ai_service import AIService

    ai_service = AIService()
    request = CreditCardInvoiceExtractionRequest(
        invoice_id=invoice_id,
        ocr_text=combined_text,
        page_ids=page_ids,
    )

    extraction = ai_service.run_ai6_credit_card_invoice_parsing(request)

    main_id = _persist_creditcard_invoice_main(invoice_id, extraction.header, combined_text)
    if not main_id:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        raise RuntimeError("Failed to persist credit card invoice header")

    _persist_creditcard_invoice_items(main_id, extraction.lines)

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
                "currency_original": line.currency_original,
                "amount_original": line.amount_original,
                "exchange_rate": line.exchange_rate,
                "amount_sek": line.amount_sek,
                "confidence": line.confidence,
                "raw_text": line.source_text or "",
            }
        )

    inserted_invoice_lines = _persist_invoice_lines(invoice_id, invoice_line_payloads)

    metadata = _load_invoice_metadata(invoice_id) or {}
    metadata["creditcard_main_id"] = main_id
    metadata["overall_confidence"] = extraction.overall_confidence
    metadata["invoice_summary"] = {
        "invoice_number": extraction.header.invoice_number,
        "card_holder": extraction.header.card_holder,
        "card_number_masked": extraction.header.card_number_masked,
        "currency": extraction.header.currency,
        "period_start": extraction.header.period_start.isoformat() if hasattr(extraction.header.period_start, "isoformat") else None,
        "period_end": extraction.header.period_end.isoformat() if hasattr(extraction.header.period_end, "isoformat") else None,
    }
    metadata["line_counts"] = {
        "total": inserted_invoice_lines,
        "matched": 0,
        "unmatched": inserted_invoice_lines,
    }
    _update_invoice_metadata(invoice_id, metadata)

    try:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
            ),
        )
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.MATCHING,
            (
                InvoiceDocumentStatus.PROCESSING,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.IMPORTED,
            ),
        )
    except Exception:
        pass

    return {
        "ok": True,
        "status": InvoiceProcessingStatus.READY_FOR_MATCHING.value,
        "lines": inserted_invoice_lines,
        "creditcard_main_id": main_id,
        "confidence": extraction.overall_confidence,
    }

def _persist_invoice_lines(invoice_id: str, parsed_lines: list[dict[str, Any]]) -> int:
    if db_cursor is None:
        return 0
    inserted = 0
    try:
        with db_cursor() as cur:
            # When re-importing (resume/restart), clear any history rows first.
            # invoice_line_history.invoice_line_id has an FK to invoice_lines.id, so deleting
            # invoice_lines directly can fail if history exists.
            cur.execute(
                """
                DELETE FROM invoice_line_history
                 WHERE invoice_line_id IN (
                   SELECT id FROM invoice_lines WHERE invoice_id=%s
                 )
                """,
                (invoice_id,),
            )
            cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
            for line in parsed_lines:
                try:
                    amount = Decimal(str(line.get("amount", 0))).quantize(Decimal("0.01"))
                except Exception:
                    amount = Decimal("0.00")
                try:
                    amount_original = line.get("amount_original")
                    amount_original = Decimal(str(amount_original)).quantize(Decimal("0.01")) if amount_original is not None else None
                except Exception:
                    amount_original = None
                try:
                    amount_sek = line.get("amount_sek")
                    amount_sek = Decimal(str(amount_sek)).quantize(Decimal("0.01")) if amount_sek is not None else None
                except Exception:
                    amount_sek = None
                try:
                    exchange_rate = line.get("exchange_rate")
                    exchange_rate = Decimal(str(exchange_rate)) if exchange_rate is not None else None
                except Exception:
                    exchange_rate = None
                currency_original = line.get("currency_original")
                if isinstance(currency_original, str):
                    currency_original = currency_original.strip().upper() or None
                else:
                    currency_original = None

                if not currency_original:
                    currency_original = "SEK"

                if currency_original == "SEK":
                    if amount_sek is None:
                        amount_sek = amount
                    if amount_original is None:
                        amount_original = amount_sek
                    if exchange_rate is None:
                        exchange_rate = Decimal("0")
                else:
                    if amount_sek is None:
                        amount_sek = amount
                    if exchange_rate is None and amount_sek is not None and amount_original not in (None, 0):
                        try:
                            exchange_rate = (amount_sek / amount_original).quantize(Decimal("0.000001"))
                        except Exception:
                            exchange_rate = None
                transaction_date = line.get("transaction_date")
                merchant_name = line.get("merchant_name") or line.get("description") or ""
                description = line.get("description") or merchant_name
                confidence = line.get("confidence")
                ocr_text = line.get("raw_text") or ""
                cur.execute(
                    (
                        "INSERT INTO invoice_lines "
                        "(invoice_id, transaction_date, amount, currency_original, amount_original, exchange_rate, amount_sek, "
                        "merchant_name, description, match_status, extraction_confidence, ocr_source_text) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        invoice_id,
                        transaction_date,
                        amount,
                        currency_original,
                        amount_original,
                        exchange_rate,
                        amount_sek,
                        merchant_name,
                        description,
                        InvoiceLineMatchStatus.PENDING.value,
                        confidence,
                        ocr_text,
                    ),
                )
                inserted += 1
    except Exception:
        logger.exception(
            "Failed to persist invoice_lines for invoice_id=%s; transaction rolled back",
            invoice_id,
        )
        return 0
    return inserted

def _count_invoice_lines(invoice_id: str) -> int:
    """Count persisted invoice lines for a credit-card invoice.

    Args:
        invoice_id: The ``invoice_documents.id`` / ``invoice_lines.invoice_id`` to count.

    Returns:
        Number of rows in ``invoice_lines`` for this invoice, or 0 if DB is unavailable.
    """
    if db_cursor is None:
        return 0
    try:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(1) FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0
    except Exception as exc:
        logger.exception("Failed to count invoice_lines for invoice_id=%s: %s", invoice_id, exc)
        return 0

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

__all__ = [
    "process_invoice_document",
    "_persist_invoice_lines",
    "_count_invoice_lines",
    "_to_decimal",
    "_format_date_for_db",
    "_persist_creditcard_invoice_ocr",
    "_persist_creditcard_invoice_main",
    "_persist_creditcard_invoice_items",
]
