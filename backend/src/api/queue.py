from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request

from api.middleware import auth_required
from services.db.connection import db_cursor
from config import config

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
                WHERE wr.status IN ('running', 'queued')
                  AND uf.deleted_at IS NULL

                UNION ALL

                SELECT
                    NULL as id,
                    uf.workflow_type as workflow_key,
                    'orphan_file' as source_channel,
                    uf.id as file_id,
                    uf.content_hash,
                    'unknown' as current_stage,
                    'orphan' as status,
                    uf.created_at,
                    uf.updated_at,
                    TIMESTAMPDIFF(SECOND, uf.updated_at, NOW()) AS idle_seconds,
                    uf.original_filename,
                    uf.ai_status,
                    NULL as latest_stage_key,
                    NULL as latest_stage_status,
                    NULL as latest_stage_updated_at
                FROM unified_files uf
                LEFT JOIN workflow_runs wr ON wr.file_id = uf.id
                WHERE wr.id IS NULL
                  AND uf.ai_status IN ('uploaded', 'processing', 'ocr_done', 'ocr_failed', 'manual_review')
                  AND uf.deleted_at IS NULL

                ORDER BY
                    CASE status
                        WHEN 'running' THEN 0
                        WHEN 'queued' THEN 1
                        WHEN 'orphan' THEN 2
                        ELSE 3
                    END,
                    CASE status
                        WHEN 'running' THEN updated_at
                        WHEN 'queued' THEN created_at
                        WHEN 'orphan' THEN created_at
                        ELSE updated_at
                    END DESC
                """
            )
            rows = cur.fetchall() or []

            def derive_ai_status(raw_ai_status, wf_status, latest_key, latest_status):
                if wf_status == "failed":
                    return "failed"
                if latest_key in ("KLAR", "finalize_ok") and latest_status == "succeeded":
                    return "completed"
                if latest_key and "ocr" in (latest_key or "") and latest_status == "succeeded":
                    return "ocr_done"
                if wf_status in ("running", "queued"):
                    return "processing"
                return raw_ai_status or "uploaded"

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

                stall_threshold = config.QUEUE_STALL_THRESHOLD_SECONDS
                derived_ai_status = derive_ai_status(ai_status, status, latest_stage_key, latest_stage_status)
                stalled = status == "running" and idle_seconds is not None and idle_seconds > stall_threshold
                is_orphan = run_id is None and file_id is not None

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
                        "derived_ai_status": derived_ai_status,
                        "latest_stage_key": latest_stage_key,
                        "latest_stage_status": latest_stage_status,
                        "latest_stage_updated_at": latest_stage_updated_at.isoformat()
                        if hasattr(latest_stage_updated_at, "isoformat")
                        else latest_stage_updated_at,
                        "stalled": stalled,
                        "stall_threshold_seconds": stall_threshold,
                        "is_orphan": is_orphan,
                        "can_resume": bool((is_orphan and file_id) or (stalled and file_id)),
                    }
                )
    except Exception as exc:
        logger.exception("Failed to load queue: %s", exc)
        return jsonify({"items": [], "meta": {"total": 0, "error": "db_error"}}), 500

    return jsonify({"items": items, "meta": {"total": len(items)}}), 200


@queue_bp.post("/resume-batch")
@auth_required
def resume_batch():
    """Resume multiple workflow items by delegating to the existing single-file resume logic."""
    payload = request.get_json(silent=True) or {}
    file_ids = payload.get("file_ids") if isinstance(payload, dict) else None

    if not isinstance(file_ids, list) or not file_ids:
        return jsonify({"error": "invalid_input", "message": "file_ids must be a non-empty list"}), 400

    from api.ingest import _resume_processing_internal

    results = []
    seen = set()
    for fid in file_ids:
        if not fid or fid in seen:
            continue
        seen.add(fid)
        data, status_code = _resume_processing_internal(str(fid))
        results.append(
            {
                "file_id": str(fid),
                "queued": data.get("queued", False),
                "workflow_run_id": data.get("workflow_run_id"),
                "workflow_key": data.get("workflow_key"),
                "status_code": status_code,
                "error": data.get("error"),
                "message": data.get("message"),
            }
        )

    return jsonify({"results": results, "count": len(results)}), 200
