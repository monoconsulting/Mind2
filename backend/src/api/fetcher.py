from __future__ import annotations

import logging
from flask import Blueprint, jsonify

from api.middleware import auth_required
from services.fetch_ftp import fetch_from_ftp

logger = logging.getLogger(__name__)
fetcher_bp = Blueprint("fetcher", __name__)


@fetcher_bp.post("/ingest/fetch-ftp")
@auth_required
def trigger_fetch_ftp():
    logger.info("=== FTP FETCH REQUEST START ===")

    result = fetch_from_ftp()

    logger.info(f"FTP fetch completed: {len(result.downloaded)} downloaded, {len(result.skipped)} skipped, {len(result.errors)} errors")

    # NOTE: fetch_from_ftp() now creates workflow_runs and dispatches WF1/WF2 directly.
    # Do not enqueue legacy process_ocr tasks here to avoid double-processing.
    enqueued: list[str] = []
    logger.info("=== FTP FETCH REQUEST COMPLETE === Enqueued: 0/%s (workflow dispatch handled in fetch_ftp)", len(result.downloaded))

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
