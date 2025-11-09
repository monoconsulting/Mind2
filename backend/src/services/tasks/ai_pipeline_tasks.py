from __future__ import annotations

import json
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from observability.events import log_event
from observability.metrics import record_invoice_decision

from services.ai_service import AIService
from services.accounting import propose_accounting_entries
from services.box_enrichment import run_box_enrichment
from services.enrichment import enrich_receipt, provider_from_env
from services.validation import validate_receipt
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)
from services.invoice_parser import parse_credit_card_statement
from services.db.files import set_ai_status, update_other_data

from models.accounting import AccountingRule
from models.receipts import AccountingEntry, Receipt, ReceiptStatus

from api.ai_processing import (
    classify_accounting_internal,
    classify_document_internal,
    classify_expense_internal,
    extract_data_internal,
)

from .base import celery_app, db_cursor, logger
from .history import _history
from .utils.file_utils import (
    _collect_text_hints,
    _load_accounting_inputs,
    _load_ai_context,
    _load_receipt_items,
    _load_receipt_model,
    _save_accounting_entries,
    _load_unified_file_info,
)
from .utils.invoice_utils import _persist_invoice_lines
from .workflow import (
    begin_import_stage,
    complete_import_stage,
    ensure_workflow,
    get_workflow_stage,
    log_finalize_failure,
    log_import_event,
    mark_stage,
)


def _move_to_manual_review(file_id: str, reason: str | None = None) -> None:
    """Best-effort helper that marks a file as requiring manual review."""

    try:
        set_ai_status(file_id, "manual_review")
    except Exception:
        logger.debug("Failed to set manual review status for %s", file_id)
    if reason:
        log_event(logger, "ai.manual_review", file_id=file_id, reason=reason)



class UnsupportedDocumentTypeError(RuntimeError):
    """Raised when AI1 can not categorize a document into an allowed type."""

def _run_ai_pipeline(file_id: str, workflow_run_id: int | None = None) -> List[str]:
    """Run the complete AI pipeline (AI1-AI4) with detailed logging."""
    import time
    from services.ai_service import AIService

    if db_cursor is None:
        raise RuntimeError("Database unavailable for AI pipeline")

    steps: List[str] = []
    ai_service = AIService()

    context = _load_ai_context(file_id)
    if context is None:
        error_msg = f"File {file_id} not found in unified_files"
        _history(
            file_id,
            "ai_pipeline",
            "error",
            ai_stage_name="Pipeline-Initialization",
            log_text="Failed to load file context from database",
            error_message=error_msg,
        )
        raise ValueError(error_msg)
    ocr_text, document_type, expense_type = context

    # AI1 - Document Classification
    start_time = time.time()
    ai1_provider = ai_service.prompt_provider_names.get("document_analysis", "unknown")
    ai1_model = ai_service.prompt_model_names.get("document_analysis", "unknown")
    begin_import_stage(workflow_run_id, "detect_type", message=f"AI1 klassificering för fil {file_id}")
    try:
        result = classify_document_internal(
            DocumentClassificationRequest(file_id=file_id, ocr_text=ocr_text or "")
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI1")

        ai1_prompt = ai_service.prompts.get("document_analysis", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Classified document as '{result.document_type}'",
            f"OCR text length: {len(ocr_text or '')} characters",
            f"--- PROMPT ---\n{ai1_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]
        if result.reasoning:
            log_parts.append(f"Reasoning: {result.reasoning}")

        _history(
            file_id,
            "ai1",
            "success",
            ai_stage_name="AI1-DocumentClassification",
            log_text="; ".join(log_parts),
            confidence=result.confidence,
            processing_time_ms=elapsed,
            provider=ai1_provider,
            model_name=ai1_model,
        )

        # Update file_type column with classified document_type
        if db_cursor is not None and result.document_type:
            try:
                with db_cursor() as cur:
                    cur.execute(
                        "UPDATE unified_files SET file_type=%s, updated_at=NOW() WHERE id=%s",
                        (result.document_type, file_id),
                    )
            except Exception:
                pass  # Best-effort update, don't fail the pipeline
        doc_type_norm = (result.document_type or "").strip().lower()
        allowed_doc_types = {"receipt", "invoice", "fc_invoice"}
        if doc_type_norm not in allowed_doc_types:
            reason = (
                f"AI1 kunde inte kategorisera dokumentet (fick '{result.document_type}' "
                "utanför tillåtna typer)."
            )
            complete_import_stage(workflow_run_id, "detect_type", success=False, message=reason)
            log_import_event(workflow_run_id, "manual_review", message=reason)
            _move_to_manual_review(file_id, reason)
            raise UnsupportedDocumentTypeError(reason)
        complete_import_stage(
            workflow_run_id,
            "detect_type",
            success=True,
            message=f"Klassificerad som {result.document_type}",
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        _history(
            file_id,
            "ai1",
            "error",
            ai_stage_name="AI1-DocumentClassification",
            log_text=f"Failed to classify document type from OCR text ({len(ocr_text or '')} chars)",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai1_provider,
            model_name=ai1_model,
        )
        complete_import_stage(
            workflow_run_id,
            "detect_type",
            success=False,
            message=error_msg,
        )
        raise

    # Reload context after AI1
    context = _load_ai_context(file_id) or context
    ocr_text, document_type, expense_type = context

    # AI2 - Expense Classification
    start_time = time.time()
    ai2_provider = ai_service.prompt_provider_names.get("expense_classification", "unknown")
    ai2_model = ai_service.prompt_model_names.get("expense_classification", "unknown")
    try:
        result = classify_expense_internal(
            ExpenseClassificationRequest(
                file_id=file_id,
                ocr_text=ocr_text or "",
                document_type=document_type or "other",
            )
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI2")

        ai2_prompt = ai_service.prompts.get("expense_classification", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Classified expense as '{result.expense_type}'",
            f"Document type: {document_type or 'other'}",
            f"--- PROMPT ---\n{ai2_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]
        if result.card_identifier:
            log_parts.append(f"Card identifier: {result.card_identifier}")
        if result.reasoning:
            log_parts.append(f"Reasoning: {result.reasoning}")

        _history(
            file_id,
            "ai2",
            "success",
            ai_stage_name="AI2-ExpenseClassification",
            log_text="; ".join(log_parts),
            confidence=result.confidence,
            processing_time_ms=elapsed,
            provider=ai2_provider,
            model_name=ai2_model,
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        _history(
            file_id,
            "ai2",
            "error",
            ai_stage_name="AI2-ExpenseClassification",
            log_text=f"Failed to classify expense type for document_type='{document_type}'",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai2_provider,
            model_name=ai2_model,
        )
        raise

    # Reload context after AI2
    context = _load_ai_context(file_id) or context
    ocr_text, document_type, expense_type = context

    # AI3 - Data Extraction
    start_time = time.time()
    ai3_provider = ai_service.prompt_provider_names.get("data_extraction", "unknown")
    ai3_model = ai_service.prompt_model_names.get("data_extraction", "unknown")
    begin_import_stage(workflow_run_id, "r_ai3", message="AI3 dataextraktion startar")
    try:
        result = extract_data_internal(
            DataExtractionRequest(
                file_id=file_id,
                ocr_text=ocr_text or "",
                document_type=document_type or "other",
                expense_type=expense_type or "personal",
            )
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI3")

        # Comprehensive extraction logging - include ALL fields
        extracted = []
        if result.unified_file:
            uf = result.unified_file
            # Financial data
            if uf.gross_amount_original:
                extracted.append(f"gross={uf.gross_amount_original}")
            if uf.net_amount_original:
                extracted.append(f"net={uf.net_amount_original}")
            if uf.gross_amount_sek:
                extracted.append(f"gross_sek={uf.gross_amount_sek}")
            if uf.net_amount_sek:
                extracted.append(f"net_sek={uf.net_amount_sek}")
            if uf.currency:
                extracted.append(f"currency={uf.currency}")
            if uf.exchange_rate:
                extracted.append(f"exchange_rate={uf.exchange_rate}")
            # Business data
            if uf.orgnr:
                extracted.append(f"orgnr={uf.orgnr}")
            if uf.purchase_datetime:
                extracted.append(f"purchase_date={uf.purchase_datetime}")
            if uf.payment_type:
                extracted.append(f"payment_type={uf.payment_type}")
            if uf.expense_type:
                extracted.append(f"expense_type={uf.expense_type}")
            if uf.receipt_number:
                extracted.append(f"receipt_number={uf.receipt_number}")

        item_count = len(result.receipt_items or [])

        # Detailed company extraction logging
        company_details = []
        if result.company:
            if result.company.name:
                company_details.append(f"name='{result.company.name}'")
            if result.company.orgnr:
                company_details.append(f"orgnr='{result.company.orgnr}'")
            if result.company.address:
                company_details.append(f"address='{result.company.address}'")
            if result.company.city:
                company_details.append(f"city='{result.company.city}'")
            if result.company.zip:
                company_details.append(f"zip='{result.company.zip}'")
            if result.company.country:
                company_details.append(f"country='{result.company.country}'")

        # Receipt items summary
        items_summary = []
        if result.receipt_items and len(result.receipt_items) > 0:
            for idx, item in enumerate(result.receipt_items[:3], 1):  # Show first 3 items
                items_summary.append(f"{item.name}@{item.item_total_price_inc_vat}")
            if len(result.receipt_items) > 3:
                items_summary.append(f"... +{len(result.receipt_items) - 3} more")

        ai3_prompt = ai_service.prompts.get("data_extraction", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Extracted data: {', '.join(extracted) if extracted else 'NO DATA'}",
            f"--- PROMPT ---\n{ai3_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]
        if company_details:
            log_parts.append(f"Company: {'; '.join(company_details)}")
        else:
            log_parts.append("Company: NO COMPANY DATA EXTRACTED")

        # Critical: Warn if no receipt_items were extracted
        if item_count == 0:
            log_parts.append("WARNING: 0 receipt_items extracted from LLM - check prompt and LLM response!")
        else:
            log_parts.append(f"Items: {item_count} total")
            if items_summary:
                log_parts.append(f"Sample items: [{', '.join(items_summary)}]")

        _history(
            file_id,
            "ai3",
            "success",
            ai_stage_name="AI3-DataExtraction",
            log_text="; ".join(log_parts),
            confidence=result.confidence,
            processing_time_ms=elapsed,
            provider=ai3_provider,
            model_name=ai3_model,
        )
        complete_import_stage(
            workflow_run_id,
            "r_ai3",
            success=True,
            message=f"AI3 extraherade {item_count} artiklar",
        )

        begin_import_stage(
            workflow_run_id,
            "r_persist",
            message=f"Sparar AI3-resultat för {item_count} artiklar",
        )
        complete_import_stage(
            workflow_run_id,
            "r_persist",
            success=True,
            message="AI3-data sparat i unified_files",
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        _history(
            file_id,
            "ai3",
            "error",
            ai_stage_name="AI3-DataExtraction",
            log_text=f"Failed to extract structured data from document_type='{document_type}', expense_type='{expense_type}'",
            error_message=error_msg,
            processing_time_ms=elapsed,
            provider=ai3_provider,
            model_name=ai3_model,
        )
        complete_import_stage(
            workflow_run_id,
            "r_ai3",
            success=False,
            message=error_msg,
        )
        raise

    # AI4 - Accounting Classification
    accounting_inputs = _load_accounting_inputs(file_id)
    begin_import_stage(workflow_run_id, "r_ai4", message="AI4 normalisering startar")
    if accounting_inputs:
        gross, net, vat_amount, vendor_name = accounting_inputs
        receipt_items = _load_receipt_items(file_id)
        start_time = time.time()
        ai4_provider = ai_service.prompt_provider_names.get("accounting_classification", "unknown")
        ai4_model = ai_service.prompt_model_names.get("accounting_classification", "unknown")
        try:
            result = classify_accounting_internal(
                AccountingClassificationRequest(
                    file_id=file_id,
                    document_type=document_type or "other",
                    expense_type=expense_type or "personal",
                    gross_amount=Decimal(str(gross or 0)),
                    net_amount=Decimal(str(net or 0)),
                    vat_amount=Decimal(str(vat_amount or 0)),
                    vendor_name=vendor_name or "",
                    receipt_items=receipt_items,
                )
            )
            elapsed = int((time.time() - start_time) * 1000)
            steps.append("AI4")

            ai7_stats = run_box_enrichment(file_id)
            if ai7_stats.get("success"):
                if "AI7" not in steps:
                    steps.append("AI7")
            else:
                logger.warning(
                    "AI7 box enrichment failed for %s in pipeline: %s",
                    file_id,
                    ai7_stats.get("error", "unknown"),
                )

            proposal_count = len(result.proposals or [])

            # Add detailed proposal breakdown
            proposal_details = []
            for proposal in (result.proposals or [])[:5]:  # Show first 5 proposals
                proposal_details.append(
                    f"account={proposal.account_code}, "
                    f"debit={proposal.debit}, credit={proposal.credit}"
                )
            if len(result.proposals or []) > 5:
                proposal_details.append(f"... +{len(result.proposals) - 5} more")

            ai4_prompt = ai_service.prompts.get("accounting_classification", "")
            raw_response = ai_service.last_raw_response or ""
            log_parts = [
                f"Generated {proposal_count} accounting proposals",
                f"Vendor: {vendor_name or 'N/A'}",
                f"Amounts: gross={gross}, net={net}, vat={vat_amount}",
                f"--- PROMPT ---\n{ai4_prompt}",
                f"--- RAW RESPONSE ---\n{raw_response}",
            ]
            if result.based_on_bas2025:
                log_parts.append("Based on BAS 2025 chart of accounts")
            if proposal_details:
                log_parts.append(f"Proposals: [{'; '.join(proposal_details)}]")

            _history(
                file_id,
                "ai4",
                "success",
                ai_stage_name="AI4-AccountingClassification",
                log_text="; ".join(log_parts),
                confidence=result.confidence,
                processing_time_ms=elapsed,
                provider=ai4_provider,
                model_name=ai4_model,
            )
            complete_import_stage(
                workflow_run_id,
                "r_ai4",
                success=True,
                message=f"AI4 skapade {proposal_count} konteringsförslag",
            )
        except Exception as exc:
            elapsed = int((time.time() - start_time) * 1000)
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            _history(
                file_id,
                "ai4",
                "error",
                ai_stage_name="AI4-AccountingClassification",
                log_text=f"Failed to classify accounting for vendor='{vendor_name}', gross={gross}, net={net}, vat={vat_amount}",
                error_message=error_msg,
                processing_time_ms=elapsed,
                provider=ai4_provider,
                model_name=ai4_model,
            )
            complete_import_stage(
                workflow_run_id,
                "r_ai4",
                success=False,
                message=error_msg,
            )
            raise
    else:
        _history(
            file_id,
            "ai4",
            "skipped",
            ai_stage_name="AI4-AccountingClassification",
            log_text="Skipped: No accounting inputs available (missing gross_amount_sek, net_amount_sek, or company_id)",
        )
        complete_import_stage(
            workflow_run_id,
            "r_ai4",
            success=True,
            message="AI4 hoppades över – saknar konteringsunderlag",
        )

    begin_import_stage(workflow_run_id, "r_queue_match", message="Köar kvitto för AI5-matchning")
    complete_import_stage(
        workflow_run_id,
        "r_queue_match",
        success=True,
        message=f"Kvitto {file_id} markerat som redo för matchning",
    )

    return steps

def _infer_document_type(
    file_type: Optional[str],
    merchant: Optional[str],
    tags: List[str],
    text_blob: str,
    company_card: bool,
) -> str:
    if company_card:
        return "receipt"
    ft = (file_type or "").lower()
    if ft:
        if any(token in ft for token in ("receipt", "expense", "company_card")):
            return "receipt"
        if any(token in ft for token in ("invoice", "supplier", "statement")):
            return "invoice"
    tags_lower = {t.lower() for t in (tags or [])}
    if tags_lower & {"receipt", "expense", "meal", "travel"}:
        return "receipt"
    if tags_lower & {"invoice", "statement", "supplier"}:
        return "invoice"
    text = " ".join(filter(None, [merchant or "", text_blob])).lower()
    invoice_keywords = [
        "invoice", "due date", "pay by", "bankgiro", "plusgiro", "ocr", "statement"
    ]
    for kw in invoice_keywords:
        if kw in text:
            return "invoice"
    receipt_keywords = [
        "receipt", "thank you", "cashier", "order", "sale total", "subtotal", "vat"
    ]
    for kw in receipt_keywords:
        if kw in text:
            return "receipt"
    return "other"

def _rules_file() -> Path:
    return Path(os.getenv("RULES_FILE", "/data/storage/rules.json"))

def _load_rules() -> List[AccountingRule]:
    path = _rules_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    rules: List[AccountingRule] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        matcher = str(item.get("matcher") or "").strip()
        account = str(item.get("account") or "").strip()
        if not matcher or not account:
            continue
        rules.append(
            AccountingRule(
                id=item.get("id"),
                name=str(item.get("note") or matcher),
                condition_type="merchant_contains",
                condition_value=matcher,
                account_code=account,
                vat_account_code=None,
            )
        )
    return rules

@celery_app.task(name="wf1.run_ai_pipeline")
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

    try:
        steps = _run_ai_pipeline(file_id, workflow_run_id)
        elapsed = int((time.time() - start_time) * 1000)
        message = f"AI pipeline completed {len(steps)} stages in {elapsed}ms: {', '.join(steps)}"
        mark_stage(workflow_run_id, "ai_pipeline", "succeeded", message=message, end=True)
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        message = f"AI pipeline failed after {elapsed}ms: {error_msg}"
        mark_stage(workflow_run_id, "ai_pipeline", "failed", message=message, end=True)
        # Do not re-raise, let the workflow system handle the failed state.

    return workflow_run_id

@celery_app.task(name="wf1.finalize")
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
            message="WF1 slutförd",
        )
        complete_import_stage(
            workflow_run_id,
            "finalize_ok",
            success=True,
            message="Kvittoflödet avslutat utan fel",
        )
        log_import_event(
            workflow_run_id,
            "KLAR",
            message="WF1 slutförd",
        )
    else:
        log_finalize_failure(workflow_run_id, message or "WF1 misslyckades")

    return workflow_run_id

@celery_app.task(name="wf2.run_invoice_analysis")
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

@celery_app.task(name="wf2.finalize")
def wf2_finalize(workflow_run_id: int) -> int:
    """
    Workflow 2: Finalize Task.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF2_")
    mark_stage(workflow_run_id, "finalize", "running", start=True)

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

    mark_stage(
        workflow_run_id,
        "finalize",
        final_status,
        message=message,
        end=True,
        workflow_status_override=final_status,
    )

    return workflow_run_id

__all__ = [
    "wf1_run_ai_pipeline",
    "wf1_finalize",
    "wf2_run_invoice_analysis",
    "wf2_finalize",
]
