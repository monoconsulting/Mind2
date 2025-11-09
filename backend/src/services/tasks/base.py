from __future__ import annotations

import logging

from services.queue_manager import get_celery

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

LOGGER_NAME = "services.tasks"
logger = logging.getLogger(LOGGER_NAME)
celery_app = get_celery()

__all__ = ["LOGGER_NAME", "logger", "celery_app", "db_cursor"]
