"""Central status definitions for invoice-related entities.

This module defines the allowed states for:
- invoice_documents.processing_status
- invoice_documents.status
- invoice_lines.match_status

These constants must match the values in the database and the documentation:
- docs/FIRSTCARD_STATUS_FLOW.md
- docs/MIND_STATUS_DEFINITIONS.md
"""

from enum import Enum


class InvoiceProcessingStatus(str, Enum):
    """Technical processing states for ``invoice_documents``."""

    UPLOADED = "uploaded"
    OCR_PENDING = "ocr_pending"
    OCR_DONE = "ocr_done"
    AI_PROCESSING = "ai_processing"
    READY_FOR_MATCHING = "ready_for_matching"
    MATCHING_COMPLETED = "matching_completed"
    COMPLETED = "completed"
    FAILED = "failed"


class InvoiceDocumentStatus(str, Enum):
    """Business lifecycle states exposed to end users."""

    IMPORTED = "imported"
    MATCHING = "matching"
    MATCHED = "matched"
    PARTIALLY_MATCHED = "partially_matched"
    PROCESSING = "processing"  # TODO(status-alignment): Legacy status, verify usage
    COMPLETED = "completed"
    FAILED = "failed"


class InvoiceLineMatchStatus(str, Enum):
    """Per-line reconciliation states."""

    PENDING = "pending"
    AUTO = "auto"
    MANUAL = "manual"
    CONFIRMED = "confirmed"
    UNMATCHED = "unmatched"
    IGNORED = "ignored"


class AiStatus(str, Enum):
    """Unified file AI processing states."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    OCR_DONE = "ocr_done"
    OCR_FAILED = "ocr_failed"
    MANUAL_REVIEW = "manual_review"
    COMPLETED = "completed"
    FAILED = "failed"
