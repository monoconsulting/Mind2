from __future__ import annotations

import logging
from typing import Any, Dict, List

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover - optional dependency
    db_cursor = None  # type: ignore

logger = logging.getLogger(__name__)


def fetch_related_file_ids(root_id: str) -> list[str]:
    """
    Return list of file IDs (root + derived children) tied to a unified_files record.

    Returns empty list if the root record does not exist.
    """
    if not root_id:
        return []
    if db_cursor is None:
        return [str(root_id)]

    related: set[str] = set()
    try:
        with db_cursor() as cur:
            cur.execute("SELECT id FROM unified_files WHERE id=%s LIMIT 1", (root_id,))
            row = cur.fetchone()
            if not row:
                return []
            related.add(str(row[0]))

            cur.execute("SELECT id FROM unified_files WHERE original_file_id=%s", (root_id,))
            for (child_id,) in cur.fetchall() or []:
                related.add(str(child_id))
    except Exception:
        logger.exception("Failed to fetch related file ids for %s", root_id)
        related.add(str(root_id))

    return sorted(related)


def clear_logs_for_file_ids(file_ids: List[str]) -> Dict[str, int]:
    """
    Delete workflow and AI history logs for the provided file IDs.

    Returns counts for deleted workflow_runs, workflow_stage_runs and ai_history rows.
    """
    cleaned_counts = {"workflow_runs": 0, "workflow_stage_runs": 0, "ai_history": 0}
    if db_cursor is None or not file_ids:
        return cleaned_counts

    placeholders = ", ".join(["%s"] * len(file_ids))
    try:
        with db_cursor() as cur:
            cur.execute(
                f"SELECT id FROM workflow_runs WHERE file_id IN ({placeholders})",
                tuple(file_ids),
            )
            run_rows = cur.fetchall() or []
    except Exception:
        logger.exception("Failed to fetch workflow run ids for cleanup")
        run_rows = []

    workflow_run_ids = [int(row[0]) for row in run_rows]

    if workflow_run_ids:
        run_placeholders = ", ".join(["%s"] * len(workflow_run_ids))
        try:
            with db_cursor() as cur:
                cur.execute(
                    f"DELETE FROM workflow_stage_runs WHERE workflow_run_id IN ({run_placeholders})",
                    tuple(workflow_run_ids),
                )
                cleaned_counts["workflow_stage_runs"] = cur.rowcount or 0
        except Exception:
            logger.exception("Failed to delete workflow_stage_runs for %s", workflow_run_ids)

    try:
        with db_cursor() as cur:
            cur.execute(
                f"DELETE FROM workflow_runs WHERE file_id IN ({placeholders})",
                tuple(file_ids),
            )
            cleaned_counts["workflow_runs"] = cur.rowcount or 0
    except Exception:
        logger.exception("Failed to delete workflow_runs for files %s", file_ids)

    try:
        with db_cursor() as cur:
            cur.execute(
                f"DELETE FROM ai_processing_history WHERE file_id IN ({placeholders})",
                tuple(file_ids),
            )
            cleaned_counts["ai_history"] = cur.rowcount or 0
    except Exception:
        logger.exception("Failed to delete ai_processing_history for files %s", file_ids)

    return cleaned_counts
