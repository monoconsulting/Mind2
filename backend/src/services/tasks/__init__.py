from __future__ import annotations

from services.queue_manager import get_celery

celery_app = get_celery()

# Import task modules so Celery registers the tasks when the package is loaded.
from . import ai_pipeline_tasks, creditcard_tasks, ocr_tasks  # noqa: F401

from .dispatchers import dispatch_workflow
from .history import _history, _update_file_fields, _update_file_status
from .workflow_state import (
    begin_import_stage,
    complete_import_stage,
    ensure_workflow,
    get_workflow_run,
    get_workflow_stage,
    log_finalize_failure,
    log_import_decision,
    log_import_event,
    mark_stage,
)
from .ocr_tasks import (
    wf1_run_ocr,
    wf2_finalize,
    wf2_merge_ocr_results,
    wf2_prepare_pdf_pages,
    wf2_run_invoice_analysis,
    wf2_run_page_ocr,
)
from .ai_pipeline_tasks import wf1_finalize, wf1_run_ai_pipeline
from .creditcard_tasks import (
    auto_match_invoice_lines,
    process_invoice_document,
    refresh_invoice_match_state,
    wf3_firstcard_invoice,
)
from .utils.creditcard_utils import (
    _ensure_creditcard_pages_and_ocr,
    _load_credit_items_for_invoice,
    _persist_creditcard_invoice_items,
    _persist_creditcard_invoice_main,
    _persist_creditcard_invoice_ocr,
    _persist_invoice_lines,
    _select_credit_item_for_line,
)
from .utils.invoice_utils import (
    _collect_invoice_ocr_text,
    _enqueue_invoice_document,
    _enforce_file_metadata,
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_file_records,
    _load_invoice_metadata,
    _load_unified_file_info,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from .utils.status_utils import _maybe_advance_invoice_from_file, _move_to_manual_review

__all__ = [
    "_collect_invoice_ocr_text",
    "_ensure_creditcard_pages_and_ocr",
    "_enqueue_invoice_document",
    "_enforce_file_metadata",
    "_get_invoice_parent_id",
    "_history",
    "_invoice_page_progress",
    "_load_credit_items_for_invoice",
    "_load_invoice_file_records",
    "_load_invoice_metadata",
    "_load_unified_file_info",
    "_maybe_advance_invoice_from_file",
    "_move_to_manual_review",
    "_persist_creditcard_invoice_items",
    "_persist_creditcard_invoice_main",
    "_persist_creditcard_invoice_ocr",
    "_persist_invoice_lines",
    "_select_credit_item_for_line",
    "_set_invoice_metadata_field",
    "_update_file_fields",
    "_update_file_status",
    "_update_invoice_metadata",
    "auto_match_invoice_lines",
    "begin_import_stage",
    "celery_app",
    "complete_import_stage",
    "dispatch_workflow",
    "ensure_workflow",
    "get_workflow_run",
    "get_workflow_stage",
    "log_finalize_failure",
    "log_import_decision",
    "log_import_event",
    "mark_stage",
    "process_invoice_document",
    "refresh_invoice_match_state",
    "wf1_finalize",
    "wf1_run_ai_pipeline",
    "wf1_run_ocr",
    "wf2_finalize",
    "wf2_merge_ocr_results",
    "wf2_prepare_pdf_pages",
    "wf2_run_invoice_analysis",
    "wf2_run_page_ocr",
    "wf3_firstcard_invoice",
]
