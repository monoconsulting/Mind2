from __future__ import annotations

import json
from importlib import import_module
from typing import Any, Optional

from ..base import logger

TASKS_MODULE = "services.tasks"


def _get_db_cursor():
    module = import_module(TASKS_MODULE)
    return getattr(module, "db_cursor", None)


def _update_file_fields(
    file_id: str,
    ocr_raw: str | None = None,
) -> bool:
    """Update ONLY OCR raw text. All business data set by AI, not OCR."""
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
        return False
    try:
        if ocr_raw is None:
            return False
        with cursor_factory() as cur:
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
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
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
        with cursor_factory() as cur:
            cur.execute(
                f"UPDATE unified_files SET {', '.join(updates)} WHERE id=%s",
                tuple(params),
            )
    except Exception:
        logger.warning("Failed to enforce metadata for file %s", file_id, exc_info=True)


def _load_unified_file_info(file_id: str) -> dict[str, Any] | None:
    cursor_factory = _get_db_cursor()
    if cursor_factory is None:
        return None
    try:
        with cursor_factory() as cur:
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


def _get_invoice_parent_id(file_id: str, file_type: str | None = None) -> Optional[str]:
    normalized_type = str(file_type or "").strip().lower()
    info: dict[str, Any] | None = None
    if not normalized_type:
        info = _load_unified_file_info(file_id)
        normalized_type = str((info or {}).get("file_type") or "").lower()

    if normalized_type in {"invoice", "cc_pdf"}:
        if info and isinstance(info.get("id"), str) and info["id"]:
            return str(info["id"])
        return str(file_id)

    if normalized_type in {"invoice_page", "cc_image"}:
        cursor_factory = _get_db_cursor()
        if cursor_factory is None:
            return None
        try:
            with cursor_factory() as cur:
                cur.execute(
                    "SELECT original_file_id FROM unified_files WHERE id=%s",
                    (file_id,),
                )
                parent_row = cur.fetchone()
        except Exception:
            return None

        parent_id = parent_row[0] if parent_row else None
        if not parent_id:
            return None

        try:
            with cursor_factory() as cur:
                cur.execute(
                    "SELECT file_type FROM unified_files WHERE id=%s",
                    (parent_id,),
                )
                parent_type_row = cur.fetchone()
        except Exception:
            return None

        parent_type = (
            str(parent_type_row[0]).strip().lower()
            if parent_type_row and parent_type_row[0]
            else ""
        )
        if parent_type in {"invoice", "cc_pdf"}:
            return str(parent_id)
        return None

    return None


def _get_file_type(file_id: str) -> Optional[str]:
    info = _load_unified_file_info(file_id)
    if not info:
        return None
    file_type = info.get("file_type")
    return str(file_type) if file_type else None


__all__ = [
    "_update_file_fields",
    "_enforce_file_metadata",
    "_load_unified_file_info",
    "_get_invoice_parent_id",
    "_get_file_type",
]
