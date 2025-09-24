from __future__ import annotations

from flask import Blueprint, jsonify

from api.middleware import auth_required
from services.fetch_ftp import fetch_from_ftp
try:
    from services.db.files import set_ai_status
except Exception:  # pragma: no cover
    def set_ai_status(file_id: str, status: str) -> bool:  # type: ignore
        _ = (file_id, status)
        return False
try:
    from services.tasks import process_ocr  # type: ignore
except Exception:  # pragma: no cover
    process_ocr = None  # type: ignore


fetcher_bp = Blueprint("fetcher", __name__)


@fetcher_bp.post("/ingest/fetch-ftp")
@auth_required
def trigger_fetch_ftp():
    result = fetch_from_ftp()
    # Auto-enqueue OCR for newly downloaded files and set status
    enqueued = []
    for file_id, _name in result.downloaded:
        try:
            set_ai_status(file_id, "queued")
            if process_ocr is not None:
                process_ocr.delay(file_id)  # type: ignore[attr-defined]
                enqueued.append(file_id)
        except Exception:
            pass
    return (
        jsonify(
            {
                "downloaded": result.downloaded,
                "skipped": result.skipped,
                "errors": result.errors,
                "enqueued": enqueued,
            }
        ),
        200,
    )
