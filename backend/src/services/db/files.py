from __future__ import annotations

import json
from typing import Any, Iterable, List, Optional, Tuple

from .connection import db_cursor


class DuplicateFileError(Exception):
    """Raised when attempting to store a duplicate file."""


def set_ai_status(file_id: str, status: str) -> bool:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE unified_files SET ai_status=%s, updated_at=NOW() WHERE id=%s",
            (status, file_id),
        )
        return cur.rowcount > 0


def list_unprocessed(limit: int = 50) -> List[str]:
    with db_cursor() as cur:
        cur.execute(
            (
                "SELECT id FROM unified_files "
                "WHERE ai_status IS NULL OR ai_status IN ('new','queued') "
                "ORDER BY created_at DESC LIMIT %s"
            ),
            (limit,),
        )
        return [row[0] for row in cur.fetchall() or []]


def get_receipt(file_id: str) -> Optional[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            (
                "SELECT u.id, c.name, c.orgnr, u.purchase_datetime, u.gross_amount, u.net_amount, u.ai_status, u.ai_confidence "
                "FROM unified_files u "
                "LEFT JOIN companies c ON c.id = u.company_id "
                "WHERE u.id=%s"
            ),
            (file_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            _id,
            merchant,
            orgnr,
            pdt,
            gross,
            net,
            ai_status,
            ai_confidence,
        ) = row
        return {
            "id": _id,
            "merchant": merchant,
            "orgnr": orgnr,
            "purchase_datetime": (pdt.isoformat() if hasattr(pdt, "isoformat") else pdt),
            "gross_amount": (float(gross) if gross is not None else None),
            "net_amount": (float(net) if net is not None else None),
            "ai_status": ai_status,
            "ai_confidence": ai_confidence,
        }

def insert_unified_file(
    *,
    file_id: str,
    file_type: str,
    workflow_type: str | None = None,
    content_hash: str,
    submitted_by: str,
    original_filename: str,
    ai_status: str,
    mime_type: str | None = None,
    file_suffix: str | None = None,
    original_file_id: str | None = None,
    original_file_name: str | None = None,
    original_file_size: int | None = None,
    other_data: dict[str, Any] | None = None,
) -> None:
    if db_cursor is None:
        return

    payload = json.dumps(other_data or {})

    workflow_value = workflow_type or "receipt"

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO unified_files (
                    id, file_type, workflow_type, ocr_raw, other_data, content_hash,
                    submitted_by, original_filename, ai_status,
                    mime_type, file_suffix, original_file_id,
                    original_file_name, original_file_size
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    file_id,
                    file_type,
                    workflow_value,
                    "",
                    payload,
                    content_hash,
                    submitted_by,
                    original_filename,
                    ai_status,
                    mime_type,
                    file_suffix,
                    original_file_id or file_id,
                    original_file_name or original_filename,
                    original_file_size,
                ),
            )
    except Exception as db_error:
        msg = str(db_error)
        if "Duplicate entry" in msg and "idx_content_hash" in msg:
            raise DuplicateFileError from db_error
        raise


def update_other_data(file_id: str, other_data: dict[str, Any]) -> None:
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET other_data=%s WHERE id=%s",
                (json.dumps(other_data or {}), file_id),
            )
    except Exception:
        pass

