from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Tuple

from .connection import db_cursor
from services.workflow_runs import create_workflow_run


class DuplicateFileError(Exception):
    """Raised when attempting to store a duplicate file."""


@dataclass
class UnifiedFile:
    id: str
    file_type: str
    original_filename: str
    content_hash: str | None
    submitted_by: str | None
    ai_status: str
    company_id: int | None = None
    workflow_type: str | None = None
    file_category: int | None = None
    workflow_run_id: int | None = None


def get_unified_file_by_hash(content_hash: str) -> Optional[UnifiedFile]:
    """Return a unified_file row matching the given content hash, if any."""
    if db_cursor is None:
        return None

    with db_cursor() as cur:
        cur.execute(
            (
                "SELECT id, file_type, original_filename, content_hash, submitted_by, "
                "ai_status, company_id, workflow_type, file_category "
                "FROM unified_files WHERE content_hash=%s LIMIT 1"
            ),
            (content_hash,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return UnifiedFile(
            id=row[0],
            file_type=row[1],
            original_filename=row[2],
            content_hash=row[3],
            submitted_by=row[4],
            ai_status=row[5],
            company_id=row[6],
            workflow_type=row[7],
            file_category=row[8],
        )


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
    """
    Deprecated: Use create_unified_file instead.
    
    Insert a new unified file record.
    """
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


def create_unified_file(
    *,
    file_id: str | None = None,
    company_id: int | None = None,
    file_type: str,
    original_filename: str,
    stored_path: str | None = None,
    content_hash: str | None,
    submitted_by: str | None,
    source: str | None,
    initial_process_status: str | None = None,
    initial_ai_status: str,
    extra_metadata: dict | None = None,
    workflow_key: str | None = None,
    workflow_type: str | None = None,
    mime_type: str | None = None,
    file_suffix: str | None = None,
    original_file_id: str | None = None,
    original_file_name: str | None = None,
    original_file_size: int | None = None,
    file_category: int | None = None,
    create_workflow: bool = True,
) -> UnifiedFile:
    """
    Create a new unified file record in the database.
    
    Handles deduplication by raising DuplicateFileError if content_hash exists.
    """
    if db_cursor is None:
        raise RuntimeError("Database connection not available")

    if file_id is None:
        file_id = str(uuid.uuid4())

    # Prepare other_data
    other_data = extra_metadata or {}
    if source:
        other_data['source'] = source
    
    payload = json.dumps(other_data)
    
    # Default workflow type if not provided
    # Logic from insert_unified_file: workflow_value = workflow_type or "receipt"
    # But we should probably be explicit or let DB default handle it?
    # DB schema might not have default. insert_unified_file used "receipt".
    final_workflow_type = workflow_type or "receipt"
    effective_workflow_key = workflow_key or (final_workflow_type if str(final_workflow_type).startswith("WF") else None)

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO unified_files (
                    id, file_type, workflow_type, ocr_raw, other_data, content_hash,
                    submitted_by, original_filename, ai_status,
                    mime_type, file_suffix, original_file_id,
                    original_file_name, original_file_size, company_id, file_category
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    file_id,
                    file_type,
                    final_workflow_type,
                    "", # ocr_raw
                    payload,
                    content_hash,
                    submitted_by,
                    original_filename,
                    initial_ai_status,
                    mime_type,
                    file_suffix,
                    original_file_id or file_id,
                    original_file_name or original_filename,
                    original_file_size,
                    company_id,
                    file_category
                ),
            )
            
            result = UnifiedFile(
                id=file_id,
                file_type=file_type,
                original_filename=original_filename,
                content_hash=content_hash,
                submitted_by=submitted_by,
                ai_status=initial_ai_status,
                company_id=company_id,
                workflow_type=final_workflow_type,
                file_category=file_category
            )
            
            # Create workflow run if workflow type is present and requested
            if create_workflow and effective_workflow_key:
                workflow_run_id = create_workflow_run(
                    workflow_key=effective_workflow_key,
                    source_channel=source or "unknown",
                    file_id=file_id,
                    content_hash=content_hash or ""
                )
                result.workflow_run_id = workflow_run_id
                
            return result
            
    except Exception as db_error:
        msg = str(db_error)
        if "Duplicate entry" in msg and "idx_content_hash" in msg:
            raise DuplicateFileError(f"File with hash {content_hash} already exists") from db_error
        raise
