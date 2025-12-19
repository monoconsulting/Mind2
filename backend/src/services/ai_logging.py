from __future__ import annotations

import logging
import re
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


def _sanitize_log_text(
    log_text: Optional[str],
    *,
    prompt_text: Optional[str],
    response_text: Optional[str],
) -> Optional[str]:
    """Prevent accidental prompt/response leakage into ai_processing_history.log_text."""
    if not log_text:
        return log_text

    sanitized = log_text
    removed_any = False

    for candidate in (prompt_text, response_text):
        if not candidate:
            continue
        # Guard against over-eager removals on tiny strings.
        if len(candidate) < 50:
            continue
        if candidate in sanitized:
            sanitized = sanitized.replace(candidate, "")
            removed_any = True

    if not removed_any:
        return log_text

    sanitized = re.sub(r"[ \t]+", " ", sanitized).strip()
    return sanitized or "Sanitized: removed prompt/response content from log_text"


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

    log_text = _sanitize_log_text(log_text, prompt_text=prompt_text, response_text=response_text)

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
