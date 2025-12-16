from __future__ import annotations

from services.ai_logging import INSERT_HISTORY_SQL, log_ai_call


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
    prompt_text: str | None = None,
    response_text: str | None = None,
) -> None:
    """Thin wrapper for backward compatibility; uses unified log_ai_call helper."""
    log_ai_call(
        file_id=file_id,
        job=job,
        status=status,
        ai_stage_name=ai_stage_name,
        log_text=log_text,
        error_message=error_message,
        confidence=confidence,
        processing_time_ms=processing_time_ms,
        provider=provider,
        model_name=model_name,
        prompt_text=prompt_text,
        response_text=response_text,
    )


__all__ = ["INSERT_HISTORY_SQL", "_history", "log_ai_call"]
