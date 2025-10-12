from __future__ import annotations

import logging
from flask import Blueprint, jsonify

from api.middleware import auth_required
from services.fetch_ftp import fetch_from_ftp

logger = logging.getLogger(__name__)
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
    logger.info("=== FTP FETCH REQUEST START ===")

    result = fetch_from_ftp()

    logger.info(f"FTP fetch completed: {len(result.downloaded)} downloaded, {len(result.skipped)} skipped, {len(result.errors)} errors")

    # Auto-enqueue OCR for newly downloaded files and set status
    enqueued = []
    for file_id, name in result.downloaded:
        try:
            logger.info(f"FTP: Setting status to 'queued' for {file_id} ({name})")
            set_ai_status(file_id, "queued")

            if process_ocr is not None:
                process_ocr.delay(file_id)  # type: ignore[attr-defined]
                enqueued.append(file_id)
                logger.info(f"FTP: OCR task queued for {file_id} ({name})")
            else:
                logger.warning(f"FTP: OCR not available for {file_id} ({name})")
        except Exception as e:
            logger.error(f"FTP: Failed to queue OCR for {file_id} ({name}): {e}")

    logger.info(f"=== FTP FETCH REQUEST COMPLETE === Enqueued: {len(enqueued)}/{len(result.downloaded)}")

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
