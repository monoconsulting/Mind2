from __future__ import annotations

from decimal import Decimal
from typing import Any

from models.ai_processing import CreditCardInvoiceExtractionRequest
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)

from .base import db_cursor
from .creditcard_tasks import (
    _persist_creditcard_invoice_items,
    _persist_creditcard_invoice_main,
)
from .utils.invoice_utils import (
    _collect_invoice_ocr_text,
    _load_invoice_metadata,
    _update_invoice_metadata,
)


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

    extraction = ai_service.parse_credit_card_invoice(request)

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


__all__ = [
    "process_invoice_document",
    "_persist_invoice_lines",
]
