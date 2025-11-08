from __future__ import annotations

import json
from datetime import datetime
from importlib import import_module
from typing import Any

from ...invoice_status import InvoiceProcessingStatus

TASKS_MODULE = "services.tasks"


def _get_db_cursor():
    module = import_module(TASKS_MODULE)
    return getattr(module, "db_cursor", None)


_INVOICE_PAGE_COMPLETE_STATUSES = {
    "ocr_done",
    InvoiceProcessingStatus.OCR_DONE.value,
    InvoiceProcessingStatus.READY_FOR_MATCHING.value,
    InvoiceProcessingStatus.MATCHING_COMPLETED.value,
    InvoiceProcessingStatus.COMPLETED.value,
}


def _load_invoice_metadata(invoice_id: str) -> dict[str, Any] | None:
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
        return None
    try:
        with cursor_factory() as cur:
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
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
        return False
    try:
        payload = dict(metadata or {})
        from ...invoice_status import invoice_documents_supports_updated_at

        if not invoice_documents_supports_updated_at():
            payload["last_progress_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with cursor_factory() as cur:
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


def _invoice_page_progress(
    invoice_id: str,
    metadata: dict[str, Any] | None = None,
) -> tuple[int, int]:
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

    used_metadata = bool(page_ids or page_status)
    if total <= 0 or not used_metadata:
        records = _load_invoice_file_records(invoice_id)
        if records:
            record_total = 0
            record_completed = 0
            for record in records:
                if not record:
                    continue
                record_total += 1
                status = ""
                if len(record) >= 3 and record[2]:
                    status = str(record[2]).lower()
                if status in _INVOICE_PAGE_COMPLETE_STATUSES:
                    record_completed += 1
            total = max(total, record_total)
            completed = max(completed, record_completed)
        elif total <= 0:
            cursor_factory = _get_db_cursor()
            if cursor_factory is not None:
                try:
                    with cursor_factory() as cur:
                        cur.execute(
                            "SELECT ai_status FROM unified_files WHERE id=%s",
                            (invoice_id,),
                        )
                        row = cur.fetchone()
                except Exception:
                    row = None
                if row:
                    total = 1
                    status = (row[0] or "").lower()
                    completed = 1 if status in _INVOICE_PAGE_COMPLETE_STATUSES else 0
    return (completed, total)


def _load_invoice_file_records(invoice_id: str) -> list[tuple[Any, ...]]:
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
        return []
    try:
        with cursor_factory() as cur:
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
    "_load_invoice_metadata",
    "_update_invoice_metadata",
    "_set_invoice_metadata_field",
    "_invoice_page_progress",
    "_load_invoice_file_records",
    "_collect_invoice_ocr_text",
    "_INVOICE_PAGE_COMPLETE_STATUSES",
]
