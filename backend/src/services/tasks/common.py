from __future__ import annotations

try:  # pragma: no cover - database unavailable in some environments
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

try:  # pragma: no cover - optional during type checking
    from services.db.files import (
        DuplicateFileError,
        insert_unified_file,
        set_ai_status,
        update_other_data,
    )
except Exception:  # pragma: no cover
    class DuplicateFileError(Exception):
        """Fallback duplicate error when database module is unavailable."""

    def insert_unified_file(*args, **kwargs):  # type: ignore[override]
        return None

    def update_other_data(*args, **kwargs):  # type: ignore[override]
        return None

    def set_ai_status(file_id: str, status: str) -> bool:  # type: ignore[override]
        _ = (file_id, status)
        return False

__all__ = [
    "DuplicateFileError",
    "db_cursor",
    "insert_unified_file",
    "set_ai_status",
    "update_other_data",
]
