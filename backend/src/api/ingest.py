from __future__ import annotations

import json
import os
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from api.middleware import auth_required
from services.file_detection import detect_file
from services.storage import FileStorage
from services.tasks import (
    begin_import_stage,
    complete_import_stage,
    dispatch_workflow,
    log_import_event,
    mark_stage,
)
from services.workflow_runs import create_workflow_run
from services.db.files import (
    list_unprocessed,
    create_unified_file,
    update_other_data,
    DuplicateFileError,
    set_ai_status,
)
from services.db.connection import db_cursor
from services.ai_logging import log_ai_call

logger = logging.getLogger(__name__)

# Deprecated local history helper; uses unified log_ai_call in services.ai_logging
_history = log_ai_call

def _find_file_id_by_hash(content_hash: str) -> str | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM unified_files WHERE content_hash = %s LIMIT 1",
                (content_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return str(row[0])
    except Exception:
        return None

ingest_bp = Blueprint("ingest", __name__)

@ingest_bp.post("/ingest/upload")
@auth_required
def upload_files() -> Any:
    """Upload files, create a workflow_run, and dispatch it."""
    logger.info("=== UPLOAD REQUEST START (New Workflow) ===")
    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "no_files"}), 400

    uploaded_count = 0
    skipped_count = 0
    duplicates: list[dict[str, Any]] = []
    errors = []

    storage_dir = os.getenv('STORAGE_DIR', '/data/storage')
    fs = FileStorage(storage_dir)
    submitted_by = request.headers.get('X-User') or 'upload'

    for idx, file in enumerate(files, 1):
        if not file or not file.filename:
            continue

        logger.info(f"File {idx}/{len(files)}: Processing '{file.filename}'")
        
        try:
            data = file.read()
            file_hash = hashlib.sha256(data).hexdigest()
            file_id = str(uuid.uuid4())
            safe_filename = secure_filename(file.filename)

            existing_file_id = _find_file_id_by_hash(file_hash)
            if existing_file_id:
                logger.info(
                    "File %s: Already imported (duplicate hash=%s...): %s -> %s",
                    idx,
                    file_hash[:16],
                    safe_filename,
                    existing_file_id,
                )
                duplicates.append(
                    {
                        "status": "already_imported",
                        "original_filename": safe_filename,
                        "file_id": existing_file_id,
                    }
                )
                skipped_count += 1
                continue

            detection = detect_file(data, safe_filename)
            
            workflow_key = None
            workflow_type = "receipt"
            if detection.kind == "image":
                workflow_key = "WF1_RECEIPT"
            elif detection.kind == "pdf":
                workflow_key = "WF2_PDF_SPLIT"
            
            if not workflow_key:
                logger.warning(f"File {idx}: SKIPPED - Unsupported file type for workflow: {detection.kind}")
                errors.append(f"Unsupported file type: {safe_filename}")
                continue

            unified_file = create_unified_file(
                file_id=file_id,
                file_type=detection.kind,
                content_hash=file_hash,
                submitted_by=submitted_by,
                original_filename=safe_filename,
                initial_ai_status="processing",
                mime_type=detection.mime_type,
                file_suffix=Path(safe_filename).suffix,
                original_file_id=file_id,
                original_file_name=safe_filename,
                original_file_size=len(data),
                extra_metadata={"detected_kind": detection.kind},
                source="web_upload",
                workflow_key=workflow_key,
                workflow_type=workflow_type,
            )
            fs.save_original(file_id, safe_filename, data)
            if detection.kind == "image":
                allowed_suffixes = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
                image_suffix = Path(safe_filename).suffix.lower()
                if image_suffix not in allowed_suffixes:
                    mime = str(detection.mime_type or "").lower()
                    suffix_by_mime = {
                        "image/jpeg": ".jpg",
                        "image/jpg": ".jpg",
                        "image/png": ".png",
                        "image/tiff": ".tiff",
                    }
                    image_suffix = suffix_by_mime.get(mime, "")
                if image_suffix in allowed_suffixes:
                    try:
                        fs.save(file_id, f"page-0001{image_suffix}", data)
                    except Exception as exc:
                        logger.warning(
                            "Failed to save page copy for image upload %s (%s): %s",
                            safe_filename,
                            file_id,
                            exc,
                        )
                else:
                    logger.warning(
                        "Skipping page copy for unsupported image type %s (mime=%s)",
                        safe_filename,
                        detection.mime_type,
                    )

            workflow_run_id = unified_file.workflow_run_id

            if workflow_run_id:
                begin_import_stage(
                    workflow_run_id,
                    "src_portal",
                    message=f"Fil {safe_filename} ({len(data)} bytes)",
                )
                complete_import_stage(
                    workflow_run_id,
                    "src_portal",
                    success=True,
                    message="Portaluppladdning klar",
                )
                begin_import_stage(
                    workflow_run_id,
                    "ingest_store",
                    message=f"Skrev unified_files {file_id}",
                )
                complete_import_stage(
                    workflow_run_id,
                    "ingest_store",
                    success=True,
                    message="Lagrade metadata i databasen",
                )
                if workflow_key == "WF1_RECEIPT":
                    begin_import_stage(
                        workflow_run_id,
                        "ingest_wf1",
                        message="Skapar WF1 workflow_run",
                    )

            if workflow_run_id and dispatch_workflow:
                dispatch_workflow(workflow_run_id)
                if workflow_key == "WF1_RECEIPT":
                    complete_import_stage(
                        workflow_run_id,
                        "ingest_wf1",
                        success=True,
                        message="WF1 dispatchad",
                    )
                logger.info(f"File {idx}: Dispatched {workflow_key} run {workflow_run_id} for file {file_id}")
                uploaded_count += 1
            else:
                if workflow_run_id and workflow_key == "WF1_RECEIPT":
                    complete_import_stage(
                        workflow_run_id,
                        "ingest_wf1",
                        success=False,
                        message="Kunde inte skapa WF1",
                    )
                raise RuntimeError(f"Failed to create or dispatch workflow for file {file_id}")

        except DuplicateFileError:
            existing_file_id = _find_file_id_by_hash(file_hash)
            logger.info(
                "File %s: Already imported (duplicate hash=%s...): %s -> %s",
                idx,
                file_hash[:16],
                safe_filename,
                existing_file_id,
            )
            duplicates.append(
                {
                    "status": "already_imported",
                    "original_filename": safe_filename,
                    "file_id": existing_file_id,
                }
            )
            skipped_count += 1
        except Exception as e:
            error_msg = f"File processing error for {file.filename}: {str(e)}"
            logger.error(f"File {idx}: ERROR - {error_msg}", exc_info=True)
            errors.append(error_msg)
            continue

    logger.info(f"=== UPLOAD REQUEST COMPLETE === Uploaded: {uploaded_count}, Skipped: {skipped_count}, Errors: {len(errors)}")

    if errors:
        return (
            jsonify(
                {
                    "ok": False,
                    "uploaded": uploaded_count,
                    "skipped": skipped_count,
                    "duplicates": duplicates,
                    "errors": errors,
                }
            ),
            500,
        )

    return jsonify({"ok": True, "uploaded": uploaded_count, "skipped": skipped_count, "duplicates": duplicates}), 200


def _parse_other_data(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        logger.warning("Failed to parse other_data payload during resume request")
        return {}


def _resolve_resume_workflow(
    *,
    file_type: Optional[str],
    workflow_type: Optional[str],
    other_data: dict[str, Any],
) -> Optional[str]:
    """Infer which workflow should handle the resume action."""
    wft = (workflow_type or "").lower()
    if wft == "creditcard_invoice":
        return "WF3_FIRSTCARD_INVOICE"

    detected_kind = (other_data.get("detected_kind") or "").lower()
    file_type_norm = (file_type or "").lower()

    if detected_kind in {"pdf", "document"} or file_type_norm in {"pdf"}:
        return "WF2_PDF_SPLIT"

    return "WF1_RECEIPT"


def _resume_processing_internal(file_id: str) -> Tuple[dict[str, Any], int]:
    """
    Shared resume logic used by both the single-file and batch resume endpoints.
    Returns (payload, status_code) without Flask response wrapping.
    """
    if not file_id:
        return {"queued": False, "error": "missing_file_id"}, 400

    if db_cursor is None:
        return {"queued": False, "error": "database_unavailable"}, 503

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       content_hash,
                       file_type,
                       workflow_type,
                       other_data,
                       ai_status
                  FROM unified_files
                 WHERE id = %s AND deleted_at IS NULL
                """,
                (file_id,),
            )
            row = cur.fetchone()
    except Exception as exc:
        logger.error("Resume lookup failed for %s: %s", file_id, exc, exc_info=True)
        return {"queued": False, "error": "database_error"}, 500

    if not row:
        return {"queued": False, "error": "not_found"}, 404

    (
        _fid,
        content_hash,
        file_type,
        workflow_type,
        other_data_raw,
        current_status,
    ) = row

    other_data = _parse_other_data(other_data_raw)
    workflow_key = _resolve_resume_workflow(
        file_type=file_type,
        workflow_type=workflow_type,
        other_data=other_data,
    )

    if not workflow_key:
        logger.error(
            "Unable to determine workflow for resume (file_id=%s, file_type=%s, workflow_type=%s)",
            file_id,
            file_type,
            workflow_type,
        )
        return {"queued": False, "error": "unknown_workflow"}, 400

    effective_hash = content_hash or other_data.get("content_hash") or file_id

    from services.workflow_runs import get_active_workflow_run

    existing_run_id = get_active_workflow_run(file_id, workflow_key)
    if existing_run_id:
        logger.info(
            "Resume: Found existing active workflow_run %s for file_id=%s, reusing it",
            existing_run_id,
            file_id,
        )
        workflow_run_id = existing_run_id
        try:
            set_ai_status(file_id, "processing")
        except Exception as exc:
            logger.warning("Failed to set ai_status=processing for %s on resume: %s", file_id, exc)
    else:
        workflow_run_id = create_workflow_run(
            workflow_key=workflow_key,
            source_channel="manual_resume",
            file_id=file_id,
            content_hash=effective_hash,
        )

        if not workflow_run_id:
            logger.error("Failed to create workflow run for resume (file_id=%s)", file_id)
            return {"queued": False, "error": "workflow_creation_failed"}, 500

        try:
            set_ai_status(file_id, "processing")
        except Exception as exc:
            logger.warning("Failed to set ai_status=processing for %s on resume (new run): %s", file_id, exc)

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE workflow_runs
                   SET status='running',
                       current_stage='resume_dispatch',
                       updated_at=NOW()
                 WHERE id=%s
                """,
                (workflow_run_id,),
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to bump workflow_run status on resume (id=%s): %s", workflow_run_id, exc)

    try:
        log_import_event(
            workflow_run_id,
            "resume_dispatch",
            status="running",
            message=f"Återupptar bearbetning (tidigare status: {current_status})",
        )
        mark_stage(
            workflow_run_id,
            "resume_dispatch",
            "running",
            update_workflow_status=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to log resume_dispatch for %s: %s", workflow_run_id, exc)

    if dispatch_workflow:
        try:
            dispatch_ok = dispatch_workflow(workflow_run_id)
            if not dispatch_ok:
                logger.error("Dispatch workflow failed for resume (id=%s)", workflow_run_id)
                mark_stage(
                    workflow_run_id,
                    "resume_dispatch",
                    "failed",
                    message="Dispatch failed on resume",
                    update_workflow_status=True,
                    workflow_status_override="failed",
                )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Dispatch workflow raised for resume (id=%s): %s", workflow_run_id, exc, exc_info=True)
            mark_stage(
                workflow_run_id,
                "resume_dispatch",
                "failed",
                message=f"Dispatch exception: {exc}",
                update_workflow_status=True,
                workflow_status_override="failed",
            )

    try:
        _history(
            file_id=file_id,
            job="resume",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("History logging failed for resume %s: %s", file_id, exc)

    message = "Bearbetning återupptagen"
    action = f"{workflow_key} run {workflow_run_id}"

    return (
        {
            "queued": True,
            "file_id": file_id,
            "workflow_key": workflow_key,
            "workflow_run_id": workflow_run_id,
            "status": "processing",
            "message": message,
            "action": action,
            "previous_status": current_status,
        },
        200,
    )


@ingest_bp.post("/ingest/process/<file_id>/resume")
@auth_required
def resume_processing(file_id: str) -> Any:
    """Re-dispatch processing for an existing receipt or invoice."""
    payload, status_code = _resume_processing_internal(file_id)
    return jsonify(payload), status_code
