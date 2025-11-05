from __future__ import annotations

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping


def _serialize(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: str = "info",
    **data: Any,
) -> None:
    """Emit a structured log message with a shared schema.

    Args:
        logger: Target logger instance.
        event: Machine readable event token, e.g. ``"matching.auto.start"``.
        level: Logging level name (``info``, ``warning``, ``error``...).
        **data: Additional context encoded into the payload.
    """
    payload: dict[str, Any] = {"event": event}
    for key, value in data.items():
        if value is None:
            continue
        payload[str(key)] = _serialize(value)
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(json.dumps(payload, ensure_ascii=True))
