from __future__ import annotations

import logging

from observability.events import log_event
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)

from ..common import set_ai_status
from .invoice_utils import (
    _enqueue_invoice_document,
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_metadata,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)

logger = logging.getLogger(__name__)


def _move_to_manual_review(file_id: str, reason: str | None = None) -> None:
    """Best-effort helper that marks a file as requiring manual review."""

    try:
        set_ai_status(file_id, "manual_review")
    except Exception:
        logger.debug("Failed to set manual review status for %s", file_id)
    if reason:
        log_event(logger, "ai.manual_review", file_id=file_id, reason=reason)


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

    if success:
        try:
            transition_document_status(
                invoice_id,
                InvoiceDocumentStatus.PROCESSING,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.PROCESSING,
                    InvoiceDocumentStatus.MATCHING,
                ),
            )
        except Exception:
            logger.debug("Failed to transition document %s after OCR", invoice_id)

    if should_schedule and _enqueue_invoice_document(invoice_id):
        _set_invoice_metadata_field(invoice_id, "invoice_document_scheduled", True)

__all__ = ["_move_to_manual_review", "_maybe_advance_invoice_from_file"]
