from __future__ import annotations

import os
import uuid
from typing import Any
from flask import Blueprint, jsonify, request

from api.middleware import auth_required
from services.queue_manager import get_celery
from services.storage import FileStorage
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


@ingest_bp.post("/capture/upload")
def capture_upload() -> Any:
    """Public capture endpoint: accepts multi-page images, optional tags and location.
    Behavior:
      - For each uploaded image, ensure a unified_files record exists (id = shared receipt_id)
      - Save files under STORAGE_DIR/<receipt_id>/page-*.ext via FileStorage
      - Store optional tags into file_tags (best-effort) and enqueue OCR for the first page
    """
    files = request.files.getlist('images')
    if not files:
        return jsonify({"ok": False, "error": "no_images"}), 400
    tags_raw = request.form.get('tags')
    location_raw = request.form.get('location')
    try:
        import json
        tags = json.loads(tags_raw) if tags_raw else []
        if not isinstance(tags, list):
            tags = []
    except Exception:
        tags = []
    # Parse optional location JSON
    location = None
    if location_raw:
        try:
            location = json.loads(location_raw)
        except Exception:
            location = None
    receipt_id = str(uuid.uuid4())
    storage_dir = os.getenv('STORAGE_DIR', '/data/storage')
    fs = FileStorage(storage_dir)
    saved: list[str] = []
    # Get original filename from first file
    original_filename = files[0].filename if files[0] and files[0].filename else None

    # Insert unified_files row
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "INSERT INTO unified_files (id, file_type, created_at, submitted_by, original_filename) "
                        "VALUES (%s, %s, NOW(), %s, %s)"
                    ),
                    (receipt_id, 'receipt', (request.headers.get('X-User') or 'anonymous'), original_filename),
                )
        except Exception:
            # best-effort
            pass
    # Save files
    for idx, f in enumerate(files, start=1):
        # derive extension
        fname = f.filename or f"page-{idx}.jpg"
        ext = os.path.splitext(fname)[1] or '.jpg'
        safe_name = f"page-{idx}{ext}"
        try:
            data = f.read()
            fs.save(receipt_id, safe_name, data)
            saved.append(safe_name)
        except Exception:
            continue
    # Save tags best-effort
    if tags and db_cursor is not None:
        try:
            with db_cursor() as cur:
                for t in tags:
                    if not t or not isinstance(t, str):
                        continue
                    cur.execute(
                        (
                            "INSERT INTO file_tags (file_id, tag, created_at) VALUES (%s, %s, NOW())"
                        ),
                        (receipt_id, t.strip()),
                    )
        except Exception:
            pass
    # Save location best-effort
    if location and isinstance(location, dict) and db_cursor is not None:
        try:
            lat = location.get('lat')
            lon = location.get('lon')
            acc = location.get('acc')
            with db_cursor() as cur:
                cur.execute(
                    (
                        "INSERT INTO file_locations (file_id, lat, lon, acc) VALUES (%s, %s, %s, %s)"
                    ),
                    (receipt_id, lat, lon, acc),
                )
        except Exception:
            pass
    # Enqueue OCR for this receipt (first page id == receipt_id in this schema)
    try:
        if process_ocr is None:
            raise RuntimeError("tasks_unavailable")
        process_ocr.delay(receipt_id)  # type: ignore[attr-defined]
    except Exception:
        pass
    return jsonify({"ok": True, "receipt_id": receipt_id, "saved": saved}), 200
