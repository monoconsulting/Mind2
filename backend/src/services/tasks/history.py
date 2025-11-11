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
        # best-effort history
        pass


__all__ = ["INSERT_HISTORY_SQL", "_history"]
