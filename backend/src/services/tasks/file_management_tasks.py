from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from ._compat import get_override
from .common import (
    AccountingEntry,
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    AiStatus,
    Receipt,
    ReceiptItem,
    ReceiptStatus,
    db_cursor,
    log_event,
    set_ai_status,
    transition_document_status,
    transition_processing_status,
)
from .history import _history as _base_history
from .utils.invoice_utils import (
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_metadata,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from api.reconciliation_firstcard.utils.db_helpers import ensure_invoice_document

logger = logging.getLogger(__name__)


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
    *,
    ocr_raw: str | None = None,
    merchant: str | None = None,
    gross: float | None = None,
    purchase_iso: str | None = None,
) -> bool:
    """Update allowed unified_file fields (currently OCR text; others are ignored)."""

    if db_cursor is None:
        return False
    try:
        if ocr_raw is None:
            return False
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET ocr_raw=%s, updated_at=NOW() WHERE id=%s",
                (ocr_raw, file_id),
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


def _enqueue_invoice_document(invoice_id: str) -> bool:
    try:
        from .invoice_tasks import process_invoice_document  # Local import to avoid cycles
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


def _move_to_manual_review(file_id: str, reason: str | None = None) -> None:
    """Best-effort helper that marks a file as requiring manual review."""

    try:
        set_ai_status(file_id, AiStatus.MANUAL_REVIEW.value)
    except Exception:
        logger.debug("Failed to set manual review status for %s", file_id)
    if reason:
        log_event(logger, "ai.manual_review", file_id=file_id, reason=reason)


def _fail_invoice_processing(invoice_id: str | None, error_message: str | None = None) -> None:
    """Transition an invoice to FAILED and capture the reason in history."""

    if not invoice_id:
        return

    processing_transition = get_override("transition_processing_status", transition_processing_status)
    document_transition = get_override("transition_document_status", transition_document_status)
    history_logger = get_override("_history", _base_history)

    try:
        processing_transitioned = processing_transition(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.UPLOADED,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
            ),
        )
    except Exception:
        processing_transitioned = False

    if processing_transitioned:
        try:
            document_transition(
                invoice_id,
                InvoiceDocumentStatus.FAILED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.MATCHED,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    InvoiceDocumentStatus.COMPLETED,
                ),
            )
        except Exception:
            logger.debug("Failed to transition document status for %s", invoice_id, exc_info=True)

    try:
        history_logger(
            invoice_id,
            job="invoice_processing",
            status="error",
            error_message=error_message,
        )
    except Exception:
        logger.debug("Failed to log invoice failure for %s", invoice_id, exc_info=True)

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
    page_status[file_id] = AiStatus.OCR_DONE.value if success else AiStatus.OCR_FAILED.value
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
    if not ensure_invoice_document(invoice_id, invoice_type="credit_card_invoice"):
        logger.error(
            "Skipping invoice state advance for %s (file %s): missing invoice_documents row",
            invoice_id,
            file_id,
        )
        return

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
            purchase_at = purchase_dt
        elif isinstance(purchase_dt, str):
            try:
                purchase_at = datetime.fromisoformat(purchase_dt.replace("Z", "+00:00"))
            except Exception:
                purchase_at = None
        else:
            purchase_at = None

        receipt = Receipt(
            id=rid,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            company_name=company_name or "",
            orgnr=orgnr or "",
            purchase_datetime=purchase_at,
            gross_amount=Decimal(str(gross or 0)),
            net_amount=Decimal(str(net or 0)),
            ai_confidence=float(ai_conf or 0),
            status=ReceiptStatus.PROCESSED,
            tags=tags,
        )
        return receipt
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


def _load_accounting_inputs(file_id: str) -> dict[str, Any] | None:
    """Load and normalize deterministic accounting inputs for AI4.

    Returns a dict with normalized values and a boolean gate `ai4_ready`.

    IMPORTANT: AI4 must not run when totals are missing/invalid. When deterministic
    inputs exist (e.g. currency=SEK and *_original is set), this function fills
    missing SEK totals and exchange_rate and persists them back to unified_files.
    """

    if db_cursor is None:
        return None

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    uf.gross_amount_sek,
                    uf.net_amount_sek,
                    uf.gross_amount_original,
                    uf.net_amount_original,
                    uf.currency,
                    uf.exchange_rate,
                    c.name AS vendor_name
                FROM unified_files uf
                LEFT JOIN companies c ON uf.company_id = c.id
                WHERE uf.id = %s
                """,
                (file_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            gross_amount_sek, net_amount_sek, gross_amount_original, net_amount_original, currency, exchange_rate, vendor_name = row

            currency_norm = str(currency or "").strip().upper()
            updates: list[str] = []
            params: list[Any] = []

            if currency_norm == "SEK":
                if gross_amount_sek is None and gross_amount_original is not None:
                    gross_amount_sek = gross_amount_original
                    updates.append("gross_amount_sek=%s")
                    params.append(gross_amount_sek)

                if net_amount_sek is None and net_amount_original is not None:
                    net_amount_sek = net_amount_original
                    updates.append("net_amount_sek=%s")
                    params.append(net_amount_sek)

                if exchange_rate in (None, 0):
                    exchange_rate = 1.0
                    updates.append("exchange_rate=%s")
                    params.append(exchange_rate)

            if updates:
                updates.append("updated_at=NOW()")
                params.append(file_id)
                cur.execute(
                    f"UPDATE unified_files SET {', '.join(updates)} WHERE id=%s",
                    tuple(params),
                )

            vat_amount_sek = None
            if gross_amount_sek is not None and net_amount_sek is not None:
                try:
                    vat_amount_sek = gross_amount_sek - net_amount_sek
                except Exception:
                    vat_amount_sek = None

            has_sek_totals = gross_amount_sek is not None and net_amount_sek is not None
            has_original_totals = gross_amount_original is not None and net_amount_original is not None

            ai4_ready = has_sek_totals
            if not ai4_ready:
                # Controlled indicator for the caller to mark needs_review and skip AI4.
                return {
                    "ai4_ready": False,
                    "reason": "missing totals for accounting",
                    "gross_amount_sek": gross_amount_sek,
                    "net_amount_sek": net_amount_sek,
                    "vat_amount_sek": vat_amount_sek,
                    "gross_amount_original": gross_amount_original,
                    "net_amount_original": net_amount_original,
                    "currency": currency_norm or None,
                    "exchange_rate": exchange_rate,
                    "vendor_name": vendor_name,
                    "missing_totals": not has_sek_totals and not has_original_totals,
                }

            # Guard obvious invalid totals to avoid sending nonsense to AI4.
            try:
                if gross_amount_sek is not None and net_amount_sek is not None and gross_amount_sek < net_amount_sek:
                    return {
                        "ai4_ready": False,
                        "reason": "missing totals for accounting",
                        "gross_amount_sek": gross_amount_sek,
                        "net_amount_sek": net_amount_sek,
                        "vat_amount_sek": vat_amount_sek,
                        "gross_amount_original": gross_amount_original,
                        "net_amount_original": net_amount_original,
                        "currency": currency_norm or None,
                        "exchange_rate": exchange_rate,
                        "vendor_name": vendor_name,
                        "missing_totals": False,
                    }
            except Exception:
                return {
                    "ai4_ready": False,
                    "reason": "missing totals for accounting",
                    "gross_amount_sek": gross_amount_sek,
                    "net_amount_sek": net_amount_sek,
                    "vat_amount_sek": vat_amount_sek,
                    "gross_amount_original": gross_amount_original,
                    "net_amount_original": net_amount_original,
                    "currency": currency_norm or None,
                    "exchange_rate": exchange_rate,
                    "vendor_name": vendor_name,
                    "missing_totals": False,
                }

            return {
                "ai4_ready": True,
                "gross_amount_sek": gross_amount_sek,
                "net_amount_sek": net_amount_sek,
                "vat_amount_sek": vat_amount_sek,
                "gross_amount_original": gross_amount_original,
                "net_amount_original": net_amount_original,
                "currency": currency_norm or None,
                "exchange_rate": exchange_rate,
                "vendor_name": vendor_name,
            }
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


__all__ = [
    "_update_file_status",
    "_update_file_fields",
    "_enforce_file_metadata",
    "_enqueue_invoice_document",
    "_move_to_manual_review",
    "_fail_invoice_processing",
    "_maybe_advance_invoice_from_file",
    "_load_receipt_model",
    "_get_file_type",
    "_collect_text_hints",
    "_load_ai_context",
    "_load_accounting_inputs",
    "_load_receipt_items",
    "_save_accounting_entries",
]
