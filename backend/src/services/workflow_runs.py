"""Shared helpers for creating and dispatching workflow runs."""

from __future__ import annotations

import logging
from typing import Optional

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

logger = logging.getLogger(__name__)


def get_active_workflow_run(file_id: str, workflow_key: str) -> Optional[int]:
    """Check if there's an active (running) workflow_run for a given file.

    Returns:
        workflow_run_id if found, None otherwise
    """
    if db_cursor is None:
        return None

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id FROM workflow_runs
                WHERE file_id = %s
                  AND workflow_key = %s
                  AND status IN ('running', 'queued')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (file_id, workflow_key),
            )
            row = cur.fetchone()
            if row:
                logger.info(
                    "Found active workflow_run %s for file_id=%s, workflow=%s",
                    row[0],
                    file_id,
                    workflow_key,
                )
                return int(row[0])
            return None
    except Exception as exc:  # pragma: no cover
        logger.error(
            "Failed to check active workflow_run for file_id=%s: %s",
            file_id,
            exc,
        )
        return None


def create_workflow_run(
    *,
    workflow_key: str,
    source_channel: str,
    file_id: str,
    content_hash: str,
) -> Optional[int]:
    """Insert a workflow_runs row and return its primary key."""
    if db_cursor is None:
        logger.error(
            "create_workflow_run: database connection unavailable (workflow=%s, file=%s)",
            workflow_key,
            file_id,
        )
        return None

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_runs (workflow_key, source_channel, file_id, content_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (workflow_key, source_channel, file_id, content_hash),
            )
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchone()
            run_id = int(row[0]) if row and row[0] is not None else None
            logger.info(
                "Created workflow_run %s for %s (file_id=%s, channel=%s)",
                run_id,
                workflow_key,
                file_id,
                source_channel,
            )
            return run_id
    except Exception as exc:  # pragma: no cover - DB errors logged for observability
        logger.error(
            "Failed to create workflow_run for %s (file_id=%s): %s",
            workflow_key,
            file_id,
            exc,
        )
        return None

