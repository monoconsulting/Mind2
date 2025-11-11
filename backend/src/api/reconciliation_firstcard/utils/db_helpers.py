# -*- coding: utf-8 -*-
# ÅÄÖ åäö – Swedish encoding test

"""Database helper functions for FirstCard reconciliation.

This module provides database operations for invoice documents, files,
and workflow management. All functions handle Swedish encoding properly
and use real database queries (no mock data).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from services.storage import FileStorage
from services.workflow_runs import create_workflow_run
from services.invoice_status import (
    InvoiceProcessingStatus,
    invoice_documents_supports_updated_at,
)
from services.validation import _as_decimal

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)


def _storage() -> FileStorage:
    """Return FileStorage instance."""
    base = os.getenv("STORAGE_DIR", "/data/storage")
    return FileStorage(base)


def _as_date(val: Any) -> Optional[date]:
    """Convert value to date object."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
        except Exception:
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except Exception:
                pass
    return None


def _count_invoice_lines(invoice_id: str) -> tuple[int, int]:
    """Count total and matched invoice lines using the canonical invoice_lines table."""
    if db_cursor is None:
        return (0, 0)

    # Always prefer invoice_lines so UI reflects real-time line status.
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN match_status IN ('auto','manual','confirmed') THEN 1 ELSE 0 END)
                  FROM invoice_lines
                 WHERE invoice_id=%s
                """,
                (invoice_id,),
            )
            row = cur.fetchone()
            if row:
                total, matched = int(row[0] or 0), int(row[1] or 0)
                if total > 0 or matched > 0:
                    return (total, matched)
    except Exception:
        pass

    # Legacy fallback via creditcard_invoice_items if invoice_lines not populated yet.
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            metadata_row = cur.fetchone()
            if metadata_row and metadata_row[0]:
                try:
                    metadata = json.loads(metadata_row[0])
                except Exception:
                    metadata = {}
                main_id = metadata.get("creditcard_main_id")
                if main_id:
                    cur.execute(
                        """
                        SELECT COUNT(*),
                               SUM(CASE WHEN matched >= 1 THEN 1 ELSE 0 END)
                          FROM creditcard_invoice_items
                         WHERE main_id=%s
                        """,
                        (main_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        return (int(row[0] or 0), int(row[1] or 0))
    except Exception:
        pass

    return (0, 0)


def _load_invoice_document(
    invoice_id: str,
    include_deleted: bool = False,
) -> Optional[tuple[str, dict[str, Any], Optional[datetime]]]:
    """Load invoice document status and metadata.

    Returns:
        (status, metadata, deleted_at) or None if not found
    """
    if db_cursor is None:
        return None

    try:
        with db_cursor() as cur:
            query = "SELECT status, metadata_json, deleted_at FROM invoice_documents WHERE id=%s"
            params: tuple[Any, ...] = (invoice_id,)
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            cur.execute(query, params)
            row = cur.fetchone()
            if not row:
                return None

            status = row[0]
            metadata_raw = row[1]
            deleted_at = row[2]
            metadata: dict[str, Any] = {}

            if metadata_raw:
                try:
                    if isinstance(metadata_raw, (bytes, bytearray)):
                        metadata_raw = metadata_raw.decode("utf-8")
                    metadata = json.loads(metadata_raw)
                except Exception:
                    metadata = {}

            return (status, metadata, deleted_at)
    except Exception:
        return None


def _list_invoice_files(source_file_id: str) -> list[dict[str, Any]]:
    """List all files related to an invoice."""
    if db_cursor is None:
        return []

    files: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, file_type, ai_status, ocr_raw, other_data, created_at
                FROM unified_files
                WHERE id = %s OR original_file_id = %s
                ORDER BY created_at ASC
                """,
                (source_file_id, source_file_id),
            )
            for row in cur.fetchall() or []:
                file_id, file_type, ai_status, ocr_raw, other_json, created_at = row
                other_data: dict[str, Any] = {}
                if other_json:
                    try:
                        other_data = json.loads(other_json)
                    except Exception:
                        other_data = {}

                files.append({
                    "id": file_id,
                    "file_type": file_type,
                    "ai_status": ai_status,
                    "ocr_raw": ocr_raw,
                    "other_data": other_data,
                    "created_at": created_at,
                })
    except Exception:
        pass

    return files


def _create_invoice_document(
    invoice_id: str,
    invoice_type: str,
    status: str,
    metadata: dict[str, Any],
    processing_status: Optional[str] = None,
) -> bool:
    """Create or update invoice document record."""
    if db_cursor is None:
        return False

    try:
        with db_cursor() as cur:
            # Check if exists
            cur.execute(
                "SELECT id FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            exists = cur.fetchone() is not None

            payload = dict(metadata or {})
            if not invoice_documents_supports_updated_at():
                payload["last_progress_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            metadata_json = json.dumps(payload)

            if exists:
                # Update existing
                set_clause = """
                    SET invoice_type=%s,
                        status=%s,
                        processing_status=COALESCE(%s, processing_status),
                        metadata_json=%s,
                        deleted_at=NULL
                """
                if invoice_documents_supports_updated_at():
                    set_clause += ", updated_at=NOW()"
                cur.execute(
                    f"""
                    UPDATE invoice_documents
                    {set_clause}
                    WHERE id=%s
                    """,
                    (
                        invoice_type,
                        status,
                        processing_status,
                        metadata_json,
                        invoice_id,
                    ),
                )
            else:
                # Insert new
                cur.execute(
                    """
                    INSERT INTO invoice_documents
                    (id, invoice_type, status, processing_status, metadata_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        invoice_type,
                        status,
                        processing_status or InvoiceProcessingStatus.UPLOADED.value,
                        metadata_json,
                    ),
                )

        return True
    except Exception as e:
        logger.error(f"Failed to create/update invoice document: {e}")
        return False


def _write_invoice_metadata(invoice_id: str, metadata: dict[str, Any]) -> bool:
    """Write metadata to invoice document."""
    if db_cursor is None:
        return False

    try:
        payload = dict(metadata or {})
        if not invoice_documents_supports_updated_at():
            payload["last_progress_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with db_cursor() as cur:
            set_clause = "metadata_json=%s"
            if invoice_documents_supports_updated_at():
                set_clause += ", updated_at=NOW()"
            cur.execute(
                f"UPDATE invoice_documents SET {set_clause} WHERE id=%s",
                (json.dumps(payload), invoice_id),
            )
        return True
    except Exception as e:
        logger.error(f"Failed to write invoice metadata: {e}")
        return False


def _create_workflow_run(
    workflow_key: str,
    source_channel: str,
    file_id: str,
    content_hash: str,
) -> Optional[int]:
    """Create workflow run and return ID."""
    run_id = create_workflow_run(
        workflow_key=workflow_key,
        source_channel=source_channel,
        file_id=file_id,
        content_hash=content_hash,
    )

    if run_id is None or db_cursor is None:
        return run_id

    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE workflow_runs SET current_stage=%s WHERE id=%s",
                ("init", run_id),
            )
    except Exception as exc:
        logger.warning(
            "Failed to set initial workflow stage for run %s (%s)",
            run_id,
            exc,
        )
    return run_id


def _find_file_id_by_hash(file_hash: str) -> Optional[str]:
    """Find existing file by content hash."""
    if db_cursor is None:
        return None

    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM unified_files WHERE content_hash=%s ORDER BY created_at DESC LIMIT 1",
                (file_hash,),
            )
            row = cur.fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass

    return None


def _find_invoice_id_for_main(main_id: int) -> Optional[str]:
    """Find invoice_document.id from creditcard_invoices_main.id."""
    if db_cursor is None:
        return None

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id FROM invoice_documents
                WHERE metadata_json LIKE CONCAT('%%"creditcard_main_id":', %s, '%%')
                LIMIT 1
                """,
                (main_id,),
            )
            row = cur.fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass

    return None


def _find_invoice_line_id_for_item(
    item_id: int,
    invoice_id: Optional[str] = None,
) -> Optional[int]:
    """Best-effort lookup of invoice_lines.id matching a creditcard invoice item."""
    from decimal import Decimal

    if db_cursor is None:
        return None

    item_row = None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT main_id,
                       purchase_date,
                       amount_original,
                       amount_sek,
                       gross_amount,
                       description,
                       merchant_name
                  FROM creditcard_invoice_items
                 WHERE id=%s
                """,
                (item_id,),
            )
            item_row = cur.fetchone()
    except Exception:
        return None

    if not item_row:
        return None

    (
        main_id,
        purchase_date,
        amount_original,
        amount_sek,
        gross_amount,
        description,
        merchant_name,
    ) = item_row

    target_invoice_id = invoice_id
    if not target_invoice_id:
        target_invoice_id = _find_invoice_id_for_main(int(main_id or 0))
    if not target_invoice_id:
        return None

    target_amount: Optional[Decimal] = None
    for candidate in (amount_sek, gross_amount, amount_original):
        decimal_candidate = _as_decimal(candidate)
        if decimal_candidate is not None:
            target_amount = decimal_candidate
            break
    amount_for_order = target_amount if target_amount is not None else Decimal("0")
    date_value = _as_date(purchase_date)
    merchant_hint = (merchant_name or description or "").strip()

    try:
        with db_cursor() as cur:
            params: list[Any] = [target_invoice_id]
            query = [
                "SELECT id",
                "  FROM invoice_lines",
                " WHERE invoice_id=%s",
                "   AND (match_status IS NULL OR match_status IN ('pending','unmatched','auto'))",
            ]
            if merchant_hint:
                query.append(" ORDER BY ")
                query.append(
                    "CASE WHEN merchant_name = %s THEN 0 ELSE 1 END,"
                )
                params.append(merchant_hint)
            else:
                query.append(" ORDER BY ")

            if date_value is not None:
                query.append("CASE WHEN transaction_date = %s THEN 0 ELSE 1 END,")
                params.append(date_value)
            else:
                query.append("0,")

            query.append(
                "ABS(IFNULL(amount, 0) - %s), id ASC LIMIT 1"
            )
            params.append(amount_for_order)
            cur.execute("".join(query), tuple(params))
            row = cur.fetchone()
            if row:
                return int(row[0])
    except Exception:
        return None

    return None


def _ensure_processing_state(invoice_id: str) -> None:
    """Initialise processing_status to 'uploaded' when missing."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            set_clause = "processing_status=%s"
            if invoice_documents_supports_updated_at():
                set_clause += ", updated_at=NOW()"
            cur.execute(
                f"UPDATE invoice_documents SET {set_clause} WHERE id=%s AND processing_status IS NULL",
                (InvoiceProcessingStatus.UPLOADED.value, invoice_id),
            )
    except Exception:
        logger.warning("Failed to initialise processing status for invoice %s", invoice_id)


def _log_line_history(
    line_id: int,
    action: str,
    performed_by: str,
    *,
    old_file_id: Optional[str] = None,
    new_file_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    """Best-effort insert into invoice_line_history."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO invoice_line_history "
                    "(invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                ),
                (line_id, action, performed_by, old_file_id, new_file_id, reason),
            )
    except Exception:
        logger.debug("Failed to write invoice line history for %s", line_id)


# Public API aliases (without underscore prefix)
storage = _storage
as_date = _as_date
count_invoice_lines = _count_invoice_lines
load_invoice_document = _load_invoice_document
list_invoice_files = _list_invoice_files
create_invoice_document = _create_invoice_document
write_invoice_metadata = _write_invoice_metadata
create_workflow_run = _create_workflow_run
find_file_id_by_hash = _find_file_id_by_hash
find_invoice_id_for_main = _find_invoice_id_for_main
find_invoice_line_id_for_item = _find_invoice_line_id_for_item
ensure_processing_state = _ensure_processing_state
log_line_history = _log_line_history
as_decimal = _as_decimal
