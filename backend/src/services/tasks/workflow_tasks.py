from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from .common import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    AiStatus,
    CreditCardInvoiceExtractionRequest,
    DocumentClassificationRequest,
    celery_app,
    db_cursor,
    log_event,
    run_box_enrichment,
    transition_document_status,
    transition_processing_status,
)
from .ai_pipeline_tasks import _run_ai_pipeline, UnsupportedDocumentTypeError
from .creditcard_tasks import (
    _ensure_creditcard_pages_and_ocr,
    auto_match_invoice_lines,
    refresh_invoice_match_state,
)
from .file_management_tasks import (
    _collect_text_hints,
    _load_ai_context,
    _load_accounting_inputs,
    _load_receipt_items,
    _load_receipt_model,
    _maybe_advance_invoice_from_file,
    _move_to_manual_review,
    _save_accounting_entries,
    _update_file_status,
    _fail_invoice_processing,
)
from .history import _history
from .invoice_tasks import (
    _persist_creditcard_invoice_items,
    _persist_creditcard_invoice_main,
    _persist_creditcard_invoice_ocr,
    _persist_invoice_lines,
    _count_invoice_lines,
    process_invoice_document,
)
from .ocr_tasks import (
    wf1_run_ocr,
    wf2_merge_ocr_results,
    wf2_prepare_pdf_pages,
    wf2_run_invoice_analysis,
    wf2_run_page_ocr,
)
from .utils.invoice_utils import (
    _collect_invoice_ocr_text,
    _get_invoice_parent_id,
    _load_invoice_metadata,
    _load_unified_file_info,
    _update_invoice_metadata,
)
from .workflow_base import (
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
from services.ai_service import AIService, AiProviderError
from api.ai_processing import classify_document_internal
from services.workflow_coordinator import FirstCardWorkflowCoordinator

logger = logging.getLogger(__name__)

# TASK_INVENTORY: ACTIVE (2025-11-28). Dispatches workflow_run records to WF1/WF2/WF3 Celery chains.
def dispatch_workflow(workflow_run_id: int) -> bool:
    """Dispatch workflow based on workflow_key.

    Builds the correct Celery chain based on workflow_key:
    - WF1_RECEIPT ΓåÆ receipt processing chain (AI1-AI4 pipeline)
    - WF2_PDF_SPLIT ΓåÆ PDF split + credit card invoice processing chain (AI6 pipeline)

    Args:
        workflow_run_id: ID of the workflow_run to dispatch

    Returns:
        True if dispatched successfully, False otherwise
    """
    wfr = get_workflow_run(workflow_run_id)
    if not wfr:
        return False

    workflow_key = wfr.get("workflow_key")

    if not workflow_key:
        mark_stage(workflow_run_id, "dispatch", "failed", message="Workflow key is missing.")
        return False

    logger.info(
        "dispatch_workflow_start",
        extra={"workflow_run_id": workflow_run_id, "workflow_key": workflow_key},
    )

    try:
        if workflow_key == "WF1_RECEIPT":
            # WF1: Build the new, separated task chain
            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF1 dispatched to new wf1.* chain.")
            logger.info("Dispatching WF1 chain for run %s", workflow_run_id)
            (wf1_run_ocr.s(workflow_run_id) | wf1_run_ai_pipeline.s() | wf1_finalize.s()).apply_async()
            logger.info(
                "dispatch_workflow_enqueued",
                extra={"workflow_run_id": workflow_run_id, "workflow_key": workflow_key, "target": "wf1"},
            )
            return True

        elif workflow_key == "WF2_PDF_SPLIT":
            # WF2: Start the PDF processing chain
            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF2 dispatched to new wf2.* chain.")
            logger.info("Dispatching WF2 chain for run %s", workflow_run_id)
            wf2_prepare_pdf_pages.s(workflow_run_id).set(queue="wf2").apply_async()
            logger.info(
                "dispatch_workflow_enqueued",
                extra={"workflow_run_id": workflow_run_id, "workflow_key": workflow_key, "target": "wf2"},
            )
            return True

        elif workflow_key == "WF3_FIRSTCARD_INVOICE":
            # WF3: Start the FirstCard invoice processing chain
            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF3 dispatched to new wf3.* chain.")
            logger.info("Dispatching WF3 chain for run %s", workflow_run_id)
            wf3_firstcard_invoice.s(workflow_run_id).apply_async()
            logger.info(
                "dispatch_workflow_enqueued",
                extra={"workflow_run_id": workflow_run_id, "workflow_key": workflow_key, "target": "wf3"},
            )
            return True

        else:
            # Unknown workflow_key
            mark_stage(
                workflow_run_id,
                "dispatch",
                "failed",
                message=f"Unknown workflow_key: {workflow_key}",
            )
            logger.warning(
                "dispatch_workflow_unknown_key",
                extra={"workflow_run_id": workflow_run_id, "workflow_key": workflow_key},
            )
            return False

    except Exception as e:
        logger.exception(
            "dispatch_workflow_failed",
            extra={"workflow_run_id": workflow_run_id, "workflow_key": workflow_key},
        )
        mark_stage(workflow_run_id, "dispatch", "failed", message=f"Dispatch exception: {e}")
        return False

# TASK_INVENTORY: ACTIVE (2025-11-28). WF1 receipt AI1–AI4 pipeline executor.
@celery_app.task(name="wf1_run_ai_pipeline")
def wf1_run_ai_pipeline(workflow_run_id: int) -> int:
    """
    Workflow 1: AI Pipeline Task (AI1-AI4).

    - Ensures the task is part of a WF1 workflow.
    - Marks the 'ai_pipeline' stage as running.
    - Executes the AI pipeline (_run_ai_pipeline).
    - Marks the 'ai_pipeline' stage as 'succeeded' or 'failed'.
    - Returns the workflow_run_id for the next task.
    """
    import time
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF1_")
    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(workflow_run_id, "ai_pipeline", "failed", message="File ID missing in workflow run.")
        raise ValueError("File ID is missing.")

    # Check if previous stage succeeded
    ocr_stage = get_workflow_stage(workflow_run_id, "ocr")
    if not ocr_stage or ocr_stage.get('status') != 'succeeded':
        mark_stage(workflow_run_id, "ai_pipeline", "skipped", message="Skipping AI pipeline because OCR stage did not succeed.")
        return workflow_run_id

    mark_stage(workflow_run_id, "ai_pipeline", "running", start=True)
    start_time = time.time()
    logger.info(
        "wf1_run_ai_pipeline_start",
        extra={"workflow_run_id": workflow_run_id, "file_id": file_id},
    )

    try:
        steps = _run_ai_pipeline(file_id, workflow_run_id)
        elapsed = int((time.time() - start_time) * 1000)
        message = f"AI pipeline completed {len(steps)} stages in {elapsed}ms: {', '.join(steps)}"
        mark_stage(workflow_run_id, "ai_pipeline", "succeeded", message=message, end=True)
        logger.info(
            "wf1_run_ai_pipeline_succeeded",
            extra={"workflow_run_id": workflow_run_id, "file_id": file_id, "steps": steps, "duration_ms": elapsed},
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        message = f"AI pipeline failed after {elapsed}ms: {error_msg}"
        mark_stage(workflow_run_id, "ai_pipeline", "failed", message=message, end=True)
        logger.error(
            "wf1_run_ai_pipeline_failed",
            exc_info=True,
            extra={"workflow_run_id": workflow_run_id, "file_id": file_id, "duration_ms": elapsed},
        )
        # Do not re-raise, let the workflow system handle the failed state.

    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF1 finalization stage updating workflow status.
@celery_app.task(name="wf1_finalize")
def wf1_finalize(workflow_run_id: int) -> int:
    """
    Workflow 1: Finalize Task.

    - Ensures the task is part of a WF1 workflow.
    - Marks the 'finalize' stage as running.
    - Checks the status of previous stages.
    - Marks the entire workflow run as 'succeeded' or 'failed'.
    - Returns the workflow_run_id.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF1_")

    mark_stage(workflow_run_id, "finalize", "running", start=True)
    logger.info(
        "wf1_finalize_start",
        extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id")},
    )

    # Check status of the AI pipeline stage
    ai_stage = get_workflow_stage(workflow_run_id, "ai_pipeline")
    
    final_status = "succeeded"
    message = "Workflow completed successfully."

    if not ai_stage or ai_stage.get('status') != 'succeeded':
        final_status = "failed"
        message = "Workflow failed because a critical stage (ai_pipeline) did not succeed."

    # Update the main workflow_run status
    if db_cursor:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE workflow_runs SET status=%s, updated_at=NOW() WHERE id=%s",
                    (final_status, workflow_run_id),
                )
        except Exception as e:
            message = f"Finalize failed to update workflow status: {e}"
            final_status = "failed"
            logger.error(
                "wf1_finalize_db_update_failed",
                exc_info=True,
                extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id")},
            )

    # SoT alignment: do not leave unified_files.ai_status as 'completed' when workflow failed.
    # If the pipeline already sent the file to manual_review, do not override it.
    file_id = wfr.get("file_id")
    if final_status != "succeeded" and file_id and db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT ai_status FROM unified_files WHERE id=%s", (file_id,))
                row = cur.fetchone()
            current_status = row[0] if row else None
            if current_status not in (AiStatus.MANUAL_REVIEW.value, AiStatus.FAILED.value):
                from services.db.files import set_ai_status

                set_ai_status(file_id, AiStatus.FAILED.value)
        except Exception:
            logger.debug(
                "wf1_finalize_ai_status_update_failed",
                exc_info=True,
                extra={"workflow_run_id": workflow_run_id, "file_id": file_id},
            )

    mark_stage(
        workflow_run_id,
        "finalize",
        final_status,
        message=message,
        end=True,
        workflow_status_override=final_status,
    )

    if final_status == "succeeded":
        begin_import_stage(
            workflow_run_id,
            "finalize_ok",
            message="WF1 slutf├╢rd",
        )
        complete_import_stage(
            workflow_run_id,
            "finalize_ok",
            success=True,
            message="Kvittofl├╢det avslutat utan fel",
        )
        log_import_event(
            workflow_run_id,
            "KLAR",
            message="WF1 slutf├╢rd",
        )
    else:
        log_finalize_failure(workflow_run_id, message or "WF1 misslyckades")

    logger.info(
        "wf1_finalize_complete",
        extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id"), "status": final_status},
    )
    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF2 finalization stage updating workflow status.
@celery_app.task(name="wf2_finalize", queue="wf2")
def wf2_finalize(workflow_run_id: int) -> int:
    """
    Workflow 2: Finalize Task.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    mark_stage(workflow_run_id, "finalize", "running", start=True)
    logger.info(
        "wf2_finalize_start",
        extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id")},
    )

    analysis_stage = get_workflow_stage(workflow_run_id, "invoice_analysis")
    
    final_status = "succeeded"
    message = "Workflow completed successfully."

    if not analysis_stage or analysis_stage.get('status') != 'succeeded':
        final_status = "failed"
        message = "Workflow failed because a critical stage (invoice_analysis) did not succeed."

    if db_cursor:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE workflow_runs SET status=%s, updated_at=NOW() WHERE id=%s",
                    (final_status, workflow_run_id),
                )
        except Exception as e:
            message = f"Finalize failed to update workflow status: {e}"
            final_status = "failed"
            logger.error(
                "wf2_finalize_db_update_failed",
                exc_info=True,
                extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id")},
            )

    mark_stage(
        workflow_run_id,
        "finalize",
        final_status,
        message=message,
        end=True,
        workflow_status_override=final_status,
    )

    if final_status == "succeeded":
        begin_import_stage(
            workflow_run_id,
            "finalize_ok",
            message="WF2 slutförd",
        )
        complete_import_stage(
            workflow_run_id,
            "finalize_ok",
            success=True,
            message="PDF-split-flödet avslutat utan fel",
        )
        log_import_event(
            workflow_run_id,
            "KLAR",
            message="WF2 slutförd",
        )
    else:
        log_finalize_failure(workflow_run_id, message or "WF2 misslyckades")

    logger.info(
        "wf2_finalize_complete",
        extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id"), "status": final_status},
    )
    return workflow_run_id

# TASK_INVENTORY: ACTIVE (2025-11-28). WF3 FirstCard invoice orchestration (OCR → AI6 → AI5 match).
@celery_app.task(name="wf3_firstcard_invoice")
def wf3_firstcard_invoice(workflow_run_id: int) -> int:
    """
    Workflow 3: FirstCard Invoice Processing.
    """
    fc_coordinator = FirstCardWorkflowCoordinator()
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF3_")
    fc_coordinator.begin_fc_import_stage(workflow_run_id, "firstcard_invoice", "Workflow running")

    file_id = wfr.get("file_id")
    invoice_id = file_id  # unified_files.id is the invoice identifier for WF3
    if not file_id:
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "firstcard_invoice",
            success=False,
            message="Workflow run missing file_id.",
        )
        log_finalize_failure(workflow_run_id, "Workflow run saknar file_id")
        raise ValueError("Workflow run missing file_id")

    metadata = _load_invoice_metadata(file_id) or {}

    fc_coordinator.begin_fc_import_stage(
        workflow_run_id,
        "fc_ocr",
        message=f"F├╢rbereder OCR f├╢r FirstCard {file_id}",
    )
    try:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.OCR_PENDING,
            (
                InvoiceProcessingStatus.UPLOADED,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
    except Exception:
        logger.debug(
            "wf3_firstcard_invoice_ocr_pending_transition_failed",
            exc_info=True,
            extra={"workflow_run_id": workflow_run_id, "file_id": file_id},
        )

    parent_info = _load_unified_file_info(file_id) or {}

    try:
        combined_text, other_data = _ensure_creditcard_pages_and_ocr(file_id, parent_info)
        parent_file_type = parent_info.get("file_type") or "unknown"
        parent_workflow_type = parent_info.get("workflow_type") or "unknown"
        page_count = len(other_data.get("pages") or [])
        logger.info(
            "WF3 run %s prepared invoice %s (file_type=%s, workflow_type=%s, pages=%d)",
            workflow_run_id,
            file_id,
            parent_file_type,
            parent_workflow_type,
            page_count,
        )
        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "firstcard_invoice",
            message=f"file_type={parent_file_type}; workflow_type={parent_workflow_type}; pages={page_count}",
        )
        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "ocr_merge",
            message="Merging OCR results",
        )

        merged_main_id: Optional[int] = None
        if combined_text:
            merged_main_id = _persist_creditcard_invoice_ocr(file_id, combined_text, metadata)

        ocr_length = len(combined_text or "")
        if merged_main_id:
            if not metadata.get("creditcard_main_id"):
                metadata["creditcard_main_id"] = merged_main_id
            metadata.setdefault("creditcard_invoice_number", f"INV-{file_id}")
            fc_coordinator.complete_fc_import_stage(
                workflow_run_id,
                "ocr_merge",
                success=True,
                message=f"Persisted merged OCR ({ocr_length} chars) to creditcard_invoices_main id={merged_main_id}",
            )
            logger.info(
                "WF3 run %s persisted %d merged OCR chars for invoice %s (main_id=%s)",
                workflow_run_id,
                ocr_length,
                file_id,
                merged_main_id,
            )
        else:
            if not combined_text:
                fc_coordinator.complete_fc_import_stage(
                    workflow_run_id,
                    "ocr_merge",
                    success=True, # Skipped is effectively success for this stage? Or should I use success=False? Skipped usually implies not failed.
                    message="No OCR text available to persist (skipped)",
                )
            else:
                fc_coordinator.complete_fc_import_stage(
                    workflow_run_id,
                    "ocr_merge",
                    success=False,
                    message="Failed to persist merged OCR text to creditcard_invoices_main",
                )
                logger.error(
                    "WF3 run %s could not persist merged OCR text for invoice %s",
                    workflow_run_id,
                    file_id,
                )
                raise RuntimeError("Unable to persist merged OCR text to creditcard_invoices_main")

        metadata.update(
            {
                "page_count": page_count,
                "processing_status": InvoiceProcessingStatus.OCR_DONE.value,
                "combined_ocr_text": combined_text,
                "merged_ocr_length": ocr_length,
            }
        )
        _update_invoice_metadata(file_id, metadata)
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.OCR_DONE,
            (
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
    except Exception as exc:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.UPLOADED,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "firstcard_invoice",
            success=False,
            message=f"OCR preparation failed: {exc}",
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_ocr",
            success=False,
            message=str(exc),
        )
        log_finalize_failure(workflow_run_id, f"OCR-misslyckande: {exc}")
        raise
    else:
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_ocr",
            success=True,
            message=f"OCR klar ({ocr_length} tecken)",
        )

    if combined_text:
        classification = classify_document_internal(
            DocumentClassificationRequest(file_id=file_id, ocr_text=combined_text)
        )
        doc_type_norm = (classification.document_type or "").strip().lower()
        is_fc_invoice = doc_type_norm == "fc_invoice"
        # log_import_decision is a helper, we can replace it or keep it if it uses mark_stage internally.
        # But D2 says replace direct creation/updates. log_import_decision uses _log_import_stage which uses mark_stage.
        # So we should replace it.
        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "fc_is_fc",
            message=f"AI1 identifierade dokumenttyp: {classification.document_type}",
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_is_fc",
            success=is_fc_invoice,
            message=f"AI1 identifierade dokumenttyp: {classification.document_type}",
        )

        if not is_fc_invoice:
            reason = (
                f"AI1 klassificerade dokumentet som '{classification.document_type}' "
                "men endast FC-fakturor till├Ñts i detta fl├╢de."
            )
            fc_coordinator.begin_fc_import_stage(workflow_run_id, AiStatus.MANUAL_REVIEW.value, message=reason)
            fc_coordinator.complete_fc_import_stage(workflow_run_id, AiStatus.MANUAL_REVIEW.value, success=True, message=reason)
            _move_to_manual_review(file_id, reason)
            log_finalize_failure(workflow_run_id, reason)
            fc_coordinator.complete_fc_import_stage(
                workflow_run_id,
                "firstcard_invoice",
                success=False,
                message=reason,
            )
            raise UnsupportedDocumentTypeError(reason)

    try:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.AI_PROCESSING,
            (
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                InvoiceProcessingStatus.COMPLETED,
            ),
        )
    except Exception:
        logger.debug(
            "wf3_firstcard_invoice_ai_processing_transition_failed",
            exc_info=True,
            extra={"workflow_run_id": workflow_run_id, "file_id": file_id},
        )

    page_ids = [page.get("file_id") for page in (other_data.get("pages") or []) if page.get("file_id")]

    from services.ai_service import AIService

    ai_service = AIService()
    request = CreditCardInvoiceExtractionRequest(
        invoice_id=invoice_id,
        ocr_text=combined_text,
        page_ids=page_ids,
    )

    import time
    start_time = time.time()
    ai6_provider = ai_service.prompt_provider_names.get("credit_card_invoice_parsing", "unknown")
    ai6_model = ai_service.prompt_model_names.get("credit_card_invoice_parsing", "unknown")
    ai6_prompt = ai_service.prompts.get("credit_card_invoice_parsing", "")
    raw_response = ""
    fc_coordinator.begin_fc_import_stage(workflow_run_id, "fc_parse", message="AI6 tolkning av faktura")
    try:
        extraction = ai_service.run_ai6_credit_card_invoice_parsing(request)
        elapsed = int((time.time() - start_time) * 1000)

        raw_response = ai_service.last_raw_response or ""
        _history(
            file_id,
            "ai6",
            "success",
            ai_stage_name="AI6-CreditCardInvoiceParsing",
            log_text=f"Successfully parsed credit card invoice ({len(extraction.lines)} lines)",
            confidence=extraction.overall_confidence,
            processing_time_ms=elapsed,
            provider=ai6_provider,
            model_name=ai6_model,
            prompt_text=ai6_prompt,
            response_text=raw_response,
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_parse",
            success=True,
            message=f"Tolkade {len(extraction.lines)} rader",
        )
        ai7_stats = run_box_enrichment(file_id)
        if not ai7_stats.get("success"):
            logger.warning(
                "AI7 box enrichment failed for %s after AI6: %s",
                file_id,
                ai7_stats.get("error", "unknown"),
            )
    except AiProviderError as exc:
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_parse",
            success=False,
            message=f"AI6 provider failed: {exc}",
        )
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        _fail_invoice_processing(invoice_id, f"AI6 provider failed: {exc}")
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "firstcard_invoice",
            success=False,
            message=f"AI6 provider failed: {exc}",
        )
        log_finalize_failure(workflow_run_id, f"AI6 provider failed: {exc}")
        return workflow_run_id
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {exc}"
        raw_response = ai_service.last_raw_response or ""

        _history(
            file_id,
            "ai6",
            "error",
            ai_stage_name="AI6-CreditCardInvoiceParsing",
            log_text="Failed to parse credit card invoice.",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai6_provider,
            model_name=ai6_model,
            prompt_text=ai6_prompt,
            response_text=raw_response,
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_parse",
            success=False,
            message=error_msg,
        )
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "firstcard_invoice",
            success=False,
            message=f"AI6 parsing failed: {type(exc).__name__}: {exc}",
        )
        log_finalize_failure(workflow_run_id, f"AI6 misslyckades: {exc}")
        raise

    main_id = _persist_creditcard_invoice_main(file_id, extraction.header, combined_text)
    if not main_id:
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "firstcard_invoice",
            success=False,
            message="Failed to persist credit card invoice header.",
        )
        log_finalize_failure(workflow_run_id, "Misslyckades att spara huvuddata")
        raise RuntimeError("Failed to persist credit card invoice header")

    items_inserted = _persist_creditcard_invoice_items(main_id, extraction.lines)

    invoice_line_payloads: list[dict[str, Any]] = []
    for line in extraction.lines:
        amount_candidate = (
            line.amount_sek
            or line.gross_amount
            or line.amount_original
            or Decimal("0.00")
        )
        amount_float = float(amount_candidate) if amount_candidate is not None else 0.0
        invoice_line_payloads.append(
            {
                "transaction_date": line.purchase_date.isoformat() if hasattr(line.purchase_date, "isoformat") else None,
                "merchant_name": line.merchant_name or "",
                "description": line.description or (line.merchant_name or ""),
                "amount": amount_float,
                "confidence": line.confidence,
                "raw_text": line.source_text or "",
            }
        )

    inserted_invoice_lines = _persist_invoice_lines(file_id, invoice_line_payloads)

    metadata = _load_invoice_metadata(file_id) or {}
    metadata.setdefault("processing_status", InvoiceProcessingStatus.AI_PROCESSING.value)
    metadata["creditcard_main_id"] = main_id
    metadata["overall_confidence"] = extraction.overall_confidence
    metadata["invoice_summary"] = {
        "invoice_number": extraction.header.invoice_number,
        "card_holder": extraction.header.card_holder,
        "currency": extraction.header.currency,
        "amount_to_pay": float(extraction.header.amount_to_pay)
        if extraction.header.amount_to_pay is not None
        else None,
    }
    actual_invoice_number = (
        extraction.header.invoice_number
        or metadata.get("creditcard_invoice_number")
        or f"INV-{file_id}"
    )
    metadata["creditcard_invoice_number"] = actual_invoice_number
    if extraction.header.period_start:
        metadata["period_start"] = extraction.header.period_start.isoformat()
    if extraction.header.period_end:
        metadata["period_end"] = extraction.header.period_end.isoformat()
    extracted_total = len(extraction.lines)
    persisted_total = _count_invoice_lines(file_id)

    metadata["line_counts"] = {
        "total": persisted_total,
        "matched": 0,
        "unmatched": persisted_total,
        "extracted_total": extracted_total,
        "persisted_total": persisted_total,
        "persist_attempted": inserted_invoice_lines,
    }

    if extracted_total == 0 or persisted_total == 0 or persisted_total != extracted_total:
        if extracted_total == 0:
            reason = "AI6 produced 0 invoice lines; cannot proceed to matching."
        elif persisted_total == 0:
            reason = (
                "Persisted 0 invoice lines although AI6 returned lines. "
                "This strongly indicates a DB schema mismatch (migrations not applied) or a SQL error."
            )
        else:
            reason = (
                f"Persisted invoice line count mismatch: extracted={extracted_total}, persisted={persisted_total}. "
                "Stop-the-line to avoid matching on incomplete data."
            )

        metadata["processing_status"] = InvoiceProcessingStatus.FAILED.value
        metadata["last_error"] = {
            "code": "invoice_lines_persist_failed",
            "message": reason,
            "extracted_total": extracted_total,
            "persisted_total": persisted_total,
        }
        _update_invoice_metadata(file_id, metadata)

        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "fc_ready",
            message="Förbereder fakturan för matchning",
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "fc_ready",
            success=False,
            message=reason,
        )
        transition_processing_status(
            file_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                InvoiceProcessingStatus.COMPLETED,
                InvoiceProcessingStatus.FAILED,
            ),
        )
        transition_document_status(
            file_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.MATCHED,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
                InvoiceDocumentStatus.PROCESSING,
                InvoiceDocumentStatus.COMPLETED,
                InvoiceDocumentStatus.FAILED,
            ),
        )
        logger.error(
            "wf3_fc_invoice_lines_persist_failed invoice_id=%s extracted_total=%s persisted_total=%s",
            file_id,
            extracted_total,
            persisted_total,
        )
        log_finalize_failure(workflow_run_id, reason)
        return workflow_run_id

    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
    _update_invoice_metadata(file_id, metadata)

    fc_coordinator.begin_fc_import_stage(
        workflow_run_id,
        "fc_ready",
        message="F├╢rbereder fakturan f├╢r matchning",
    )
    transition_processing_status(
        file_id,
        InvoiceProcessingStatus.READY_FOR_MATCHING,
        (
            InvoiceProcessingStatus.AI_PROCESSING,
            InvoiceProcessingStatus.OCR_DONE,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            InvoiceProcessingStatus.MATCHING_COMPLETED,
            InvoiceProcessingStatus.COMPLETED,
        ),
    )
    transition_document_status(
        file_id,
        InvoiceDocumentStatus.MATCHING,
        (
            InvoiceDocumentStatus.IMPORTED,
            InvoiceDocumentStatus.MATCHING,
            InvoiceDocumentStatus.MATCHED,
            InvoiceDocumentStatus.PARTIALLY_MATCHED,
            InvoiceDocumentStatus.COMPLETED,
        ),
    )
    fc_coordinator.complete_fc_import_stage(
        workflow_run_id,
        "fc_ready",
        success=True,
        message="Fakturan redo f├╢r AI5",
    )

    try:
        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "auto_match",
            message="Auto-match running",
        )
        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "ai5",
            message="AI5 kortmatchning startar",
        )
        matched_auto, evaluated = auto_match_invoice_lines(file_id)
        total_lines, matched_lines = refresh_invoice_match_state(file_id)
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "auto_match",
            success=True,
            message=f"Auto-matched {matched_lines} of {total_lines} lines (new matches: {matched_auto})",
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "ai5",
            success=True,
            message=f"AI5 matchade {matched_lines}/{total_lines} rader",
        )
        has_match = matched_lines > 0
        fc_coordinator.begin_fc_import_stage(
            workflow_run_id,
            "m_found",
            message="Match hittad" if has_match else "Inga automatiska matchningar",
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "m_found",
            success=has_match,
            message="Match hittad" if has_match else "Inga automatiska matchningar",
        )
        if has_match:
            fc_coordinator.begin_fc_import_stage(
                workflow_run_id,
                "m_link",
                message="L├ñnkar kvitton till fakturarader",
            )
            fc_coordinator.complete_fc_import_stage(
                workflow_run_id,
                "m_link",
                success=True,
                message=f"{matched_lines} rader l├ñnkade",
            )
        unmatched_count = max(total_lines - matched_lines, 0)
        if unmatched_count > 0:
            fc_coordinator.begin_fc_import_stage(
                workflow_run_id,
                "m_unmatched",
                message="Flaggar omatchade rader",
            )
            fc_coordinator.complete_fc_import_stage(
                workflow_run_id,
                "m_unmatched",
                success=True,
                message=f"{unmatched_count} rader kvar att hantera",
            )
    except Exception as exc:
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "auto_match",
            success=False,
            message=f"Auto-match failed: {exc}",
        )
        fc_coordinator.complete_fc_import_stage(
            workflow_run_id,
            "ai5",
            success=False,
            message=f"AI5 misslyckades: {exc}",
        )
        logger.error(
            "wf3_firstcard_invoice_auto_match_failed",
            exc_info=True,
            extra={"workflow_run_id": workflow_run_id, "file_id": file_id},
        )

    fc_coordinator.complete_fc_import_stage(
        workflow_run_id,
        "firstcard_invoice",
        success=True,
        message=f"Parsed credit card invoice: main_id={main_id}, lines={items_inserted}/{inserted_invoice_lines}",
    )
    fc_coordinator.begin_fc_import_stage(
        workflow_run_id,
        "finalize_ok",
        message="FirstCard-fl├╢det klart",
    )
    fc_coordinator.complete_fc_import_stage(
        workflow_run_id,
        "finalize_ok",
        success=True,
        message="Fakturafl├╢det avslutades utan fel",
    )
    fc_coordinator.begin_fc_import_stage(
        workflow_run_id,
        "KLAR",
        message="WF3 slutf├╢rd",
    )
    fc_coordinator.complete_fc_import_stage(
        workflow_run_id,
        "KLAR",
        success=True,
        message="WF3 slutf├╢rd",
    )
    # SoT compliance: mark workflow as succeeded and set ai_status to completed
    try:
        if db_cursor:
            with db_cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_runs
                       SET status=%s,
                           current_stage=%s,
                           updated_at=NOW()
                     WHERE id=%s
                    """,
                    ("succeeded", "KLAR", workflow_run_id),
                )
        if wfr and wfr.get("file_id"):
            from services.db.files import set_ai_status

            set_ai_status(wfr["file_id"], AiStatus.COMPLETED.value)
            logger.info(
                "wf3_firstcard_invoice_complete_status_set",
                extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id")},
            )
    except Exception:
        logger.error(
            "wf3_firstcard_invoice_finalize_status_failed",
            exc_info=True,
            extra={"workflow_run_id": workflow_run_id, "file_id": wfr.get("file_id") if wfr else None},
        )

    return workflow_run_id

__all__ = [
    "dispatch_workflow",
    "wf1_run_ai_pipeline",
    "wf1_finalize",
    "wf2_finalize",
    "wf3_firstcard_invoice",
]
