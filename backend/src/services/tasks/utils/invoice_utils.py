from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from ..common import (
    InvoiceProcessingStatus,
    db_cursor,
    invoice_documents_supports_updated_at,
)

_INVOICE_PAGE_COMPLETE_STATUSES = {
    "ocr_done",
    InvoiceProcessingStatus.OCR_DONE.value,
    InvoiceProcessingStatus.READY_FOR_MATCHING.value,
    InvoiceProcessingStatus.MATCHING_COMPLETED.value,
    InvoiceProcessingStatus.COMPLETED.value,
}


def _load_unified_file_info(file_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, file_type, workflow_type, original_file_id, other_data, mime_type, "
                    "original_filename, original_file_name "
                    "FROM unified_files WHERE id=%s"
                ),
                (file_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    (
        uid,
        file_type,
        workflow_type,
        original_file_id,
        raw_other,
        mime_type,
        original_filename,
        original_file_name,
    ) = row
    other_data: dict[str, Any]
    if raw_other:
        try:
            other_data = json.loads(raw_other)
        except Exception:
            other_data = {}
    else:
        other_data = {}
    return {
        "id": uid,
        "file_type": file_type or "",
        "workflow_type": workflow_type or "",
        "original_file_id": original_file_id,
        "other_data": other_data,
        "mime_type": mime_type,
        "original_filename": original_filename,
        "original_file_name": original_file_name,
    }


def _get_invoice_parent_id(file_id: str) -> Optional[str]:
    info = _load_unified_file_info(file_id)
    if not info:
        return None
    file_type = str(info.get("file_type") or "").lower()
    if file_type in {"invoice_page", "cc_image"}:
        parent = info.get("original_file_id")
        return str(parent) if isinstance(parent, str) and parent else None
    if file_type in {"invoice", "cc_pdf"}:
        identifier = info.get("id")
        return str(identifier) if isinstance(identifier, str) and identifier else None
    return None


def _load_invoice_metadata(invoice_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    payload = row[0]
    if not payload:
        return {}
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except Exception:
            payload = payload.decode("latin1", errors="ignore")
    try:
        return json.loads(payload)
    except Exception:
        return {}


def _update_invoice_metadata(invoice_id: str, metadata: dict[str, Any]) -> bool:
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
    except Exception:
        return False


def _set_invoice_metadata_field(invoice_id: str, field: str, value: Any) -> dict[str, Any] | None:
    metadata = _load_invoice_metadata(invoice_id)
    if metadata is None:
        return None
    metadata[field] = value
    if _update_invoice_metadata(invoice_id, metadata):
        return metadata
    return None


def _invoice_page_progress(invoice_id: str, metadata: dict[str, Any] | None = None) -> dict[str, int]:
    data = metadata if metadata is not None else (_load_invoice_metadata(invoice_id) or {})
    page_ids = data.get("page_ids")
    if not isinstance(page_ids, list):
        page_ids = []
    page_status = data.get("page_status")
    if not isinstance(page_status, dict):
        page_status = {}
    completed = 0
    for pid in page_ids:
        status = (page_status.get(pid) or "").lower()
        if status in _INVOICE_PAGE_COMPLETE_STATUSES:
            completed += 1
    if not page_ids and page_status:
        completed = sum(
            1
            for status in page_status.values()
            if (status or "").lower() in _INVOICE_PAGE_COMPLETE_STATUSES
        )
    total = data.get("page_count")
    if not isinstance(total, int) or total <= 0:
        fallback = len(page_ids) or len(page_status)
        total = fallback if fallback > 0 else 0
    pending = max(total - completed, 0)
    return {"total": total, "completed": completed, "pending": pending}


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


__all__ = [
    "_load_unified_file_info",
    "_get_invoice_parent_id",
    "_load_invoice_metadata",
    "_update_invoice_metadata",
    "_set_invoice_metadata_field",
    "_invoice_page_progress",
    "_load_invoice_file_records",
    "_collect_invoice_ocr_text",
]
