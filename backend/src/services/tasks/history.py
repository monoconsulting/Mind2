from __future__ import annotations

from .common import db_cursor

INSERT_HISTORY_SQL = """
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def _history(
    file_id: str,
    job: str,
    status: str,
    ai_stage_name: str | None = None,
    log_text: str | None = None,
    error_message: str | None = None,
    confidence: float | None = None,
    processing_time_ms: int | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> None:
    """Log processing history with detailed information."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                INSERT_HISTORY_SQL,
                (
                    file_id,
                    job,
                    status,
                    ai_stage_name,
                    log_text,
                    error_message,
                    confidence,
                    processing_time_ms,
                    provider,
                    model_name,
                ),
            )
    except Exception:
        # best-effort history logging
        pass


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
    ocr_raw: str | None = None,
) -> bool:
    """Update ONLY OCR raw text. All business data set by AI, not OCR."""
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

__all__ = ["_history", "_update_file_status", "_update_file_fields", "INSERT_HISTORY_SQL"]
