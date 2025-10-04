"""Invoice processing state machine helpers.

This module centralises the lifecycle rules for invoice processing.

There are three parallel state machines:

* ``invoice_documents.processing_status`` tracks the technical pipeline
  (upload, OCR, AI extraction, matching, completion, failure).
* ``invoice_documents.status`` represents the business-facing state shown
  to users (imported, matched, completed, failed, etc.).
* ``invoice_lines.match_status`` captures progress for individual
  transaction lines (pending, auto, manual, confirmed, unmatched).

Each transition is validated and executed atomically in the database using
``WHERE`` clauses that assert the current state. If the row update fails the
helper records an observability metric and logs a warning. This protects the
pipeline from accidental regressions or race conditions where two workers try
 to update the same document concurrently.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Iterable

try:  # pragma: no cover - imported lazily during tests
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

from observability.metrics import record_invoice_state_assertion


logger = logging.getLogger(__name__)


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


# Allowed transitions expressed as ``current -> {next}``
PROCESSING_TRANSITIONS: dict[InvoiceProcessingStatus, set[InvoiceProcessingStatus]] = {
    InvoiceProcessingStatus.UPLOADED: {
        InvoiceProcessingStatus.OCR_PENDING,
        InvoiceProcessingStatus.READY_FOR_MATCHING,  # manual JSON import can skip OCR
        InvoiceProcessingStatus.FAILED,
    },
    InvoiceProcessingStatus.OCR_PENDING: {
        InvoiceProcessingStatus.OCR_DONE,
        InvoiceProcessingStatus.FAILED,
    },
    InvoiceProcessingStatus.OCR_DONE: {
        InvoiceProcessingStatus.AI_PROCESSING,
        InvoiceProcessingStatus.READY_FOR_MATCHING,  # allow direct fallback when OCR already contains data
        InvoiceProcessingStatus.FAILED,
    },
    InvoiceProcessingStatus.AI_PROCESSING: {
        InvoiceProcessingStatus.READY_FOR_MATCHING,
        InvoiceProcessingStatus.FAILED,
    },
    InvoiceProcessingStatus.READY_FOR_MATCHING: {
        InvoiceProcessingStatus.MATCHING_COMPLETED,
        InvoiceProcessingStatus.FAILED,
    },
    InvoiceProcessingStatus.MATCHING_COMPLETED: {
        InvoiceProcessingStatus.COMPLETED,
    },
    InvoiceProcessingStatus.COMPLETED: set(),
    InvoiceProcessingStatus.FAILED: set(),
}

DOCUMENT_STATUS_TRANSITIONS: dict[InvoiceDocumentStatus, set[InvoiceDocumentStatus]] = {
    InvoiceDocumentStatus.IMPORTED: {
        InvoiceDocumentStatus.MATCHING,
        InvoiceDocumentStatus.MATCHED,
        InvoiceDocumentStatus.PARTIALLY_MATCHED,
        InvoiceDocumentStatus.FAILED,
    },
    InvoiceDocumentStatus.MATCHING: {
        InvoiceDocumentStatus.MATCHED,
        InvoiceDocumentStatus.PARTIALLY_MATCHED,
        InvoiceDocumentStatus.FAILED,
    },
    InvoiceDocumentStatus.MATCHED: {
        InvoiceDocumentStatus.COMPLETED,
        InvoiceDocumentStatus.PARTIALLY_MATCHED,
    },
    InvoiceDocumentStatus.PARTIALLY_MATCHED: {
        InvoiceDocumentStatus.MATCHED,
        InvoiceDocumentStatus.COMPLETED,
        InvoiceDocumentStatus.FAILED,
    },
    InvoiceDocumentStatus.COMPLETED: set(),
    InvoiceDocumentStatus.FAILED: set(),
}

LINE_STATUS_TRANSITIONS: dict[InvoiceLineMatchStatus, set[InvoiceLineMatchStatus]] = {
    InvoiceLineMatchStatus.PENDING: {
        InvoiceLineMatchStatus.AUTO,
        InvoiceLineMatchStatus.MANUAL,
        InvoiceLineMatchStatus.UNMATCHED,
        InvoiceLineMatchStatus.IGNORED,
    },
    InvoiceLineMatchStatus.AUTO: {
        InvoiceLineMatchStatus.MANUAL,
        InvoiceLineMatchStatus.CONFIRMED,
        InvoiceLineMatchStatus.UNMATCHED,
    },
    InvoiceLineMatchStatus.MANUAL: {
        InvoiceLineMatchStatus.CONFIRMED,
        InvoiceLineMatchStatus.UNMATCHED,
    },
    InvoiceLineMatchStatus.CONFIRMED: set(),
    InvoiceLineMatchStatus.UNMATCHED: {
        InvoiceLineMatchStatus.MANUAL,
    },
    InvoiceLineMatchStatus.IGNORED: {
        InvoiceLineMatchStatus.MANUAL,
    },
}


def _record_illegal(entity: str, object_id: str, target: str) -> None:
    """Log and emit metrics for illegal transitions."""

    current_value = "missing"
    if db_cursor is not None:
        column = "processing_status" if entity == "processing_status" else "status"
        if entity == "line_match_status":
            column = "match_status"
            query = "SELECT match_status FROM invoice_lines WHERE id=%s"
            params = (object_id,)
        else:
            query = f"SELECT {column} FROM invoice_documents WHERE id=%s"
            params = (object_id,)
        try:
            with db_cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
            if row:
                current_value = row[0] or "null"
        except Exception:  # pragma: no cover - defensive logging path
            logger.exception("Failed to fetch current invoice state for assertion")
    record_invoice_state_assertion(entity, current_value, target)
    logger.warning(
        "Illegal transition for %s id=%s: current=%s target=%s", entity, object_id, current_value, target
    )


def transition_processing_status(
    document_id: str,
    target: InvoiceProcessingStatus,
    allowed_from: Iterable[InvoiceProcessingStatus],
) -> bool:
    """Atomically update ``invoice_documents.processing_status``.

    Args:
        document_id: Invoice identifier.
        target: Target processing state.
        allowed_from: One or more current states that may transition into ``target``.
    """

    states = tuple(allowed_from)
    if not states:
        raise ValueError("allowed_from must contain at least one state")
    if db_cursor is None:
        return False
    placeholders = ", ".join(["%s"] * len(states))
    sql = (
        f"UPDATE invoice_documents SET processing_status=%s "
        f"WHERE id=%s AND processing_status IN ({placeholders})"
    )
    params: tuple[object, ...] = (target.value, document_id, *[state.value for state in states])
    try:
        with db_cursor() as cur:
            cur.execute(sql, params)
            if cur.rowcount:
                return True
    except Exception:
        logger.exception("Failed to update invoice processing status")
        raise
    _record_illegal("processing_status", document_id, target.value)
    return False


def transition_document_status(
    document_id: str,
    target: InvoiceDocumentStatus,
    allowed_from: Iterable[InvoiceDocumentStatus],
) -> bool:
    states = tuple(allowed_from)
    if not states:
        raise ValueError("allowed_from must contain at least one state")
    if db_cursor is None:
        return False
    placeholders = ", ".join(["%s"] * len(states))
    sql = f"UPDATE invoice_documents SET status=%s WHERE id=%s AND status IN ({placeholders})"
    params: tuple[object, ...] = (target.value, document_id, *[state.value for state in states])
    try:
        with db_cursor() as cur:
            cur.execute(sql, params)
            if cur.rowcount:
                return True
    except Exception:
        logger.exception("Failed to update invoice document status")
        raise
    _record_illegal("status", document_id, target.value)
    return False


def transition_line_status(
    line_id: int,
    target: InvoiceLineMatchStatus,
    allowed_from: Iterable[InvoiceLineMatchStatus],
) -> bool:
    states = tuple(allowed_from)
    if not states:
        raise ValueError("allowed_from must contain at least one state")
    if db_cursor is None:
        return False
    placeholders = ", ".join(["%s"] * len(states))
    sql = (
        f"UPDATE invoice_lines SET match_status=%s WHERE id=%s "
        f"AND (match_status IS NULL OR match_status IN ({placeholders}))"
    )
    params: tuple[object, ...] = (target.value, line_id, *[state.value for state in states])
    try:
        with db_cursor() as cur:
            cur.execute(sql, params)
            if cur.rowcount:
                return True
    except Exception:
        logger.exception("Failed to update invoice line status")
        raise
    _record_illegal("line_match_status", str(line_id), target.value)
    return False


def transition_line_status_and_link(
    line_id: int,
    matched_file_id: str,
    score: float | None,
    target: InvoiceLineMatchStatus,
    allowed_from: Iterable[InvoiceLineMatchStatus],
) -> bool:
    """Update ``match_status`` together with ``matched_file_id`` and ``match_score``."""

    states = tuple(allowed_from)
    if not states:
        raise ValueError("allowed_from must contain at least one state")
    if db_cursor is None:
        return False
    placeholders = ", ".join(["%s"] * len(states))
    sql = (
        "UPDATE invoice_lines SET matched_file_id=%s, match_score=%s, match_status=%s "
        "WHERE id=%s AND (match_status IS NULL OR match_status IN ({placeholders}))"
    ).format(placeholders=placeholders)
    params: tuple[object, ...] = (
        matched_file_id,
        score,
        target.value,
        line_id,
        *[state.value for state in states],
    )
    try:
        with db_cursor() as cur:
            cur.execute(sql, params)
            if cur.rowcount:
                return True
    except Exception:
        logger.exception("Failed to link invoice line to receipt")
        raise
    _record_illegal("line_match_status", str(line_id), target.value)
    return False


def reset_line_match(line_id: int) -> bool:
    """Reset an invoice line to ``pending`` when an auto-match fails."""

    if db_cursor is None:
        return False
    sql = (
        "UPDATE invoice_lines SET matched_file_id=NULL, match_score=NULL, match_status=%s "
        "WHERE id=%s"
    )
    try:
        with db_cursor() as cur:
            cur.execute(sql, (InvoiceLineMatchStatus.PENDING.value, line_id))
            return cur.rowcount > 0
    except Exception:
        logger.exception("Failed to reset invoice line state")
        raise
