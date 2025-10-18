from __future__ import annotations

import json
import os
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Any, Iterable
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from api.middleware import auth_required
from services.file_detection import detect_file
from services.storage import FileStorage
from services.tasks import dispatch_workflow
from services.workflow_runs import create_workflow_run
from services.db.files import (
    list_unprocessed,
    insert_unified_file,
    update_other_data,
    DuplicateFileError,
)
from services.db.connection import db_cursor

logger = logging.getLogger(__name__)

INSERT_HISTORY_SQL = '''
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
'''

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
) -> None:
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                INSERT_HISTORY_SQL,
                (
                    file_id,
                    job,
                    status,
                    ai_stage_name,
                    log_text,
                    error_message,
                    confidence,
                    processing_time_ms,
                    provider,
                    model_name,
                ),
            )
    except Exception:
        pass

def _hash_exists(content_hash: str) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM unified_files WHERE content_hash = %s LIMIT 1",
                (content_hash,),
            )
            return cur.fetchone() is not None
    except Exception:
        return False

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

            if _hash_exists(file_hash):
                logger.warning(f"File {idx}: SKIPPED - Duplicate detected: {safe_filename}")
                skipped_count += 1
                continue

            detection = detect_file(data, safe_filename)
            
            workflow_key = None
            if detection.kind == "image":
                workflow_key = "WF1_RECEIPT"
            elif detection.kind == "pdf":
                workflow_key = "WF2_PDF_SPLIT"
            
            if not workflow_key:
                logger.warning(f"File {idx}: SKIPPED - Unsupported file type for workflow: {detection.kind}")
                errors.append(f"Unsupported file type: {safe_filename}")
                continue

            insert_unified_file(
                file_id=file_id,
                file_type=detection.kind,
                content_hash=file_hash,
                submitted_by=submitted_by,
                original_filename=safe_filename,
                ai_status="processing",
                mime_type=detection.mime_type,
                file_suffix=Path(safe_filename).suffix,
                original_file_id=file_id,
                original_file_name=safe_filename,
                original_file_size=len(data),
                other_data={"detected_kind": detection.kind, "source": "web_upload"},
            )
            fs.save_original(file_id, safe_filename, data)

            workflow_run_id = create_workflow_run(
                workflow_key=workflow_key,
                source_channel="web_upload",
                file_id=file_id,
                content_hash=file_hash
            )

            if workflow_run_id and dispatch_workflow:
                dispatch_workflow(workflow_run_id)
                logger.info(f"File {idx}: Dispatched {workflow_key} run {workflow_run_id} for file {file_id}")
                uploaded_count += 1
            else:
                raise RuntimeError(f"Failed to create or dispatch workflow for file {file_id}")

        except DuplicateFileError:
            logger.warning(f"File {idx}: SKIPPED - Duplicate file (hash={file_hash[:16]}...)")
            skipped_count += 1
        except Exception as e:
            error_msg = f"File processing error for {file.filename}: {str(e)}"
            logger.error(f"File {idx}: ERROR - {error_msg}", exc_info=True)
            errors.append(error_msg)
            continue

    logger.info(f"=== UPLOAD REQUEST COMPLETE === Uploaded: {uploaded_count}, Skipped: {skipped_count}, Errors: {len(errors)}")

    if errors:
        return jsonify({"ok": False, "uploaded": uploaded_count, "skipped": skipped_count, "errors": errors}), 500

    return jsonify({"ok": True, "uploaded": uploaded_count, "skipped": skipped_count}), 200
