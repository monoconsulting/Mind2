from __future__ import annotations

import logging
from typing import Any, Optional

from .common import db_cursor, set_ai_status

logger = logging.getLogger(__name__)


def get_workflow_run(workflow_run_id: int) -> dict[str, Any] | None:
    """Load workflow_run by ID."""
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, workflow_key, source_channel, file_id, content_hash,
                       current_stage, status, created_at, updated_at
                FROM workflow_runs
                WHERE id = %s
                """,
                (workflow_run_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "workflow_key": row[1],
            "source_channel": row[2],
            "file_id": row[3],
            "content_hash": row[4],
            "current_stage": row[5],
            "status": row[6],
            "created_at": row[7],
            "updated_at": row[8],
        }
    except Exception:
        return None


def get_workflow_stage(workflow_run_id: int, stage_key: str) -> dict[str, Any] | None:
    """Load a specific workflow_stage_run by workflow_run_id and stage_key."""
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, stage_key, status, started_at, finished_at, message FROM workflow_stage_runs "
                "WHERE workflow_run_id = %s AND stage_key = %s",
                (workflow_run_id, stage_key),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "stage_key": row[1],
            "status": row[2],
            "started_at": row[3],
            "finished_at": row[4],
            "message": row[5],
        }
    except Exception:
        return None


def mark_stage(
    workflow_run_id: int,
    stage_key: str,
    status: str,
    message: str | None = None,
    start: bool = False,
    end: bool = False,
    update_workflow_status: bool = True,
    workflow_status_override: str | None = None,
) -> bool:
    """Insert/update workflow_stage_runs and bump workflow_runs.current_stage/status."""
    if db_cursor is None:
        return False

    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM workflow_stage_runs WHERE workflow_run_id=%s AND stage_key=%s",
                (workflow_run_id, stage_key),
            )
            existing = cur.fetchone()

            if existing:
                stage_id = existing[0]
                updates = ["status=%s"]
                params: list[Any] = [status]

                if message is not None:
                    updates.append("message=%s")
                    params.append(message[:200] if message else None)
                if start:
                    updates.append("started_at=NOW()")
                if end:
                    updates.append("finished_at=NOW()")

                params.append(stage_id)
                cur.execute(
                    f"UPDATE workflow_stage_runs SET {', '.join(updates)} WHERE id=%s",
                    tuple(params),
                )
            else:
                started_at_val = "NOW()" if start else "NULL"
                finished_at_val = "NOW()" if end else "NULL"
                cur.execute(
                    f"""
                    INSERT INTO workflow_stage_runs
                    (workflow_run_id, stage_key, status, started_at, finished_at, message)
                    VALUES (%s, %s, %s, {started_at_val}, {finished_at_val}, %s)
                    """,
                    (workflow_run_id, stage_key, status, message[:200] if message else None),
                )

            workflow_status = workflow_status_override
            if workflow_status is None:
                workflow_status = "running"
                if status == "failed":
                    workflow_status = "failed"
                elif status == "skipped":
                    workflow_status = "canceled"

            if update_workflow_status:
                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET current_stage=%s, status=%s, updated_at=NOW()
                    WHERE id=%s
                    """,
                    (stage_key, workflow_status, workflow_run_id),
                )

        return True
    except Exception:
        return False


_IMPORT_STAGE_WITH_BOUNDARIES = {
    "src_portal",
    "src_ftp",
    "src_fc",
    "ingest_store",
    "ingest_wf1",
    "fc_create",
    "fc_ocr",
    "fc_parse",
    "fc_ready",
    "detect_type",
    "r_ocr",
    "r_ai3",
    "r_ai4",
    "r_persist",
    "r_queue_match",
    "ai5",
    "m_link",
    "m_unmatched",
    "finalize_ok",
    "finalize_fail",
}


def _log_import_stage(
    workflow_run_id: Optional[int],
    stage_key: str,
    status: str,
    *,
    message: str | None = None,
    start: bool = False,
    end: bool = False,
) -> None:
    if workflow_run_id is None:
        return
    try:
        mark_stage(
            workflow_run_id,
            stage_key,
            status,
            message=message,
            start=start,
            end=end,
            update_workflow_status=False,
        )
    except Exception:
        logger.debug("Failed to log import stage %s for workflow %s", stage_key, workflow_run_id)


def begin_import_stage(workflow_run_id: Optional[int], stage_base: str, *, message: str | None = None) -> None:
    """Log the start of a high-level import stage (with optional boundary nodes)."""

    if stage_base in _IMPORT_STAGE_WITH_BOUNDARIES:
        _log_import_stage(
            workflow_run_id,
            f"{stage_base}_start",
            "succeeded",
            message=message,
            start=True,
            end=True,
        )
    _log_import_stage(workflow_run_id, stage_base, "running", message=message, start=True)

    if stage_base in ("src_portal", "src_ftp", "src_fc"):
        wfr = get_workflow_run(workflow_run_id)
        if wfr and wfr.get("file_id"):
            set_ai_status(wfr["file_id"], "processing")
            logger.info(
                "Set ai_status='processing' for file_id=%s at stage=%s",
                wfr["file_id"],
                stage_base,
            )


def complete_import_stage(
    workflow_run_id: Optional[int],
    stage_base: str,
    *,
    success: bool = True,
    message: str | None = None,
) -> None:
    """Log completion of an import stage and annotate boundary markers if applicable."""

    status = "succeeded" if success else "failed"
    _log_import_stage(workflow_run_id, stage_base, status, message=message, end=True)
    if stage_base in _IMPORT_STAGE_WITH_BOUNDARIES:
        _log_import_stage(
            workflow_run_id,
            f"{stage_base}_end",
            status,
            message=message,
            start=True,
            end=True,
        )

    if stage_base == "finalize_ok" and success:
        wfr = get_workflow_run(workflow_run_id)
        if wfr and wfr.get("file_id"):
            set_ai_status(wfr["file_id"], "completed")
            logger.info(
                "Set ai_status='completed' for file_id=%s after finalize_ok",
                wfr["file_id"],
            )


def log_import_decision(
    workflow_run_id: Optional[int],
    stage_key: str,
    *,
    success: bool,
    message: str | None = None,
) -> None:
    """Log decision nodes such as fc_is_fc or m_found."""

    status = "succeeded" if success else "failed"
    _log_import_stage(workflow_run_id, stage_key, status, message=message, start=True, end=True)


def log_import_event(
    workflow_run_id: Optional[int],
    stage_key: str,
    *,
    status: str = "succeeded",
    message: str | None = None,
) -> None:
    """Log instantaneous stages such as manual_review or KLAR."""

    _log_import_stage(workflow_run_id, stage_key, status, message=message, start=True, end=True)


def log_finalize_failure(workflow_run_id: Optional[int], reason: str) -> None:
    """Convenience helper for finalize_fail stage logging."""

    begin_import_stage(workflow_run_id, "finalize_fail", message=reason)
    complete_import_stage(workflow_run_id, "finalize_fail", success=False, message=reason)


def ensure_workflow(workflow_run_id: int, expected_prefix: str) -> dict[str, Any]:
    """Guard to ensure a task is running in the correct workflow."""

    wfr = get_workflow_run(workflow_run_id)
    if not wfr:
        raise ValueError(f"Workflow run {workflow_run_id} not found.")

    workflow_key = wfr.get("workflow_key", "")
    if not workflow_key.startswith(expected_prefix):
        task_name = "unknown_task"
        try:
            from celery import current_task

            if current_task:
                task_name = current_task.name
        except Exception:
            pass

        message = (
            f"Task '{task_name}' belongs to '{expected_prefix}' "
            f"but was triggered by workflow '{workflow_key}' ({workflow_run_id})."
        )
        mark_stage(
            workflow_run_id=workflow_run_id,
            stage_key="guard",
            status="skipped",
            message=message,
        )
        raise RuntimeError("Workflow/task mismatch.")

    return wfr


__all__ = [
    "begin_import_stage",
    "complete_import_stage",
    "ensure_workflow",
    "get_workflow_run",
    "get_workflow_stage",
    "log_finalize_failure",
    "log_import_decision",
    "log_import_event",
    "mark_stage",
]
