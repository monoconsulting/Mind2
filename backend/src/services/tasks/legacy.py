from __future__ import annotations

import os
import sys
import time
from typing import Any, Callable, Optional, Tuple

from observability.metrics import track_task

from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)
from services.ocr import run_ocr

from .ai_pipeline_tasks import _run_ai_pipeline
from .base import celery_app, logger
from .history import _history
from .invoice_tasks import _maybe_advance_invoice_from_file, process_invoice_document
from .utils import file_utils as _file_utils_module
from .utils import invoice_utils as _invoice_utils_module
from .utils.file_utils import (
    _collect_text_hints,
    _get_file_type,
    _load_unified_file_info,
    _update_file_fields,
    _update_file_status,
)
from .utils.invoice_utils import (
    _INVOICE_PAGE_COMPLETE_STATUSES,
    _get_invoice_parent_id as _default_invoice_parent_id,
    _invoice_page_progress as _invoice_page_progress_dict,
)

_COMPLETE_PAGE_STATUSES = {str(value).lower() for value in _INVOICE_PAGE_COMPLETE_STATUSES}
_DOCUMENT_FAILURE_STATES: tuple[InvoiceDocumentStatus, ...] = tuple(
    status
    for status in (
        InvoiceDocumentStatus.IMPORTED,
        getattr(InvoiceDocumentStatus, "PROCESSING", None),
        InvoiceDocumentStatus.MATCHING,
    )
    if isinstance(status, InvoiceDocumentStatus)
)


def _resolve_tasks_callable(name: str, fallback: Callable[..., Any]) -> Callable[..., Any]:
    tasks_module = sys.modules.get("services.tasks")
    if tasks_module is not None:
        candidate = getattr(tasks_module, name, None)
        if callable(candidate):
            return candidate  # type: ignore[return-value]
    return fallback


def _invoice_page_progress(invoice_id: str, metadata: dict[str, Any] | None = None) -> Tuple[int, int]:
    """Legacy tuple-based progress helper kept for backwards compatibility."""

    tasks_module = sys.modules.get("services.tasks")
    cursor_factory: Callable[[], Any] | None = None
    if tasks_module is not None and hasattr(tasks_module, "db_cursor"):
        cursor_candidate = getattr(tasks_module, "db_cursor")
        _invoice_utils_module.db_cursor = cursor_candidate
        if callable(cursor_candidate):
            cursor_factory = cursor_candidate
    elif hasattr(_invoice_utils_module, "db_cursor") and callable(_invoice_utils_module.db_cursor):
        cursor_factory = _invoice_utils_module.db_cursor

    if metadata is not None:
        progress = _invoice_page_progress_dict(invoice_id, metadata)
        completed = int(progress.get("completed", 0) or 0)
        total = int(progress.get("total", 0) or 0)
        return completed, total

    if cursor_factory is not None:
        try:
            with cursor_factory() as cur:
                cur.execute(
                    "SELECT id, file_type, ai_status FROM unified_files WHERE original_file_id=%s ORDER BY created_at ASC",
                    (invoice_id,),
                )
                rows = cur.fetchall() or []
                if rows:
                    total = 0
                    completed = 0
                    for row in rows:
                        if not row:
                            continue
                        total += 1
                        status = None
                        if len(row) >= 3:
                            status = row[2]
                        elif len(row) >= 1:
                            status = row[-1]
                        if str(status or "").lower() in _COMPLETE_PAGE_STATUSES:
                            completed += 1
                    return completed, total

                cur.execute(
                    "SELECT ai_status FROM unified_files WHERE id=%s",
                    (invoice_id,),
                )
                row = cur.fetchone()
                if row:
                    status = row[0]
                    total = 1
                    completed = 1 if str(status or "").lower() in _COMPLETE_PAGE_STATUSES else 0
                    return completed, total
                return 0, 0
        except Exception:
            return 0, 0

    progress = _invoice_page_progress_dict(invoice_id, metadata)
    completed = int(progress.get("completed", 0) or 0)
    total = int(progress.get("total", 0) or 0)
    return completed, total


def _get_invoice_parent_id(file_id: str, file_type: Optional[str] = None) -> Optional[str]:
    ft = str(file_type or "").lower()
    if ft in {"invoice", "cc_pdf"}:
        return file_id

    tasks_module = sys.modules.get("services.tasks")
    loader = _resolve_tasks_callable("_load_unified_file_info", _load_unified_file_info)
    cursor_factory: Callable[[], Any] | None = None
    if tasks_module is not None and hasattr(tasks_module, "db_cursor"):
        cursor_candidate = getattr(tasks_module, "db_cursor")
        if callable(cursor_candidate):
            cursor_factory = cursor_candidate
        _file_utils_module.db_cursor = cursor_candidate
    elif hasattr(_file_utils_module, "db_cursor") and callable(_file_utils_module.db_cursor):
        cursor_factory = _file_utils_module.db_cursor

    info: dict[str, Any] = {}

    if not ft:
        try:
            raw_info = loader(file_id)
        except Exception:
            raw_info = None
        if isinstance(raw_info, dict):
            info = raw_info
            ft = str(info.get("file_type") or "").lower()

    if ft in {"invoice", "cc_pdf"}:
        return file_id

    parent_id: Optional[str] = None
    parent_type: Optional[str] = None
    performed_manual_lookup = False
    if ft in {"invoice_page", "cc_image"} and cursor_factory is not None:
        performed_manual_lookup = True
        try:
            with cursor_factory() as cur:
                cur.execute(
                    "SELECT original_file_id FROM unified_files WHERE id=%s",
                    (file_id,),
                )
                row = cur.fetchone()
                if row:
                    parent_id = row[0]
                if isinstance(parent_id, str) and parent_id:
                    cur.execute(
                        "SELECT file_type FROM unified_files WHERE id=%s",
                        (parent_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        parent_type = row[0]
        except Exception:
            parent_id = None
            parent_type = None

    if ft in {"invoice_page", "cc_image"} and not info and (not performed_manual_lookup or parent_id is None):
        try:
            raw_info = loader(file_id)
        except Exception:
            raw_info = None
        if isinstance(raw_info, dict):
            info = raw_info
            candidate = info.get("original_file_id") or info.get("id")
            if isinstance(candidate, str) and candidate and parent_id is None:
                parent_id = candidate

    if isinstance(parent_id, str) and parent_id:
        if parent_type is None and info:
            parent_type = info.get("file_type") if parent_id == info.get("id") else None
        if str(parent_type or "").lower() in {"invoice", "cc_pdf"}:
            return parent_id
        if parent_type is None:
            # When we cannot verify, keep legacy behaviour and return parent id best-effort.
            return parent_id

    return None


def _enqueue_invoice_ai_extraction(invoice_id: str) -> bool:
    """Schedule invoice AI extraction while honouring monkeypatched tests."""

    tasks_module = sys.modules.get("services.tasks")
    task: Any | None = None
    if tasks_module is not None:
        candidate = getattr(tasks_module, "process_invoice_ai_extraction", None)
        if callable(candidate) or hasattr(candidate, "delay"):
            task = candidate
    if task is None:
        task = process_invoice_ai_extraction
    try:
        if hasattr(task, "delay"):
            task.delay(invoice_id)  # type: ignore[attr-defined]
        else:
            task(invoice_id)
        return True
    except Exception:
        logger.warning("Failed to enqueue invoice AI extraction for %s", invoice_id, exc_info=True)
        return False


def _fail_invoice_processing(invoice_id: Optional[str], error: str | None) -> None:
    """Best-effort helper that marks an invoice as failed after OCR issues."""

    if not invoice_id:
        return

    transition_processing = _resolve_tasks_callable(
        "transition_processing_status",
        transition_processing_status,
    )
    transition_document = _resolve_tasks_callable(
        "transition_document_status",
        transition_document_status,
    )
    history_logger = _resolve_tasks_callable("_history", _history)

    try:
        transitioned = transition_processing(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.UPLOADED,
            ),
        )
    except Exception:
        transitioned = False

    if transitioned:
        try:
            transition_document(
                invoice_id,
                InvoiceDocumentStatus.FAILED,
                _DOCUMENT_FAILURE_STATES,
            )
        except Exception:
            logger.debug("Failed to transition document status for invoice %s", invoice_id, exc_info=True)

    history_logger(
        invoice_id,
        job="invoice_pipeline",
        status="error",
        ai_stage_name="Invoice-OCR",
        log_text="Invoice processing failed during OCR stage.",
        error_message=error,
    )


def _is_invoice_like(file_type: str, workflow_type: str, invoice_id: Optional[str]) -> bool:
    invoice_like_types = {"invoice", "invoice_page", "cc_pdf", "cc_image"}
    invoice_like_workflows = {"creditcard_invoice", "invoice", "invoice_import"}
    if invoice_id:
        return True
    if file_type in invoice_like_types:
        return True
    return workflow_type in invoice_like_workflows


@celery_app.task(name="process_ocr")
@track_task("process_ocr")
def process_ocr(file_id: str) -> dict[str, Any]:
    start_time = time.time()

    info = _load_unified_file_info(file_id) or {}
    file_type = str(info.get("file_type") or _get_file_type(file_id) or "").lower()
    workflow_type = str(info.get("workflow_type") or "").lower()
    invoice_parent_resolver = _resolve_tasks_callable("_get_invoice_parent_id", _default_invoice_parent_id)
    invoice_id = invoice_parent_resolver(file_id, file_type)

    history_logger = _resolve_tasks_callable("_history", _history)

    tasks_module = sys.modules.get("services.tasks")
    ocr_runner = run_ocr
    if tasks_module is not None:
        candidate = getattr(tasks_module, "run_ocr", None)
        if callable(candidate):
            ocr_runner = candidate  # type: ignore[assignment]

    try:
        result = ocr_runner(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {exc}"
        _update_file_status(file_id, status="manual_review", confidence=0.0)
        elapsed = int((time.time() - start_time) * 1000)
        history_logger(
            file_id,
            job="ocr",
            status="error",
            ai_stage_name="OCR-TextExtraction",
            log_text="OCR processing failed or returned no results",
            error_message=error_msg,
            confidence=0.0,
            processing_time_ms=elapsed,
            provider="paddleocr",
        )
        if _is_invoice_like(file_type, workflow_type, invoice_id):
            _maybe_advance_invoice_from_file(file_id, success=False)
            failure_hook = _resolve_tasks_callable("_fail_invoice_processing", _fail_invoice_processing)
            failure_hook(invoice_id, error_msg)
        return {
            "file_id": file_id,
            "status": "manual_review",
            "ok": False,
            "error": error_msg,
            "invoice_id": invoice_id,
        }

    text = (result or {}).get("text") or ""
    _update_file_fields(file_id, ocr_raw=text)
    _update_file_status(file_id, status="ocr_done", confidence=None)

    elapsed = int((time.time() - start_time) * 1000)
    text_len = len(text)
    text_preview = text[:100].replace("\n", " ") if text else ""
    detected = []
    if result.get("merchant_name"):
        detected.append(f"merchant='{result.get('merchant_name')}'")
    if result.get("gross_amount") is not None:
        detected.append(f"amount={result.get('gross_amount')}")
    if result.get("purchase_datetime"):
        detected.append(f"date={result.get('purchase_datetime')}")
    hints = _collect_text_hints(file_id)
    if hints:
        detected.append(f"hints={hints[:80]}{'...' if len(hints) > 80 else ''}")

    log_parts = [f"OCR completed successfully: extracted {text_len} characters of raw text"]
    if text_preview:
        log_parts.append(f"preview: '{text_preview}{'...' if text_len > 100 else ''}'")
    if detected:
        log_parts.append(f"detected: {', '.join(detected)}")

    history_logger(
        file_id,
        job="ocr",
        status="success",
        ai_stage_name="OCR-TextExtraction",
        log_text="; ".join(log_parts),
        confidence=None,
        processing_time_ms=elapsed,
        provider="paddleocr",
    )

    response: dict[str, Any] = {
        "file_id": file_id,
        "status": "ocr_done",
        "ok": True,
    }

    if _is_invoice_like(file_type, workflow_type, invoice_id):
        if invoice_id:
            _maybe_advance_invoice_from_file(file_id, success=True)
            progress_fn = _resolve_tasks_callable("_invoice_page_progress", _invoice_page_progress)
            completed, total = progress_fn(invoice_id)
            response.update(
                {
                    "invoice_id": invoice_id,
                    "pages_completed": completed,
                    "pages_total": total,
                }
            )
        else:
            logger.info("OCR treated file %s as invoice-like but no parent invoice resolved", file_id)
    else:
        tasks_module = sys.modules.get("services.tasks")
        pipeline_task: Any | None = None
        if tasks_module is not None:
            candidate = getattr(tasks_module, "process_ai_pipeline", None)
            if callable(candidate) or hasattr(candidate, "delay"):
                pipeline_task = candidate
        if pipeline_task is None:
            pipeline_task = process_ai_pipeline
        try:
            if hasattr(pipeline_task, "delay"):
                pipeline_task.delay(file_id)  # type: ignore[attr-defined]
            else:
                pipeline_task(file_id)
        except Exception:
            logger.warning("Failed to enqueue AI pipeline for %s", file_id, exc_info=True)

    return response


@celery_app.task(name="process_ai_pipeline")
@track_task("process_ai_pipeline")
def process_ai_pipeline(file_id: str) -> dict[str, Any]:
    start_time = time.time()
    history_logger = _resolve_tasks_callable("_history", _history)
    try:
        steps = _run_ai_pipeline(file_id)
        elapsed = int((time.time() - start_time) * 1000)
        history_logger(
            file_id,
            job="ai_pipeline",
            status="success",
            ai_stage_name="Pipeline-Complete",
            log_text=f"Completed {len(steps)} AI stages successfully: {', '.join(steps)}",
            processing_time_ms=elapsed,
        )
        return {"file_id": file_id, "steps": steps, "ok": True}
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {exc}"
        history_logger(
            file_id,
            job="ai_pipeline",
            status="error",
            ai_stage_name="Pipeline-Complete",
            log_text="AI pipeline failed, file marked for manual review",
            error_message=error_msg,
            processing_time_ms=elapsed,
        )
        _update_file_status(file_id, "manual_review")
        return {"file_id": file_id, "ok": False, "error": str(exc)}


@celery_app.task(name="process_invoice_ai_extraction")
@track_task("process_invoice_ai_extraction")
def process_invoice_ai_extraction(invoice_id: str) -> dict[str, Any]:
    """Legacy alias that delegates to the refactored invoice document task."""

    return process_invoice_document(invoice_id)


__all__ = [
    "process_ocr",
    "process_ai_pipeline",
    "process_invoice_ai_extraction",
    "_invoice_page_progress",
    "_enqueue_invoice_ai_extraction",
    "_fail_invoice_processing",
    "_get_invoice_parent_id",
    "run_ocr",
]
