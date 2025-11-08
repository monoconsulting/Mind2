from __future__ import annotations

from typing import Any

from importlib import import_module

from ...invoice_status import InvoiceProcessingStatus, transition_processing_status
from .invoice_utils import (
    _invoice_page_progress,
    _load_invoice_metadata,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from .metadata_utils import _get_invoice_parent_id


def _get_db_cursor():
    module = import_module("services.tasks")
    return getattr(module, "db_cursor", None)


def _update_file_status(file_id: str, status: str, confidence: float | None = None) -> bool:
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
        return False
    try:
        with cursor_factory() as cur:
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


def _enqueue_invoice_document(invoice_id: str) -> bool:
    try:
        from ..invoice_tasks import process_invoice_document
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

    completed_pages, total_pages = _invoice_page_progress(invoice_id, metadata)
    metadata["ocr_completed_pages"] = completed_pages
    existing_count = metadata.get("page_count")
    if isinstance(existing_count, int) and existing_count > 0:
        metadata["page_count"] = max(existing_count, total_pages)
    else:
        metadata["page_count"] = total_pages

    should_schedule = False
    if success and total_pages > 0 and completed_pages >= total_pages:
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


__all__ = [
    "_update_file_status",
    "_maybe_advance_invoice_from_file",
    "_enqueue_invoice_document",
]
