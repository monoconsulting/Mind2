from __future__ import annotations

import os
import uuid
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Any
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from api.middleware import auth_required
from services.queue_manager import get_celery
from services.storage import FileStorage

logger = logging.getLogger(__name__)
try:
    from services.tasks import process_ocr, process_classification, process_ai_pipeline  # type: ignore
except Exception:  # pragma: no cover - allow running without Celery in tests/dev
    process_ocr = None  # type: ignore
    process_classification = None  # type: ignore
    process_ai_pipeline = None  # type: ignore
try:
    from services.db.files import list_unprocessed
except Exception:  # pragma: no cover
    list_unprocessed = lambda limit=50: []  # type: ignore
try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


INSERT_HISTORY_SQL = """
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


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
    """Log processing history with detailed information."""
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
        # best-effort history
        pass


ingest_bp = Blueprint("ingest", __name__)


@ingest_bp.post("/ingest/queue-new")
@auth_required
def queue_new():
    limit = int(request.args.get("limit", 10))
    ids = list_unprocessed(limit=limit)
    enqueued = []
    for fid in ids:
        try:
            if process_ocr is None:
                raise RuntimeError("tasks_unavailable")
            process_ocr.delay(fid)  # type: ignore[attr-defined]
            enqueued.append(fid)
        except Exception:
            pass
    return jsonify({"enqueued": enqueued}), 200


@ingest_bp.post("/ingest/process/<fid>/ocr")
@auth_required
def trigger_ocr(fid: str):
    try:
        if process_ocr is None:
            raise RuntimeError("tasks_unavailable")
        r = process_ocr.delay(fid)  # type: ignore[attr-defined]
    except Exception:
        return jsonify({"queued": False}), 500
    return jsonify({"queued": True, "task_id": getattr(r, "id", None)}), 200


@ingest_bp.post("/ingest/process/<fid>/classify")
@auth_required
def trigger_classify(fid: str):
    try:
        if process_classification is None:
            raise RuntimeError("tasks_unavailable")
        r = process_classification.delay(fid)  # type: ignore[attr-defined]
    except Exception:
        return jsonify({"queued": False}), 500
    return jsonify({"queued": True, "task_id": getattr(r, "id", None)}), 200


@ingest_bp.post("/ingest/process/<fid>/resume")
@auth_required
def resume_processing(fid: str):
    """Resume processing from the point where it failed or stopped."""
    try:
        # Check processing history to find where it stopped
        if db_cursor is None:
            return jsonify({"error": "db_unavailable"}), 500

        last_status = None
        last_job_type = None

        with db_cursor() as cur:
            cur.execute(
                """
                SELECT job_type, status
                FROM ai_processing_history
                WHERE file_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (fid,)
            )
            row = cur.fetchone()
            if row:
                last_job_type, last_status = row

        # Determine next step based on last job type and status
        if last_status == "error":
            # If any error, determine where to restart from
            if last_job_type in ("upload", "ocr"):
                # Restart from OCR
                if process_ocr is None:
                    raise RuntimeError("tasks_unavailable")
                r = process_ocr.delay(fid)  # type: ignore[attr-defined]
                return jsonify({
                    "queued": True,
                    "task_id": getattr(r, "id", None),
                    "resumed_from": last_job_type,
                    "action": "restart_from_ocr"
                }), 200
            elif last_job_type in ("ai1", "ai2", "ai3", "ai4", "ai5", "ai_pipeline"):
                # Restart AI pipeline (OCR already done)
                if process_ai_pipeline is None:
                    raise RuntimeError("tasks_unavailable")
                r = process_ai_pipeline.delay(fid)  # type: ignore[attr-defined]
                return jsonify({
                    "queued": True,
                    "task_id": getattr(r, "id", None),
                    "resumed_from": last_job_type,
                    "action": "restart_ai_pipeline"
                }), 200
            else:
                # Unknown error, restart from OCR
                if process_ocr is None:
                    raise RuntimeError("tasks_unavailable")
                r = process_ocr.delay(fid)  # type: ignore[attr-defined]
                return jsonify({
                    "queued": True,
                    "task_id": getattr(r, "id", None),
                    "resumed_from": last_job_type or "unknown",
                    "action": "restart_from_ocr"
                }), 200
        elif last_job_type == "ocr" and last_status == "success":
            # OCR succeeded, continue to AI pipeline
            if process_ai_pipeline is None:
                raise RuntimeError("tasks_unavailable")
            r = process_ai_pipeline.delay(fid)  # type: ignore[attr-defined]
            return jsonify({
                "queued": True,
                "task_id": getattr(r, "id", None),
                "resumed_from": last_job_type,
                "action": "continue_to_ai_pipeline"
            }), 200
        elif last_job_type == "upload" and last_status == "success":
            # Upload succeeded, start OCR
            if process_ocr is None:
                raise RuntimeError("tasks_unavailable")
            r = process_ocr.delay(fid)  # type: ignore[attr-defined]
            return jsonify({
                "queued": True,
                "task_id": getattr(r, "id", None),
                "resumed_from": last_job_type,
                "action": "continue_to_ocr"
            }), 200
        else:
            # Default: restart full pipeline
            if process_ocr is None:
                raise RuntimeError("tasks_unavailable")
            r = process_ocr.delay(fid)  # type: ignore[attr-defined]
            return jsonify({
                "queued": True,
                "task_id": getattr(r, "id", None),
                "resumed_from": last_job_type or "unknown",
                "action": "restart_pipeline"
            }), 200

    except Exception as e:
        logger.error(f"Error resuming processing for {fid}: {e}")
        return jsonify({"queued": False, "error": str(e)}), 500


@ingest_bp.post("/ingest/upload")
@auth_required
def upload_files() -> Any:
    """Upload files from form data and process them."""
    logger.info("=== UPLOAD REQUEST START ===")
    files = request.files.getlist('files')
    logger.info(f"Received {len(files) if files else 0} files in request")

    if not files:
        logger.warning("No files provided in upload request")
        return jsonify({"error": "no_files"}), 400

    uploaded_count = 0
    skipped_count = 0
    errors = []

    storage_dir = os.getenv('STORAGE_DIR', '/data/storage')
    fs = FileStorage(storage_dir)

    for idx, file in enumerate(files, 1):
        if not file or not file.filename:
            logger.warning(f"File {idx}: Skipping - no filename")
            continue

        logger.info(f"File {idx}/{len(files)}: Processing '{file.filename}'")

        try:
            # Read file data
            data = file.read()
            logger.info(f"File {idx}: Read {len(data)} bytes")

            # Calculate hash for duplicate detection
            file_hash = hashlib.sha256(data).hexdigest()
            logger.info(f"File {idx}: Hash calculated: {file_hash[:16]}...")

            receipt_id = str(uuid.uuid4())
            safe_filename = secure_filename(file.filename) if file.filename else f"upload_{receipt_id}.jpg"
            stored_filename = f"page-1{os.path.splitext(safe_filename)[1] or '.jpg'}"

            logger.info(f"File {idx}: Generated ID={receipt_id}, stored_filename={stored_filename}")

            # Insert into database with duplicate detection
            if db_cursor is not None:
                try:
                    with db_cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO unified_files (
                                id, file_type, ocr_raw, other_data, content_hash,
                                submitted_by, original_filename, ai_status, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            """,
                            (
                                receipt_id, 'receipt', '', '{}', file_hash,
                                (request.headers.get('X-User') or 'upload'), safe_filename, 'uploaded'
                            ),
                        )
                    logger.info(f"File {idx}: Database record created")

                    # Log successful upload
                    _history(
                        file_id=receipt_id,
                        job="upload",
                        status="success",
                        ai_stage_name="Upload-FileReceived",
                        log_text=f"File uploaded successfully: filename={safe_filename}, size={len(data)} bytes, hash={file_hash[:16]}..., user={request.headers.get('X-User') or 'upload'}",
                        provider="web_upload",
                    )
                except Exception as db_error:
                    # Check for duplicate hash
                    if 'Duplicate entry' in str(db_error) and 'idx_content_hash' in str(db_error):
                        logger.warning(f"File {idx}: SKIPPED - Duplicate file (hash={file_hash[:16]}...)")
                        skipped_count += 1
                        # Log duplicate
                        _history(
                            file_id=receipt_id,
                            job="upload",
                            status="error",
                            ai_stage_name="Upload-FileReceived",
                            log_text=f"Skipped duplicate file: hash={file_hash[:16]}..., filename={safe_filename}",
                            error_message="Duplicate file detected by content hash",
                            provider="web_upload",
                        )
                        continue
                    else:
                        raise

            # Save file to storage
            fs.save(receipt_id, stored_filename, data)
            logger.info(f"File {idx}: Saved to storage at {receipt_id}/{stored_filename}")

            # Queue OCR processing
            try:
                if process_ocr is not None:
                    process_ocr.delay(receipt_id)
                    logger.info(f"File {idx}: OCR task queued for {receipt_id}")
                else:
                    logger.warning(f"File {idx}: OCR not available, skipping queue")
            except Exception as e:
                logger.warning(f"File {idx}: OCR enqueue failed for {receipt_id}: {e}")

            uploaded_count += 1
            logger.info(f"File {idx}: SUCCESS - Uploaded as {receipt_id}")

        except Exception as e:
            error_msg = f"File processing error for {file.filename}: {str(e)}"
            logger.error(f"File {idx}: ERROR - {error_msg}")
            errors.append(error_msg)
            # Log upload error if we have a receipt_id
            if 'receipt_id' in locals():
                _history(
                    file_id=receipt_id,
                    job="upload",
                    status="error",
                    ai_stage_name="Upload-FileReceived",
                    log_text=f"Failed to upload file: filename={file.filename if file.filename else 'unknown'}",
                    error_message=f"{type(e).__name__}: {str(e)}",
                    provider="web_upload",
                )
            continue

    logger.info(f"=== UPLOAD REQUEST COMPLETE === Uploaded: {uploaded_count}, Skipped: {skipped_count}, Errors: {len(errors)}")

    if errors:
        return jsonify({"ok": False, "uploaded": uploaded_count, "skipped": skipped_count, "errors": errors}), 500

    return jsonify({"ok": True, "uploaded": uploaded_count, "skipped": skipped_count}), 200
