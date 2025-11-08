from __future__ import annotations

from services.invoice_status import (
    transition_document_status,
    transition_line_status,
    transition_line_status_and_link,
    transition_processing_status,
)

from .base import celery_app, db_cursor, logger
from .dispatcher import dispatch_workflow
from .history import _history
from .ocr_tasks import (
    wf1_run_ocr,
    wf2_merge_ocr_results,
    wf2_prepare_pdf_pages,
    wf2_run_page_ocr,
)
from .ai_pipeline_tasks import (
    wf1_finalize,
    wf1_run_ai_pipeline,
    wf2_finalize,
    wf2_run_invoice_analysis,
)
from .creditcard_tasks import (
    auto_match_invoice_lines,
    refresh_invoice_match_state,
    wf3_firstcard_invoice,
)
from .invoice_tasks import (
    _enqueue_invoice_document,
    _maybe_advance_invoice_from_file,
    process_invoice_document,
)
from .utils.file_utils import (
    _collect_text_hints,
    _enforce_file_metadata,
    _get_file_type,
    _load_accounting_inputs,
    _load_ai_context,
    _load_receipt_items,
    _load_receipt_model,
    _load_unified_file_info,
    _save_accounting_entries,
    _update_file_fields,
    _update_file_status,
)
from .utils.invoice_utils import (
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_metadata,
    _persist_invoice_lines,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from .workflow import (
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

__all__ = [
    "celery_app",
    "logger",
    "db_cursor",
    "dispatch_workflow",
    "process_invoice_document",
    "wf1_run_ocr",
    "wf1_run_ai_pipeline",
    "wf1_finalize",
    "wf2_prepare_pdf_pages",
    "wf2_run_page_ocr",
    "wf2_merge_ocr_results",
    "wf2_run_invoice_analysis",
    "wf2_finalize",
    "wf3_firstcard_invoice",
    "auto_match_invoice_lines",
    "refresh_invoice_match_state",
    "begin_import_stage",
    "complete_import_stage",
    "log_import_decision",
    "log_import_event",
    "log_finalize_failure",
    "mark_stage",
    "ensure_workflow",
    "get_workflow_run",
    "get_workflow_stage",
    "transition_processing_status",
    "transition_document_status",
    "transition_line_status",
    "transition_line_status_and_link",
    "_history",
    "_load_unified_file_info",
    "_update_file_status",
    "_update_file_fields",
    "_enforce_file_metadata",
    "_collect_text_hints",
    "_load_ai_context",
    "_load_accounting_inputs",
    "_load_receipt_items",
    "_load_receipt_model",
    "_save_accounting_entries",
    "_get_invoice_parent_id",
    "_load_invoice_metadata",
    "_update_invoice_metadata",
    "_set_invoice_metadata_field",
    "_invoice_page_progress",
    "_enqueue_invoice_document",
    "_maybe_advance_invoice_from_file",
    "_persist_invoice_lines",
]
