from __future__ import annotations

import logging

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

from services.queue_manager import get_celery

logger = logging.getLogger("services.tasks")
celery_app = get_celery()
