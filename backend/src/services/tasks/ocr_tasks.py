from __future__ import annotations

import logging
import os
import time
from typing import Any

from .common import (
    FileStorage,
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    celery_app,
    db_cursor,
    insert_unified_file,
    log_event,
    pdf_to_png_pages,
    run_ocr,
    update_other_data,
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
logger = logging.getLogger(__name__)

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

    begin_import_stage(workflow_run_id, "r_ocr", message=f"OCR startar f├╢r fil {file_id}")
    mark_stage(workflow_run_id, "ocr", "running", start=True)
    start_time = time.time()

    result: dict[str, Any] | None = None
    error_msg: str | None = None

    try:
        result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"

    elapsed = int((time.time() - start_time) * 1000)

    if result:
        _update_file_fields(file_id, ocr_raw=result.get("text"))
        text_len = len(result.get("text", ""))
        message = f"OCR succeeded, extracted {text_len} chars in {elapsed}ms."
        mark_stage(workflow_run_id, "ocr", "succeeded", message=message, end=True)
        complete_import_stage(workflow_run_id, "r_ocr", success=True, message=message)
    else:
        message = f"OCR failed: {error_msg or 'OCR returned no results'}"
        mark_stage(workflow_run_id, "ocr", "failed", message=message, end=True)
        complete_import_stage(workflow_run_id, "r_ocr", success=False, message=message)
        # Do not raise an exception, allow the workflow to be inspected.
        # A failed stage will already halt the workflow chain by default.

    return workflow_run_id

@celery_app.task(name="wf2_prepare_pdf_pages")
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

        # Convert PDF to PNG pages
        conversion_started = time.perf_counter()
        pages = pdf_to_png_pages(data, converted_root, file_id, dpi=300)
        if not pages:
            raise RuntimeError("PDF conversion resulted in no pages.")

        page_refs = []
        for page in pages:
            page_number = page.index + 1
            page_id = str(uuid.uuid4())
            page_hash = hashlib.sha256(page.bytes).hexdigest()

            insert_unified_file(
                file_id=page_id,
                file_type="pdf_page",
                content_hash=page_hash,
                submitted_by="workflow",
                original_filename=f"{safe_filename}-page-{page_number:04d}.png",
                ai_status="uploaded",
                mime_type="image/png",
                file_suffix=".png",
                original_file_id=file_id,
                original_file_name=safe_filename,
                original_file_size=len(page.bytes),
                other_data={
                    "detected_kind": "pdf_page",
                    "page_number": page_number,
                    "source_pdf": file_id,
                },
            )

            stored_page_name = f"page-{page_number:04d}.png"
            fs.adopt(page_id, stored_page_name, page.path)
            page_refs.append({"file_id": page_id, "page_number": page_number})

        duration_ms = int((time.perf_counter() - conversion_started) * 1000) if conversion_started else None
        converted_page_ids = [page["file_id"] for page in page_refs]
        log_event(
            logger,
            "convert.wf2.conversion_succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            page_count=len(page_refs),
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
                f"workflow_run_id={workflow_run_id}"
            ),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name="fitz-dpi-300",
        )

        # Update the parent PDF unified_file with page info
        other_data = dict(parent_info.get("other_data", {}) or {})
        other_data.update({"page_count": len(page_refs), "pages": page_refs})
        update_other_data(file_id, other_data)

        mark_stage(
            workflow_run_id,
            "prepare_pages",
            "succeeded",
            message=f"Split PDF into {len(page_refs)} pages.",
            end=True,
        )
        log_event(
            logger,
            "convert.wf2.prepare_succeeded",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            page_count=len(page_refs),
        )

        # Now, trigger the parallel OCR
        if page_refs:
            ocr_tasks = group(
                wf2_run_page_ocr.s(workflow_run_id, page["file_id"]) for page in page_refs
            )
            callback = wf2_merge_ocr_results.s(workflow_run_id)
            chord(ocr_tasks)(callback)
            log_event(
                logger,
                "convert.wf2.ocr_dispatched",
                workflow_run_id=workflow_run_id,
                file_id=file_id,
                page_count=len(page_refs),
            )

    except DuplicateFileError as dup_exc:
        duration_ms = int((time.perf_counter() - conversion_started) * 1000) if conversion_started else None
        log_event(
            logger,
            "convert.wf2.conversion_failed",
            workflow_run_id=workflow_run_id,
            file_id=file_id,
            error=f"Duplicate page detected: {dup_exc}",
            duration_ms=duration_ms,
        )
        _history(
            file_id,
            "pdf_convert",
            "error",
            ai_stage_name="PDF-Conversion",
            log_text="Duplicate page detected during WF2 PDF conversion.",
            error_message=str(dup_exc),
            processing_time_ms=duration_ms,
            provider="pymupdf",
            model_name="fitz-dpi-300",
        )
        mark_stage(
            workflow_run_id,
            "prepare_pages",
            "failed",
            message=f"Duplicate page detected: {dup_exc}",
            end=True,
        )
        raise
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
            model_name="fitz-dpi-300",
        )
        mark_stage(workflow_run_id, "prepare_pages", "failed", message=str(e), end=True)
        raise

    return workflow_run_id

@celery_app.task(name="wf2_run_page_ocr")
def wf2_run_page_ocr(workflow_run_id: int, page_file_id: str) -> tuple[int, str, str]:
    """
    Workflow 2: OCR Task for a single page.
    - Runs OCR and returns the text.
    """
    import time
    ensure_workflow(workflow_run_id, expected_prefix="WF2_")

    page_info = _load_unified_file_info(page_file_id)
    page_number = page_info.get("other_data", {}).get("page_number", "unknown") if page_info else "unknown"
    stage_key = f"ocr_page_{page_number}"

    mark_stage(workflow_run_id, stage_key, "running", start=True)
    start_time = time.time()

    result: dict[str, Any] | None = None
    error_msg: str | None = None
    text = ""

    try:
        result = run_ocr(page_file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"

    elapsed = int((time.time() - start_time) * 1000)

    if result:
        text = result.get("text", "")
        _update_file_fields(page_file_id, ocr_raw=text)
        message = f"OCR succeeded for page {page_number}, extracted {len(text)} chars in {elapsed}ms."
        mark_stage(workflow_run_id, stage_key, "succeeded", message=message, end=True)
    else:
        message = f"OCR failed for page {page_number}: {error_msg or 'OCR returned no results'}"
        mark_stage(workflow_run_id, stage_key, "failed", message=message, end=True)

    return (workflow_run_id, page_file_id, text)

@celery_app.task(name="wf2_merge_ocr_results")
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

    all_text = []
    failed_pages = []
    for result in results:
        if result and len(result) == 3:
            _, page_id, text = result
            if text:
                all_text.append(text)
            else:
                failed_pages.append(page_id)
    
    combined_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
    
    # Save the combined text to the parent PDF's other_data
    parent_file_info = _load_unified_file_info(file_id) or {}
    other_data = dict(parent_file_info.get("other_data", {}) or {})
    other_data["combined_ocr_text"] = combined_text
    if failed_pages:
        other_data["failed_ocr_pages"] = failed_pages
    update_other_data(file_id, other_data)

    message = f"Merged OCR text from {len(all_text)} pages. {len(failed_pages)} pages failed."
    status = "succeeded"
    if failed_pages:
        status = "failed"
        message += f" Failed pages: {', '.join(failed_pages)}"
    elif not combined_text:
        status = "failed"
        message = "OCR merge produced no text."

    mark_stage(workflow_run_id, "merge_ocr", status, message=message, end=True)

    if status != "succeeded":
        return workflow_run_id

    # Trigger the next step
    wf2_run_invoice_analysis.s(workflow_run_id).apply_async()

    return workflow_run_id

@celery_app.task(name="wf2_run_invoice_analysis")
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

        # Trigger finalization
        wf2_finalize.s(workflow_run_id).apply_async()

    except Exception as e:
        mark_stage(workflow_run_id, "invoice_analysis", "failed", message=str(e), end=True)
        raise

    return workflow_run_id

__all__ = [
    "wf1_run_ocr",
    "wf2_prepare_pdf_pages",
    "wf2_run_page_ocr",
    "wf2_merge_ocr_results",
    "wf2_run_invoice_analysis",
]
