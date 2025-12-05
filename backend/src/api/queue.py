from __future__ import annotations

import logging
from flask import Blueprint, jsonify

from api.middleware import auth_required
from services.db.connection import db_cursor

queue_bp = Blueprint("queue", __name__, url_prefix="/queue")
logger = logging.getLogger(__name__)


@queue_bp.get("/")
@auth_required
def list_queue():
    """
    Return ordered queue of workflow_runs.

    Order:
    - running first (updated_at desc)
    - queued next (created_at asc)
    - everything else by updated_at desc
    """
    if db_cursor is None:
        return jsonify({"items": [], "meta": {"total": 0}}), 503

    items = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    wr.id,
                    wr.workflow_key,
                    wr.source_channel,
                    wr.file_id,
                    wr.content_hash,
                    wr.current_stage,
                    wr.status,
                    wr.created_at,
                    wr.updated_at,
                    TIMESTAMPDIFF(SECOND, wr.updated_at, NOW()) AS idle_seconds,
                    uf.original_filename,
                    uf.ai_status,
                    (
                        SELECT wsr.stage_key
                          FROM workflow_stage_runs wsr
                         WHERE wsr.workflow_run_id = wr.id
                         ORDER BY wsr.started_at DESC, wsr.id DESC
                         LIMIT 1
                    ) AS latest_stage_key,
                    (
                        SELECT wsr.status
                          FROM workflow_stage_runs wsr
                         WHERE wsr.workflow_run_id = wr.id
                         ORDER BY wsr.started_at DESC, wsr.id DESC
                         LIMIT 1
                    ) AS latest_stage_status,
                    (
                        SELECT COALESCE(wsr.finished_at, wsr.started_at)
                          FROM workflow_stage_runs wsr
                         WHERE wsr.workflow_run_id = wr.id
                         ORDER BY wsr.started_at DESC, wsr.id DESC
                         LIMIT 1
                    ) AS latest_stage_updated_at
                FROM workflow_runs wr
                LEFT JOIN unified_files uf ON uf.id = wr.file_id
                ORDER BY
                    CASE wr.status
                        WHEN 'running' THEN 0
                        WHEN 'queued' THEN 1
                        ELSE 2
                    END,
                    CASE wr.status
                        WHEN 'running' THEN wr.updated_at
                        WHEN 'queued' THEN wr.created_at
                        ELSE wr.updated_at
                    END DESC
                """
            )
            rows = cur.fetchall() or []
            for row in rows:
                (
                    run_id,
                    workflow_key,
                    source_channel,
                    file_id,
                    content_hash,
                    current_stage,
                    status,
                    created_at,
                    updated_at,
                    idle_seconds,
                    original_filename,
                    ai_status,
                    latest_stage_key,
                    latest_stage_status,
                    latest_stage_updated_at,
                ) = row

                stalled = False
                try:
                    stalled = status in ("queued", "running") and idle_seconds is not None and idle_seconds > 300
                except Exception:
                    stalled = False

                items.append(
                    {
                        "id": run_id,
                        "workflow_key": workflow_key,
                        "source_channel": source_channel,
                        "file_id": file_id,
                        "content_hash": content_hash,
                        "current_stage": current_stage,
                        "status": status,
                        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
                        "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
                        "idle_seconds": idle_seconds,
                        "file_name": original_filename,
                        "ai_status": ai_status,
                        "latest_stage_key": latest_stage_key,
                        "latest_stage_status": latest_stage_status,
                        "latest_stage_updated_at": latest_stage_updated_at.isoformat()
                        if hasattr(latest_stage_updated_at, "isoformat")
                        else latest_stage_updated_at,
                        "stalled": stalled,
                    }
                )
    except Exception as exc:
        logger.exception("Failed to load queue: %s", exc)
        return jsonify({"items": [], "meta": {"total": 0, "error": "db_error"}}), 500

    return jsonify({"items": items, "meta": {"total": len(items)}}), 200
