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
    from services.tasks import process_ocr, process_classification  # type: ignore
except Exception:  # pragma: no cover - allow running without Celery in tests/dev
    process_ocr = None  # type: ignore
    process_classification = None  # type: ignore
try:
    from services.db.files import list_unprocessed
except Exception:  # pragma: no cover
    list_unprocessed = lambda limit=50: []  # type: ignore
try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


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
                except Exception as db_error:
                    # Check for duplicate hash
                    if 'Duplicate entry' in str(db_error) and 'idx_content_hash' in str(db_error):
                        logger.warning(f"File {idx}: SKIPPED - Duplicate file (hash={file_hash[:16]}...)")
                        skipped_count += 1
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
            continue

    logger.info(f"=== UPLOAD REQUEST COMPLETE === Uploaded: {uploaded_count}, Skipped: {skipped_count}, Errors: {len(errors)}")

    if errors:
        return jsonify({"ok": False, "uploaded": uploaded_count, "skipped": skipped_count, "errors": errors}), 500

    return jsonify({"ok": True, "uploaded": uploaded_count, "skipped": skipped_count}), 200
