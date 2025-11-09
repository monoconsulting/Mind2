from __future__ import annotations

from decimal import Decimal
import sys
from typing import Any, Callable, List, TypeVar

from models.ai_processing import CreditCardInvoiceExtractionRequest

from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    transition_document_status as _transition_document_status,
    transition_processing_status as _transition_processing_status,
)

from .base import celery_app, db_cursor
from .creditcard_tasks import _persist_creditcard_invoice_items, _persist_creditcard_invoice_main
from .utils.invoice_utils import (
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_metadata,
    _persist_invoice_lines,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)

_CallableT = TypeVar("_CallableT", bound=Callable[..., Any])


def _resolve_transition_processing_status() -> Callable[[str, InvoiceProcessingStatus, tuple[InvoiceProcessingStatus, ...]], bool]:
    tasks_module = sys.modules.get("services.tasks")
    if tasks_module is not None:
        func = getattr(tasks_module, "transition_processing_status", None)
        if callable(func):
            return func  # type: ignore[return-value]
    return _transition_processing_status


def _resolve_transition_document_status() -> Callable[[str, InvoiceDocumentStatus, tuple[InvoiceDocumentStatus, ...]], bool]:
    tasks_module = sys.modules.get("services.tasks")
    if tasks_module is not None:
        func = getattr(tasks_module, "transition_document_status", None)
        if callable(func):
            return func  # type: ignore[return-value]
    return _transition_document_status


def _resolve_tasks_callable(name: str, fallback: _CallableT) -> _CallableT:
    tasks_module = sys.modules.get("services.tasks")
    if tasks_module is not None:
        candidate = getattr(tasks_module, name, None)
        if callable(candidate):
            return candidate  # type: ignore[return-value]
    return fallback


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


def _enqueue_invoice_document(invoice_id: str) -> bool:
    tasks_module = sys.modules.get("services.tasks")
    task: Any | None = None
    if tasks_module is not None:
        candidate = getattr(tasks_module, "process_invoice_ai_extraction", None)
        if callable(candidate) or hasattr(candidate, "delay"):
            task = candidate
    if task is None:
        task = process_invoice_document
    try:
        if hasattr(task, "delay"):
            task.delay(invoice_id)  # type: ignore[attr-defined]
        else:
            task(invoice_id)  # type: ignore[misc]
        return True
    except Exception:
        return False


@celery_app.task(name="process_invoice_document")
def process_invoice_document(invoice_id: str) -> dict[str, Any]:
    """Legacy-compatible processing entrypoint for credit card invoices."""

    metadata = _load_invoice_metadata(invoice_id) or {}
    transition_processing_status_fn = _resolve_transition_processing_status()
    transition_document_status_fn = _resolve_transition_document_status()
    try:
        transition_processing_status_fn(
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
        transition_processing_status_fn(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status_fn(
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
        transition_processing_status_fn(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status_fn(
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
        transition_processing_status_fn(
            invoice_id,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
            ),
        )
        transition_document_status_fn(
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


def _maybe_advance_invoice_from_file(file_id: str, success: bool) -> None:
    get_parent = _resolve_tasks_callable("_get_invoice_parent_id", _get_invoice_parent_id)
    invoice_id = get_parent(file_id, None)
    if not invoice_id:
        return

    load_metadata = _resolve_tasks_callable("_load_invoice_metadata", _load_invoice_metadata)
    update_metadata = _resolve_tasks_callable("_update_invoice_metadata", _update_invoice_metadata)
    set_field = _resolve_tasks_callable("_set_invoice_metadata_field", _set_invoice_metadata_field)
    enqueue_document = _resolve_tasks_callable("_enqueue_invoice_document", _enqueue_invoice_document)

    metadata = load_metadata(invoice_id) or {}
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

    progress_fn = _resolve_tasks_callable("_invoice_page_progress", _invoice_page_progress)
    try:
        progress_result = progress_fn(invoice_id, metadata)
    except TypeError:
        progress_result = progress_fn(invoice_id)
    if isinstance(progress_result, dict):
        progress = {
            "completed": int(progress_result.get("completed", 0) or 0),
            "total": int(progress_result.get("total", 0) or 0),
        }
    elif (
        isinstance(progress_result, tuple)
        and len(progress_result) >= 2
        and all(isinstance(value, (int, float)) for value in progress_result[:2])
    ):
        progress = {
            "completed": int(progress_result[0]),
            "total": int(progress_result[1]),
        }
    else:
        progress = {"completed": 0, "total": 0}

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

    update_metadata(invoice_id, metadata)
    transition_processing_status_fn = _resolve_transition_processing_status()
    transition_processing_status_fn(invoice_id, next_state, allowed_states)

    if should_schedule and enqueue_document(invoice_id):
        set_field(invoice_id, "invoice_document_scheduled", True)


__all__ = [
    "process_invoice_document",
    "_load_invoice_file_records",
    "_collect_invoice_ocr_text",
    "_enqueue_invoice_document",
    "_maybe_advance_invoice_from_file",
]
