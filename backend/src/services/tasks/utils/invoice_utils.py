from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
import sys
from typing import Any, Callable, Optional

from services.invoice_status import (
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    invoice_documents_supports_updated_at,
)

from ..base import db_cursor
from .file_utils import _load_unified_file_info as _file_utils_loader


_INVOICE_PAGE_COMPLETE_STATUSES = {
    "ocr_done",
    InvoiceProcessingStatus.OCR_DONE.value,
    InvoiceProcessingStatus.READY_FOR_MATCHING.value,
    InvoiceProcessingStatus.MATCHING_COMPLETED.value,
    InvoiceProcessingStatus.COMPLETED.value,
}


def _resolve_file_info_loader() -> Callable[[str], dict[str, Any] | None]:
    tasks_module = sys.modules.get("services.tasks")
    if tasks_module is not None:
        loader = getattr(tasks_module, "_load_unified_file_info", None)
        if callable(loader):
            return loader  # type: ignore[return-value]
    return _file_utils_loader


def _get_invoice_parent_id(file_id: str, file_type: Optional[str] = None) -> Optional[str]:
    loader = _resolve_file_info_loader()
    try:
        info = loader(file_id) or {}
    except Exception:
        info = {}
    if file_type is not None:
        info = dict(info)
        info["file_type"] = file_type

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
        data = json.loads(payload)
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


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
    for page_id in page_ids:
        status = (page_status.get(page_id) or "").lower()
        if status in _INVOICE_PAGE_COMPLETE_STATUSES:
            completed += 1
    if not page_ids:
        for status in page_status.values():
            if (status or "").lower() in _INVOICE_PAGE_COMPLETE_STATUSES:
                completed += 1
    total = data.get("page_count")
    if not isinstance(total, int) or total <= 0:
        fallback = len(page_ids) or len(page_status)
        total = fallback if fallback > 0 else 0
    pending = max(total - completed, 0)
    return {"total": total, "completed": completed, "pending": pending}


def _persist_invoice_lines(invoice_id: str, parsed_lines: list[dict[str, Any]]) -> int:
    if db_cursor is None:
        return 0
    inserted = 0
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
            for line in parsed_lines:
                try:
                    amount = Decimal(str(line.get("amount", 0))).quantize(Decimal("0.01"))
                except Exception:
                    amount = Decimal("0.00")
                transaction_date = line.get("transaction_date")
                merchant_name = line.get("merchant_name") or line.get("description") or ""
                description = line.get("description") or merchant_name
                confidence = line.get("confidence")
                ocr_text = line.get("raw_text") or ""
                cur.execute(
                    (
                        "INSERT INTO invoice_lines "
                        "(invoice_id, transaction_date, amount, merchant_name, description, match_status, extraction_confidence, ocr_source_text) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        invoice_id,
                        transaction_date,
                        amount,
                        merchant_name,
                        description,
                        InvoiceLineMatchStatus.PENDING.value,
                        confidence,
                        ocr_text,
                    ),
                )
                inserted += 1
    except Exception:
        return inserted
    return inserted


__all__ = [
    "_INVOICE_PAGE_COMPLETE_STATUSES",
    "_resolve_file_info_loader",
    "_get_invoice_parent_id",
    "_load_invoice_metadata",
    "_update_invoice_metadata",
    "_set_invoice_metadata_field",
    "_invoice_page_progress",
    "_persist_invoice_lines",
]
