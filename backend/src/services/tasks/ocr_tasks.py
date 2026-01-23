from __future__ import annotations

import logging
import os
import time
import uuid
import hashlib
from pathlib import Path
from typing import Any

from .common import (
    FileStorage,
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    AiStatus,
    celery_app,
    db_cursor,
    create_unified_file,
    get_unified_file_by_hash,
    log_event,
    pdf_to_png_pages,
    run_ocr,
    update_other_data,
    DuplicateFileError,
    group,
    chord,
    parse_credit_card_statement,
)
from .creditcard_tasks import _ensure_creditcard_pages_and_ocr
from .file_management_tasks import (
    _enforce_file_metadata,
    _maybe_advance_invoice_from_file,
    _update_file_fields,
    _update_file_status,
)
from .history import _history
from .invoice_tasks import _persist_invoice_lines
from .utils.invoice_utils import _collect_invoice_ocr_text, _load_unified_file_info
from .workflow_base import (
    begin_import_stage,
    complete_import_stage,
    ensure_workflow,
    get_workflow_stage,
    mark_stage,
    log_import_event,
)
from services.ocr import OCR_MIN_NONWHITESPACE_CHARS, count_non_whitespace_chars
logger = logging.getLogger(__name__)


def _merge_ocr_page_results(
    results: list[tuple[int, str, str]],
) -> dict[str, Any]:
    all_text: list[str] = []
    failed_pages: list[str] = []
    missing_results = 0
    total_pages = len(results or [])
    pages_with_text = 0
    total_chars_merged = 0

    for result in results or []:
        if not result or len(result) != 3:
            missing_results += 1
            continue
        _, page_id, text = result
        text = text or ""
        char_count = count_non_whitespace_chars(text)
        if char_count >= OCR_MIN_NONWHITESPACE_CHARS:
            all_text.append(text)
            pages_with_text += 1
            total_chars_merged += char_count
        else:
            failed_pages.append(str(page_id))

    combined_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
    return {
        "combined_text": combined_text,
        "failed_pages": failed_pages,
        "missing_results": missing_results,
        "total_pages": total_pages,
        "pages_with_text": pages_with_text,
        "total_chars_merged": total_chars_merged,
    }

# TASK_INVENTORY: ACTIVE (2025-11-28). WF1 OCR stage for receipt workflow.
@celery_app.task(name="wf1_run_ocr")
def wf1_run_ocr(workflow_run_id: int) -> int:
    """
    Workflow 1: OCR Task.

    - Ensures the task is part of a WF1 workflow.
    - Marks the 'ocr' stage as running.
    - Executes OCR on the file associated with the workflow.
    - Marks the 'ocr' stage as 'succeeded' or 'failed'.
    - Returns the workflow_run_id for the next task in the chain.
    """
    import time
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF1_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "ocr", "failed", message="File ID missing in workflow run.")
        raise ValueError("File ID is missing.")

    begin_import_stage(workflow_run_id, "r_ocr", message=f"OCR startar för fil {file_id}")
    mark_stage(workflow_run_id, "ocr", "running", start=True)
    start_time = time.time()
    log_event(
        logger,
        "wf1.ocr.start",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
    )

    result: dict[str, Any] | None = None
    error_msg: str | None = None

    try:
        result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        log_event(
            logger,
            "wf1.ocr.error",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=error_msg,
        )

    elapsed = int((time.time() - start_time) * 1000)

    text = (result or {}).get("text") or ""
    char_count = (result or {}).get("char_count")
    if char_count is None:
        char_count = count_non_whitespace_chars(text)
    if result and char_count >= OCR_MIN_NONWHITESPACE_CHARS:
        _update_file_fields(file_id, ocr_raw=text)
        message = f"OCR succeeded, extracted {char_count} chars in {elapsed}ms."
        mark_stage(workflow_run_id, "ocr", "succeeded", message=message, end=True)
        complete_import_stage(workflow_run_id, "r_ocr", success=True, message=message)
        _update_file_status(file_id, AiStatus.OCR_DONE.value)
        log_event(
            logger,
            "wf1.ocr.succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            duration_ms=elapsed,
            characters=char_count,
            lang_used=(result or {}).get("lang_used"),
            fallback_triggered=(result or {}).get("fallback_triggered"),
        )
    else:
        message = (
            f"OCR failed: {error_msg or 'OCR returned too-short text'} "
            f"(chars={char_count}, min={OCR_MIN_NONWHITESPACE_CHARS})."
        )
        mark_stage(workflow_run_id, "ocr", "failed", message=message, end=True)
        complete_import_stage(workflow_run_id, "r_ocr", success=False, message=message)
        # Do not raise an exception, allow the workflow to be inspected.
        # A failed stage will already halt the workflow chain by default.
        log_event(
            logger,
            "wf1.ocr.failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=error_msg or "no_text",
            duration_ms=elapsed,
            characters=char_count,
            lang_used=(result or {}).get("lang_used"),
            fallback_triggered=(result or {}).get("fallback_triggered"),
        )
        _update_file_status(file_id, AiStatus.OCR_FAILED.value)

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 PDF splitter that schedules per-page OCR.
@celery_app.task(name="wf2_prepare_pdf_pages", queue="wf2")
def wf2_prepare_pdf_pages(workflow_run_id: int) -> int:
    """
    Workflow 2: Prepare PDF Pages Task.
    - Splits the source PDF into individual PNG pages.
    - Creates a unified_file record for each page.
    - Triggers the parallel OCR tasks for each page.
    """
    import time

    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "prepare_pages", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "prepare_pages", "running", start=True)

    parent_info = _load_unified_file_info(file_id) or {}
    mime_type = str(parent_info.get("mime_type") or "").lower()
    file_type = str(parent_info.get("file_type") or "").lower()
    log_event(
        logger,
        "convert.wf2.prepare_start",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
        mime_type=mime_type,
        file_type=file_type,
    )
    if mime_type and mime_type != "application/pdf":
        message = f"Unsupported mime_type for WF2: {mime_type}"
        log_event(
            logger,
            "convert.wf2.prepare_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            reason="unsupported_mime",
            mime_type=mime_type,
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=message, end=True)
        raise ValueError(message)
    if not mime_type and file_type not in {"pdf", "invoice"}:
        message = f"Unsupported file_type for WF2: {file_type or 'unknown'}"
        log_event(
            logger,
            "convert.wf2.prepare_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            reason="unsupported_file_type",
            file_type=file_type or "unknown",
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=message, end=True)
        raise ValueError(message)

    storage_dir = os.getenv("STORAGE_DIR", "/data/storage")
    fs = FileStorage(storage_dir)

    conversion_started: float | None = None
    try:
        originals_root = (fs.base / "originals").resolve()
        original_filename = str(
            parent_info.get("original_file_name")
            or parent_info.get("original_filename")
            or ""
        )
        suffix = Path(original_filename).suffix or ".pdf"
        stored_original_name = f"{file_id}{suffix if suffix.startswith('.') else f'.{suffix}'}"
        original_path = (originals_root / stored_original_name).resolve()

        if not str(original_path).startswith(str(originals_root)):
            raise ValueError("Original file path resolved outside storage root.")
        if not original_path.exists():
            raise FileNotFoundError(f"Original file not found in storage for {file_id}")

        log_event(
            logger,
            "convert.wf2.read_original",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            original_filename=original_filename or original_path.name,
            storage_path=str(original_path),
        )

        data = original_path.read_bytes()
        safe_filename = original_filename or original_path.name

        converted_root = (fs.base / "converted" / file_id).resolve()
        converted_root.mkdir(parents=True, exist_ok=True)

        # Convert PDF to PNG pages (configurable DPI + deterministic fallback ladder).
        conversion_started = time.perf_counter()
        try:
            pdf_dpi = int(os.getenv("OCR_PDF_DPI", "300") or "300")
        except Exception:
            pdf_dpi = 300

        dpi_candidates = [pdf_dpi, 300, 250, 200, 150]
        seen: set[int] = set()
        pages = []
        last_exc: Exception | None = None
        for dpi_candidate in dpi_candidates:
            if dpi_candidate in seen or dpi_candidate <= 0:
                continue
            seen.add(dpi_candidate)
            try:
                pages = pdf_to_png_pages(data, converted_root, file_id, dpi=dpi_candidate)
                if pages:
                    pdf_dpi = dpi_candidate
                    break
            except Exception as exc:
                last_exc = exc

        if not pages:
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("PDF conversion resulted in no pages.")

        page_refs: list[dict[str, Any]] = []
        duplicate_page_ids: list[str] = []
        for page in pages:
            page_number = page.index + 1
            page_id = str(uuid.uuid4())
            page_hash = hashlib.sha256(page.bytes).hexdigest()

            target_file_id = page_id
            duplicate = False

            try:
                create_unified_file(
                    file_id=page_id,
                    file_type="pdf_page",
                    workflow_type="receipt",
                    content_hash=page_hash,
                    submitted_by="workflow",
                    source="wf2_split",
                    original_filename=f"{safe_filename}-page-{page_number:04d}.png",
                    initial_ai_status=AiStatus.UPLOADED.value,
                    mime_type="image/png",
                    file_suffix=".png",
                    original_file_id=file_id,
                    original_file_name=safe_filename,
                    original_file_size=len(page.bytes),
                    extra_metadata={
                        "detected_kind": "pdf_page",
                        "page_number": page_number,
                        "source_pdf": file_id,
                    },
                    create_workflow=False,
                )
            except DuplicateFileError:
                existing = get_unified_file_by_hash(page_hash)
                if not existing:
                    raise
                target_file_id = existing.id
                duplicate = True
                duplicate_page_ids.append(target_file_id)
                log_event(
                    logger,
                    "convert.wf2.duplicate_page_reused",
                    workflow_run_id=workflow_run_id,
                    file_id=file_id,
                    page_number=page_number,
                    reused_file_id=target_file_id,
                )

            stored_page_name = f"page-{page_number:04d}.png"
            stored_page_path = fs.adopt(target_file_id, stored_page_name, page.path)
            if page_number == 1:
                try:
                    existing_parent_images = [
                        name
                        for name in fs.list(file_id)
                        if name.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff"))
                    ]
                    if not existing_parent_images:
                        fs.save(file_id, "page-0001.png", stored_page_path.read_bytes())
                        log_event(
                            logger,
                            "wf2.parent_preview_written",
                            workflow_run_id=workflow_run_id,
                            file_id=file_id,
                            source_page_file_id=target_file_id,
                        )
                except Exception as exc:
                    log_event(
                        logger,
                        "wf2.parent_preview_write_failed",
                        workflow_run_id=workflow_run_id,
                        file_id=file_id,
                        error=str(exc),
                    )
            page_refs.append(
                {
                    "file_id": target_file_id,
                    "page_number": page_number,
                    "duplicate": duplicate,
                    "workflow_type": "receipt",
                }
            )

        duration_ms = int((time.perf_counter() - conversion_started) * 1000) if conversion_started else None
        converted_page_ids = [page["file_id"] for page in page_refs]
        log_event(
            logger,
            "convert.wf2.conversion_succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            page_count=len(page_refs),
            duplicate_reused=len(duplicate_page_ids),
            duration_ms=duration_ms,
            page_ids=converted_page_ids,
        )
        _history(
            file_id,
            "pdf_convert",
            "success",
            ai_stage_name="PDF-Conversion",
            log_text=(
                f"WF2 converted PDF into {len(page_refs)} page(s): page_ids={converted_page_ids}; "
                f"workflow_run_id={workflow_run_id}; duplicate_pages_reused={len(duplicate_page_ids)}"
            ),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name=f"fitz-dpi-{pdf_dpi}",
        )

        # Update the parent PDF unified_file with page info
        other_data = dict(parent_info.get("other_data", {}) or {})
        other_data.update({"page_count": len(page_refs), "pages": page_refs})
        if duplicate_page_ids:
            other_data["duplicate_page_ids"] = duplicate_page_ids
        update_other_data(file_id, other_data)

        mark_stage(
            workflow_run_id,
            "prepare_pages",
            "succeeded",
            message=(
                f"Split PDF into {len(page_refs)} pages."
                + (f" Reused {len(duplicate_page_ids)} duplicate page(s)." if duplicate_page_ids else "")
            ),
            end=True,
        )
        log_event(
            logger,
            "convert.wf2.prepare_succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            page_count=len(page_refs),
            duplicate_reused=len(duplicate_page_ids),
        )

        # Now, trigger the parallel OCR
        if page_refs:
            ocr_tasks = group(
                wf2_run_page_ocr.s(workflow_run_id, page["file_id"], page["page_number"]).set(queue="wf2")
                for page in page_refs
            )
            callback = wf2_merge_ocr_results.s(workflow_run_id).set(queue="wf2")
            chord(ocr_tasks)(callback)
            log_event(
                logger,
                "convert.wf2.ocr_dispatched",
                workflow_run_id=workflow_run_id,
                file_id=file_id,
                page_count=len(page_refs),
            )
    except Exception as e:
        duration_ms = int((time.perf_counter() - conversion_started) * 1000) if conversion_started else None
        log_event(
            logger,
            "convert.wf2.conversion_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=str(e),
            duration_ms=duration_ms,
        )
        _history(
            file_id,
            "pdf_convert",
            "error",
            ai_stage_name="PDF-Conversion",
            log_text="WF2 PDF conversion failed.",
            error_message=str(e),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name=f"fitz-dpi-{pdf_dpi if 'pdf_dpi' in locals() else 300}",
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=str(e), end=True)
        raise

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 per-page OCR execution.
@celery_app.task(name="wf2_run_page_ocr", queue="wf2")
def wf2_run_page_ocr(
    workflow_run_id: int, page_file_id: str, page_number: int | str | None = None
) -> tuple[int, str, str]:
    """
    Workflow 2: OCR Task for a single page.
    - Runs OCR and returns the text.
    """
    import time
    ensure_workflow(workflow_run_id, expected_prefix="WF2_")

    page_info = _load_unified_file_info(page_file_id)
    effective_page_number = (
        page_number
        if page_number is not None
        else (page_info.get("other_data", {}).get("page_number", "unknown") if page_info else "unknown")
    )
    stage_key = f"ocr_page_{effective_page_number}"

    mark_stage(workflow_run_id, stage_key, "running", start=True, update_workflow_status=False)
    start_time = time.time()
    storage_dir = os.getenv("STORAGE_DIR", "/data/storage")
    fs = FileStorage(storage_dir)
    image_names = [
        name
        for name in fs.list(page_file_id)
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))
    ]
    image_count = len(image_names)
    log_event(
        logger,
        "wf2.page_ocr.start",
        workflow_run_id=workflow_run_id,
        page_file_id=page_file_id,
        page_number=effective_page_number,
        storage_dir=storage_dir,
        image_count=image_count,
    )

    if image_count == 0:
        message = f"No images found for page_file_id {page_file_id} in {storage_dir}."
        mark_stage(
            workflow_run_id,
            stage_key,
            "failed",
            message=message,
            end=True,
            update_workflow_status=False,
        )
        log_event(
            logger,
            "wf2.page_ocr.failed",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            error="no_images",
            duration_ms=0,
            image_count=image_count,
        )
        _update_file_status(page_file_id, AiStatus.OCR_FAILED.value)
        return (workflow_run_id, page_file_id, "")

    result: dict[str, Any] | None = None
    error_msg: str | None = None
    text = ""

    try:
        result = run_ocr(page_file_id, storage_dir)
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        log_event(
            logger,
            "wf2.page_ocr.error",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            error=error_msg,
        )

    elapsed = int((time.time() - start_time) * 1000)

    lang_used = (result or {}).get("lang_used")
    fallback_triggered = (result or {}).get("fallback_triggered")
    text = (result or {}).get("text") or ""
    char_count = count_non_whitespace_chars(text)

    page_other = dict(page_info.get("other_data", {}) or {}) if page_info else {}
    page_other.update(
        {
            "ocr_lang_used": lang_used,
            "ocr_char_count": char_count,
            "ocr_fallback_triggered": bool(fallback_triggered),
            "ocr_image_count": image_count,
        }
    )
    update_other_data(page_file_id, page_other)

    if result and char_count >= OCR_MIN_NONWHITESPACE_CHARS:
        _update_file_fields(page_file_id, ocr_raw=text)
        message = (
            f"OCR succeeded for page {effective_page_number}, extracted {char_count} chars "
            f"in {elapsed}ms (lang={lang_used})."
        )
        mark_stage(
            workflow_run_id,
            stage_key,
            "succeeded",
            message=message,
            end=True,
            update_workflow_status=False,
        )
        _update_file_status(page_file_id, AiStatus.OCR_DONE.value)
        log_event(
            logger,
            "wf2.page_ocr.succeeded",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            duration_ms=elapsed,
            characters=char_count,
            lang_used=lang_used,
            fallback_triggered=fallback_triggered,
            image_count=image_count,
        )
    else:
        lang_summary = f"lang_used={lang_used}, fallback_triggered={fallback_triggered}"
        message = (
            f"OCR failed for page {effective_page_number}: "
            f"{error_msg or 'OCR returned too-short text'} "
            f"(chars={char_count}, min={OCR_MIN_NONWHITESPACE_CHARS}, images={image_count}, {lang_summary})."
        )
        mark_stage(
            workflow_run_id,
            stage_key,
            "failed",
            message=message,
            end=True,
            update_workflow_status=False,
        )
        log_event(
            logger,
            "wf2.page_ocr.failed",
            workflow_run_id=workflow_run_id,
            page_file_id=page_file_id,
            page_number=effective_page_number,
            error=error_msg or 'no_text',
            duration_ms=elapsed,
            characters=char_count,
            lang_used=lang_used,
            fallback_triggered=fallback_triggered,
            image_count=image_count,
        )
        _update_file_status(page_file_id, AiStatus.OCR_FAILED.value)
        text = ""

    return (workflow_run_id, page_file_id, text)

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 fan-in to merge OCR results and continue workflow.
@celery_app.task(name="wf2_merge_ocr_results", queue="wf2")
def wf2_merge_ocr_results(results: list[tuple[int, str, str]], workflow_run_id: int):
    """
    Workflow 2: Merge OCR Results Task.
    - Collects OCR text from all page tasks.
    - Saves the combined text.
    - Triggers the next step in the workflow.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id") # This is the parent PDF file_id
    if not file_id:
        mark_stage(workflow_run_id, "merge_ocr", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "merge_ocr", "running", start=True)

    merge_stats = _merge_ocr_page_results(results)
    combined_text = merge_stats["combined_text"]
    failed_pages = merge_stats["failed_pages"]
    missing_results = merge_stats["missing_results"]
    total_pages = merge_stats["total_pages"]
    pages_with_text = merge_stats["pages_with_text"]
    total_chars_merged = merge_stats["total_chars_merged"]
    
    # Save the combined text to the parent PDF's other_data
    parent_file_info = _load_unified_file_info(file_id) or {}
    other_data = dict(parent_file_info.get("other_data", {}) or {})
    other_data["combined_ocr_text"] = combined_text
    if failed_pages:
        other_data["failed_ocr_pages"] = failed_pages
    if missing_results:
        other_data["ocr_missing_results"] = missing_results
    other_data["ocr_pages_total"] = total_pages
    other_data["ocr_pages_with_text"] = pages_with_text
    other_data["ocr_total_chars"] = total_chars_merged
    update_other_data(file_id, other_data)

    # Mark pages as completed to avoid orphan queue noise
    for result in results:
        if result and len(result) == 3:
            _, page_id, _ = result
            _update_file_status(page_id, AiStatus.COMPLETED.value)

    message = (
        f"Merged OCR text from {pages_with_text}/{total_pages} pages "
        f"({total_chars_merged} chars)."
    )
    status = "succeeded" if pages_with_text > 0 else "failed"
    if failed_pages:
        message += f" Failed pages: {', '.join(failed_pages)}"
    if status == "failed":
        message = "OCR merge produced no usable text."

    mark_stage(workflow_run_id, "merge_ocr", status, message=message, end=True)
    log_event(
        logger,
        "wf2.merge_ocr.completed",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
        total_pages=total_pages,
        pages_with_text=pages_with_text,
        failed_pages=failed_pages,
        total_chars_merged=total_chars_merged,
        status=status,
    )

    if status == "succeeded":
        # Update parent ocr_raw to enable downstream AI
        _update_file_fields(file_id, ocr_raw=combined_text)
        _update_file_status(file_id, AiStatus.OCR_DONE.value)
    else:
        _update_file_status(file_id, AiStatus.OCR_FAILED.value)

    if status != "succeeded":
        return workflow_run_id

    # Decide next step based on intended workflow type
    parent_workflow_type = str(parent_file_info.get("workflow_type") or "").lower()

    if parent_workflow_type in ("receipt", ""):
        # Create and dispatch a WF1 workflow_run for the parent PDF (single log entry expected)
        try:
            from services.workflow_runs import create_workflow_run
            from services.tasks.workflow_tasks import dispatch_workflow, mark_stage as wt_mark_stage
        except Exception:
            dispatch_workflow = None
            create_workflow_run = None
            wt_mark_stage = None

        if create_workflow_run and dispatch_workflow and wt_mark_stage:
            # Ensure invoice_analysis is marked so wf2_finalize can succeed
            wt_mark_stage(workflow_run_id, "invoice_analysis", "succeeded", message="Skipped: forwarded to WF1")

            new_wr_id = create_workflow_run(
                workflow_key="WF1_RECEIPT",
                source_channel="wf2_split",
                file_id=file_id,
                content_hash=parent_file_info.get("content_hash") or "",
            )
            dispatch_workflow(new_wr_id)
            log_event(
                logger,
                "wf2.dispatch_wf1_after_split",
                workflow_run_id=workflow_run_id,
                new_workflow_run_id=new_wr_id,
                file_id=file_id,
            )
        else:
            log_event(
                logger,
                "wf2.dispatch_wf1_after_split_failed",
                workflow_run_id=workflow_run_id,
                file_id=file_id,
                reason="dispatch helpers unavailable",
            )

        # Finalize WF2 to succeeded to keep SoT invariant
        mark_stage(
            workflow_run_id,
            "finalize",
            "succeeded",
            message="WF2 slutförd, dispatchad till WF1 for receipt processing",
            end=True,
            workflow_status_override="succeeded",
        )
        begin_import_stage(
            workflow_run_id,
            "finalize_ok",
            message="WF2 slutförd",
        )
        complete_import_stage(
            workflow_run_id,
            "finalize_ok",
            success=True,
            message="PDF-split avslutad och skickad vidare till WF1",
        )
        log_import_event(
            workflow_run_id,
            "KLAR",
            message="WF2 slutförd",
        )
    else:
        # Non-receipt path: continue existing WF2 invoice analysis chain
        wf2_run_invoice_analysis.s(workflow_run_id).set(queue="wf2").apply_async()

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 invoice analysis stage (parses merged OCR).
@celery_app.task(name="wf2_run_invoice_analysis", queue="wf2")
def wf2_run_invoice_analysis(workflow_run_id: int) -> int:
    """
    Workflow 2: Invoice Analysis Task.
    - Parses the combined OCR text.
    - Creates invoice line items.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "invoice_analysis", "failed", message="File ID missing.")
        raise ValueError("File ID is missing.")

    mark_stage(workflow_run_id, "invoice_analysis", "running", start=True)
    log_event(
        logger,
        "wf2.invoice_analysis.start",
        workflow_run_id=workflow_run_id,
        file_id=file_id,
    )

    parent_info = _load_unified_file_info(file_id) or {}

    try:
        other_data = dict(parent_info.get("other_data", {}) or {})
        combined_text = other_data.get("combined_ocr_text", "")

        if not combined_text:
            raise ValueError("Combined OCR text is missing.")

        # This logic is from the old `process_invoice_document`
        parsed = parse_credit_card_statement(combined_text)
        lines = parsed.get("lines") or []
        inserted = _persist_invoice_lines(file_id, lines)

        other_data["invoice_line_count"] = inserted
        update_other_data(file_id, other_data)

        message = f"Invoice analysis complete. Inserted {inserted} lines."
        mark_stage(workflow_run_id, "invoice_analysis", "succeeded", message=message, end=True)
        log_event(
            logger,
            "wf2.invoice_analysis.succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            inserted=inserted,
        )

        # Trigger finalization (lazy import to avoid circular import at module load)
        import importlib

        wf_tasks = importlib.import_module("services.tasks.workflow_tasks")
        finalize_task = getattr(wf_tasks, "wf2_finalize", None)
        if not finalize_task:
            raise NameError("wf2_finalize task not found in workflow_tasks module")

        finalize_task.s(workflow_run_id).set(queue="wf2").apply_async()

    except Exception as e:
        mark_stage(workflow_run_id, "invoice_analysis", "failed", message=str(e), end=True)
        log_event(
            logger,
            "wf2.invoice_analysis.failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=str(e),
        )
        raise

    return workflow_run_id

__all__ = [
    "wf1_run_ocr",
    "wf2_prepare_pdf_pages",
    "wf2_run_page_ocr",
    "wf2_merge_ocr_results",
    "wf2_run_invoice_analysis",
]
