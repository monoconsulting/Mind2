from __future__ import annotations

import logging
from typing import Optional

from services.db.connection import db_cursor

logger = logging.getLogger(__name__)

# Centralised insert used across ingestion/tasks (Phase F - unified helper)
INSERT_HISTORY_SQL = """
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name, prompt_text, response_text)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def log_ai_call(
    file_id: str,
    job: str,
    status: str,
    ai_stage_name: Optional[str] = None,
    log_text: Optional[str] = None,
    error_message: Optional[str] = None,
    confidence: Optional[float] = None,
    processing_time_ms: Optional[int] = None,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    prompt_text: Optional[str] = None,
    response_text: Optional[str] = None,
    *,
    cursor=None,
) -> bool:
    """Best-effort logging into ai_processing_history."""
    if db_cursor is None:
        logger.debug(
            "db_cursor unavailable; skip ai_processing_history insert for job=%s file_id=%s",
            job,
            file_id,
        )
        return False

    try:
        if cursor is not None:
            cursor.execute(
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
                        prompt_text,
                        response_text,
                    ),
            )
            return True

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
                        prompt_text,
                        response_text,
                    ),
            )
            return True
    except Exception as exc:
        logger.warning(
            "Failed to log ai_processing_history (file_id=%s, job=%s): %s",
            file_id,
            job,
            exc,
        )
        return False


__all__ = ["INSERT_HISTORY_SQL", "log_ai_call"]
