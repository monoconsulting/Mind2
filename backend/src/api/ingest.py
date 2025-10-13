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
from services.queue_manager import get_celery
from services.storage import FileStorage
from services.file_detection import detect_file
from services.pdf_conversion import pdf_to_png_pages

logger = logging.getLogger(__name__)
try:
    from services.tasks import (  # type: ignore
        process_ocr,
        process_classification,
        process_ai_pipeline,
        process_audio_transcription,
    )
except Exception:  # pragma: no cover - allow running without Celery in tests/dev
    process_ocr = None  # type: ignore
    process_classification = None  # type: ignore
    process_ai_pipeline = None  # type: ignore
    process_audio_transcription = None  # type: ignore
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


class DuplicateFileError(Exception):
    """Raised when attempting to store a duplicate file."""


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


def _cleanup_paths(paths: Iterable[Path]) -> None:
    for p in paths:
        path = Path(p)
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except Exception:
            logger.debug("Failed to remove temporary file %s", path, exc_info=True)


def _insert_unified_file(
    *,
    file_id: str,
    file_type: str,
    content_hash: str,
    submitted_by: str,
    original_filename: str,
    ai_status: str,
    mime_type: str | None = None,
    file_suffix: str | None = None,
    original_file_id: str | None = None,
    original_file_name: str | None = None,
    original_file_size: int | None = None,
    other_data: dict[str, Any] | None = None,
) -> None:
    if db_cursor is None:
        return

    payload = json.dumps(other_data or {})

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO unified_files (
                    id, file_type, ocr_raw, other_data, content_hash,
                    submitted_by, original_filename, ai_status,
                    mime_type, file_suffix, original_file_id,
                    original_file_name, original_file_size
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    file_id,
                    file_type,
                    "",
                    payload,
                    content_hash,
                    submitted_by,
                    original_filename,
                    ai_status,
                    mime_type,
                    file_suffix,
                    original_file_id or file_id,
                    original_file_name or original_filename,
                    original_file_size,
                ),
            )
    except Exception as db_error:
        msg = str(db_error)
        if "Duplicate entry" in msg and "idx_content_hash" in msg:
            raise DuplicateFileError from db_error
        raise


def _update_other_data(file_id: str, other_data: dict[str, Any]) -> None:
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET other_data=%s WHERE id=%s",
                (json.dumps(other_data or {}), file_id),
            )
    except Exception:
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
        logger.info(f"[RESUME] Fetching last processing state for {fid}")

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

        def _reset_workflow_stages(stages_to_pending: list[str]) -> bool:
            """Set ai_status to pending and append history markers for specified stages."""
            if db_cursor is None:
                return False

            try:
                with db_cursor() as cur:
                    cur.execute(
                        "UPDATE unified_files SET ai_status=%s, ai_confidence=NULL, updated_at=NOW() WHERE id=%s",
                        ("pending", fid),
                    )

                if stages_to_pending:
                    with db_cursor() as cur:
                        for stage in stages_to_pending:
                            ai_stage_name = "OCR" if stage == "ocr" else stage.upper()
                            cur.execute(
                                INSERT_HISTORY_SQL,
                                (
                                    fid,
                                    stage,
                                    "pending",
                                    ai_stage_name,
                                    "Reset to pending by resume",
                                    None,
                                    None,
                                    None,
                                    None,
                                    None,
                                ),
                            )
                logger.info(f"[RESUME] Workflow stages reset to pending for {fid} ({', '.join(stages_to_pending)})")
                return True
            except Exception as reset_exc:  # pragma: no cover - defensive logging
                logger.error(f"[RESUME] Failed to reset workflow stages for {fid}: {reset_exc}")
                try:
                    import traceback

                    logger.debug(traceback.format_exc())
                except Exception:
                    pass
                return False

        def _queue_and_respond(task_callable, resumed_from: str, action: str, stages_to_pending: list[str]):
            if task_callable is None:
                raise RuntimeError("tasks_unavailable")
            result = task_callable.delay(fid)  # type: ignore[attr-defined]
            reset_ok = _reset_workflow_stages(stages_to_pending)
            if not reset_ok:
                logger.warning(f"[RESUME] Workflow stages could not be reset for {fid}")
            return jsonify(
                {
                    "queued": True,
                    "task_id": getattr(result, "id", None),
                    "resumed_from": resumed_from,
                    "action": action,
                }
            ), 200

        resumed_from = last_job_type or "unknown"

        # Determine next step based on last job type and status
        if last_status == "error":
            if last_job_type in ("upload", "ocr"):
                return _queue_and_respond(process_ocr, resumed_from, "restart_from_ocr", ["ocr", "ai1", "ai2", "ai3", "ai4"])
            if last_job_type in ("ai1", "ai2", "ai3", "ai4", "ai5", "ai_pipeline"):
                return _queue_and_respond(process_ai_pipeline, resumed_from, "restart_ai_pipeline", ["ai1", "ai2", "ai3", "ai4"])
            return _queue_and_respond(process_ocr, resumed_from, "restart_from_ocr", ["ocr", "ai1", "ai2", "ai3", "ai4"])

        if last_job_type == "ocr" and last_status == "success":
            return _queue_and_respond(process_ai_pipeline, resumed_from, "continue_to_ai_pipeline", ["ai1", "ai2", "ai3", "ai4"])

        if last_job_type == "upload" and last_status == "success":
            return _queue_and_respond(process_ocr, resumed_from, "continue_to_ocr", ["ocr", "ai1", "ai2", "ai3", "ai4"])

        # Default: restart the full pipeline from OCR
        return _queue_and_respond(process_ocr, resumed_from, "restart_pipeline", ["ocr", "ai1", "ai2", "ai3", "ai4"])

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
    submitted_by = request.headers.get('X-User') or 'upload'

    def _queue_ocr_task(target_id: str) -> None:
        try:
            if process_ocr is not None:
                process_ocr.delay(target_id)
                logger.info(f"Queued OCR task for {target_id}")
            else:
                logger.warning(f"OCR task unavailable for {target_id}")
        except Exception as exc:
            logger.warning(f"Failed to enqueue OCR for {target_id}: {exc}")

    def _queue_audio_task(target_id: str) -> None:
        try:
            if process_audio_transcription is not None:
                process_audio_transcription.delay(target_id)
                logger.info(f"Queued transcription task for {target_id}")
            else:
                logger.warning(f"Transcription task unavailable for {target_id}")
        except Exception as exc:
            logger.warning(f"Failed to enqueue transcription for {target_id}: {exc}")

    for idx, file in enumerate(files, 1):
        if not file or not file.filename:
            logger.warning(f"File {idx}: Skipping - no filename")
            continue

        logger.info(f"File {idx}/{len(files)}: Processing '{file.filename}'")

        cleanup_paths: set[Path] = set()
        try:
            # Read file data
            data = file.read()
            logger.info(f"File {idx}: Read {len(data)} bytes")

            # Calculate hash for duplicate detection
            file_hash = hashlib.sha256(data).hexdigest()
            logger.info(f"File {idx}: Hash calculated: {file_hash[:16]}...")

            receipt_id = str(uuid.uuid4())
            safe_filename = secure_filename(file.filename) if file.filename else f"upload_{receipt_id}"
            detection = detect_file(data, safe_filename)
            logger.info(
                f"File {idx}: Detected kind={detection.kind}, mime={detection.mime_type}, ext={detection.extension}"
            )

            if _hash_exists(file_hash):
                logger.warning(f"File {idx}: SKIPPED - Duplicate detected before insert")
                skipped_count += 1
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

            if detection.kind == "pdf":
                logger.info(f"File {idx}: Handling as PDF document")
                pdf_id = receipt_id

                try:
                    pages = pdf_to_png_pages(data, fs.base / "converted", pdf_id, dpi=300)
                except Exception as conv_error:
                    error_msg = f"PDF conversion failed: {conv_error}"
                    logger.error(f"File {idx}: {error_msg}")
                    errors.append(error_msg)
                    _history(
                        file_id=pdf_id,
                        job="upload",
                        status="error",
                        ai_stage_name="Upload-PdfStored",
                        log_text=f"Failed to convert PDF: filename={safe_filename}",
                        error_message=str(conv_error),
                        provider="web_upload",
                    )
                    continue

                cleanup_paths = {page.path for page in pages}

                if not pages:
                    error_msg = f"PDF has no pages: {safe_filename}"
                    logger.error(f"File {idx}: {error_msg}")
                    errors.append(error_msg)
                    _history(
                        file_id=pdf_id,
                        job="upload",
                        status="error",
                        ai_stage_name="Upload-PdfStored",
                        log_text=error_msg,
                        error_message="empty_pdf",
                        provider="web_upload",
                    )
                    _cleanup_paths(cleanup_paths)
                    cleanup_paths.clear()
                    continue

                try:
                    _insert_unified_file(
                        file_id=pdf_id,
                        file_type="pdf",
                        content_hash=file_hash,
                        submitted_by=submitted_by,
                        original_filename=safe_filename,
                        ai_status="uploaded",
                        mime_type="application/pdf",
                        file_suffix=Path(safe_filename).suffix or ".pdf",
                        original_file_id=pdf_id,
                        original_file_name=safe_filename,
                        original_file_size=len(data),
                        other_data={
                            "detected_kind": "pdf",
                            "page_count": len(pages),
                            "source": "web_upload",
                        },
                    )
                    logger.info(f"File {idx}: PDF database record created ({pdf_id})")
                except DuplicateFileError:
                    logger.warning(f"File {idx}: SKIPPED - Duplicate PDF (hash={file_hash[:16]}...)")
                    skipped_count += 1
                    _history(
                        file_id=pdf_id,
                        job="upload",
                        status="error",
                        ai_stage_name="Upload-PdfStored",
                        log_text=f"Skipped duplicate PDF: hash={file_hash[:16]}..., filename={safe_filename}",
                        error_message="Duplicate file detected by content hash",
                        provider="web_upload",
                    )
                    _cleanup_paths(cleanup_paths)
                    cleanup_paths.clear()
                    continue

                fs.save_original(pdf_id, safe_filename, data)

                page_refs = []
                for page in pages:
                    page_number = page.index + 1
                    page_id = str(uuid.uuid4())
                    page_hash = hashlib.sha256(page.bytes).hexdigest()
                    original_path = page.path
                    try:
                        _insert_unified_file(
                            file_id=page_id,
                            file_type="unknown",
                            content_hash=page_hash,
                            submitted_by=submitted_by,
                            original_filename=f"{safe_filename}-page-{page_number:04d}.png",
                            ai_status="uploaded",
                            mime_type="image/png",
                            file_suffix=".png",
                            original_file_id=pdf_id,
                            original_file_name=safe_filename,
                            original_file_size=len(page.bytes),
                            other_data={
                                "detected_kind": "pdf_page",
                                "page_number": page_number,
                                "source_pdf": pdf_id,
                                "source": "web_upload",
                            },
                        )
                    except DuplicateFileError:
                        logger.warning(
                            f"File {idx}: Duplicate PDF page skipped (page={page_number}, hash={page_hash[:16]}...)"
                        )
                        skipped_count += 1
                        _cleanup_paths([original_path])
                        cleanup_paths.discard(original_path)
                        _history(
                            file_id=page_id,
                            job="upload",
                            status="error",
                            ai_stage_name="Upload-PdfPageGenerated",
                            log_text=f"Skipped duplicate PDF page {page_number}",
                            error_message="Duplicate PDF page detected",
                            provider="web_upload",
                        )
                        continue

                    stored_page_name = f"page-{page_number:04d}.png"
                    try:
                        stored_path = fs.adopt(page_id, stored_page_name, original_path)
                    except FileNotFoundError:
                        raise RuntimeError(
                            f"Converted page missing before storage (page={page_number})"
                        )
                    cleanup_paths.discard(original_path)
                    page.path = stored_path
                    logger.info(
                        "File %s: Stored PDF page %s as %s/%s",
                        idx,
                        page_number,
                        page_id,
                        stored_page_name,
                    )
                    page_refs.append({"file_id": page_id, "page_number": page_number})
                    _queue_ocr_task(page_id)
                    uploaded_count += 1
                    _history(
                        file_id=page_id,
                        job="upload",
                        status="success",
                        ai_stage_name="Upload-PdfPageGenerated",
                        log_text=f"Generated PDF page {page_number} for {pdf_id}",
                        provider="web_upload",
                    )

                _update_other_data(
                    pdf_id,
                    {
                        "detected_kind": "pdf",
                        "page_count": len(page_refs),
                        "pages": page_refs,
                        "source": "web_upload",
                    },
                    )
                _history(
                    file_id=pdf_id,
                    job="upload",
                    status="success",
                    ai_stage_name="Upload-PdfStored",
                    log_text=f"PDF stored with {len(page_refs)} page(s)",
                    provider="web_upload",
                )
                cleanup_paths.clear()
                continue

            if detection.kind == "audio":
                logger.info(f"File {idx}: Handling as audio file")
                audio_id = receipt_id
                extension = detection.extension or Path(safe_filename).suffix or ".audio"
                try:
                    _insert_unified_file(
                        file_id=audio_id,
                        file_type="audio",
                        content_hash=file_hash,
                        submitted_by=submitted_by,
                        original_filename=safe_filename,
                        ai_status="awaiting_transcription",
                        mime_type=detection.mime_type or "audio/octet-stream",
                        file_suffix=extension,
                        original_file_id=audio_id,
                        original_file_name=safe_filename,
                        original_file_size=len(data),
                        other_data={
                            "detected_kind": "audio",
                            "source": "web_upload",
                        },
                    )
                except DuplicateFileError:
                    logger.warning(f"File {idx}: SKIPPED - Duplicate audio (hash={file_hash[:16]}...)")
                    skipped_count += 1
                    _history(
                        file_id=audio_id,
                        job="upload",
                        status="error",
                        ai_stage_name="Upload-AudioRouted",
                        log_text=f"Skipped duplicate audio: hash={file_hash[:16]}...",
                        error_message="Duplicate file detected by content hash",
                        provider="web_upload",
                    )
                    continue

                fs.save_original(audio_id, safe_filename, data)
                uploaded_count += 1
                _queue_audio_task(audio_id)
                _history(
                    file_id=audio_id,
                    job="upload",
                    status="success",
                    ai_stage_name="Upload-AudioRouted",
                    log_text=f"Audio routed to transcription: filename={safe_filename}",
                    provider="web_upload",
                )
                continue

            if detection.kind == "image":
                logger.info(f"File {idx}: Handling as image")
                extension = detection.extension or Path(safe_filename).suffix or ".jpg"
                try:
                    _insert_unified_file(
                        file_id=receipt_id,
                        file_type="unknown",
                        content_hash=file_hash,
                        submitted_by=submitted_by,
                        original_filename=safe_filename,
                        ai_status="uploaded",
                        mime_type=detection.mime_type or "image/octet-stream",
                        file_suffix=extension,
                        original_file_id=receipt_id,
                        original_file_name=safe_filename,
                        original_file_size=len(data),
                        other_data={
                            "detected_kind": "image",
                            "source": "web_upload",
                        },
                    )
                except DuplicateFileError:
                    logger.warning(f"File {idx}: SKIPPED - Duplicate image (hash={file_hash[:16]}...)")
                    skipped_count += 1
                    _history(
                        file_id=receipt_id,
                        job="upload",
                        status="error",
                        ai_stage_name="Upload-FileReceived",
                        log_text=f"Skipped duplicate image: hash={file_hash[:16]}...",
                        error_message="Duplicate file detected by content hash",
                        provider="web_upload",
                    )
                    continue

                fs.save_original(receipt_id, safe_filename, data)
                uploaded_count += 1
                _queue_ocr_task(receipt_id)
                _history(
                    file_id=receipt_id,
                    job="upload",
                    status="success",
                    ai_stage_name="Upload-FileReceived",
                    log_text=f"Image uploaded successfully: filename={safe_filename}",
                    provider="web_upload",
                )
                continue

            logger.info(f"File {idx}: Handling as unsupported/other type")
            other_id = receipt_id
            try:
                _insert_unified_file(
                    file_id=other_id,
                    file_type="other",
                    content_hash=file_hash,
                    submitted_by=submitted_by,
                    original_filename=safe_filename,
                    ai_status="manual_review",
                    mime_type=detection.mime_type or "application/octet-stream",
                    file_suffix=Path(safe_filename).suffix,
                    original_file_id=other_id,
                    original_file_name=safe_filename,
                    original_file_size=len(data),
                    other_data={
                        "detected_kind": detection.kind,
                        "source": "web_upload",
                    },
                )
            except DuplicateFileError:
                logger.warning(f"File {idx}: SKIPPED - Duplicate other file (hash={file_hash[:16]}...)")
                skipped_count += 1
                _history(
                    file_id=other_id,
                    job="upload",
                    status="error",
                    ai_stage_name="Upload-OtherRouted",
                    log_text=f"Skipped duplicate file: hash={file_hash[:16]}...",
                    error_message="Duplicate file detected by content hash",
                    provider="web_upload",
                )
                continue

            stored_other_name = secure_filename(safe_filename) or f"file_{other_id}"
            fs.save(other_id, stored_other_name, data)
            fs.save_original(other_id, safe_filename, data)
            _history(
                file_id=other_id,
                job="upload",
                status="success",
                ai_stage_name="Upload-OtherRouted",
                log_text=f"File routed to manual review: filename={safe_filename}",
                provider="web_upload",
            )

        except Exception as e:
            error_msg = f"File processing error for {file.filename}: {str(e)}"
            logger.error(f"File {idx}: ERROR - {error_msg}")
            errors.append(error_msg)
            if cleanup_paths:
                _cleanup_paths(cleanup_paths)
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
