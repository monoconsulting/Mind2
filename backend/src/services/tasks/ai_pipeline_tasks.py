from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from .common import (
    AccountingClassificationRequest,
    AccountingEntry,
    AiStatus,
    AccountingRule,
    DataExtractionRequest,
    DocumentClassificationRequest,
    ExpenseClassificationRequest,
    Receipt,
    ReceiptItem,
    ReceiptStatus,
    db_cursor,
    enrich_receipt,
    provider_from_env,
    propose_accounting_entries,
    run_box_enrichment,
    track_task,
    validate_receipt,
)
from .common import (
    classify_accounting_internal,
    classify_document_internal,
    classify_expense_internal,
    extract_data_internal,
)
from .file_management_tasks import (
    _collect_text_hints,
    _enforce_file_metadata,
    _load_accounting_inputs,
    _load_ai_context,
    _load_receipt_items,
    _load_receipt_model,
    _maybe_advance_invoice_from_file,
    _move_to_manual_review,
    _save_accounting_entries,
    _update_file_status,
)
from .history import _history
from .utils.invoice_utils import _load_unified_file_info
from .workflow_base import begin_import_stage, complete_import_stage, log_import_event

logger = logging.getLogger(__name__)


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
    ai1_prompt = ai_service.prompts.get("document_analysis", "")
    raw_response = ""
    begin_import_stage(workflow_run_id, "detect_type", message=f"AI1 klassificering för fil {file_id}")
    try:
        result = classify_document_internal(
            DocumentClassificationRequest(file_id=file_id, ocr_text=ocr_text or "")
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI1")

        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Classified document as '{result.document_type}'",
            f"OCR text length: {len(ocr_text or '')} characters",
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
            prompt_text=ai1_prompt,
            response_text=raw_response,
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
            log_import_event(workflow_run_id, AiStatus.MANUAL_REVIEW.value, message=reason)
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
        raw_response = ai_service.last_raw_response or ""
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
            prompt_text=ai1_prompt,
            response_text=raw_response,
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
    ai2_prompt = ai_service.prompts.get("expense_classification", "")
    raw_response = ""
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

        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Classified expense as '{result.expense_type}'",
            f"Document type: {document_type or 'other'}",
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
            prompt_text=ai2_prompt,
            response_text=raw_response,
        )
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {str(exc)}"
        raw_response = ai_service.last_raw_response or ""
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
            prompt_text=ai2_prompt,
            response_text=raw_response,
        )
        raise

    # Reload context after AI2
    context = _load_ai_context(file_id) or context
    ocr_text, document_type, expense_type = context

# AI3 - Data Extraction
    start_time = time.time()
    ai3_provider = ai_service.prompt_provider_names.get("data_extraction", "unknown")
    ai3_model = ai_service.prompt_model_names.get("data_extraction", "unknown")
    ai3_prompt = ai_service.prompts.get("data_extraction", "")
    raw_response = ""
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
        item_samples = []
        if result.receipt_items and len(result.receipt_items) > 0:
            for item in result.receipt_items[:3]:
                item_samples.append(f"{item.name}@{item.item_total_price_inc_vat}")

        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Extracted data: {', '.join(extracted) if extracted else 'NO DATA'}",
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
            if item_samples:
                log_parts.append(
                    f"Sample items (first {len(item_samples)}): [{', '.join(item_samples)}]"
                )

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
            prompt_text=ai3_prompt,
            response_text=raw_response,
        )
        complete_import_stage(
            workflow_run_id,
            "r_ai3",
            success=True,
            message=f"AI3 extraherade {item_count} artiklar",
        )

        company_stage_msg = f"company_match_type={result.company_match_type or 'unknown'} created={result.company_create_needed}"
        log_import_event(
            workflow_run_id,
            "company_resolved",
            status="succeeded",
            message=company_stage_msg,
        )

        begin_import_stage(
            workflow_run_id,
            "r_persist",
            message=f"Sparar AI3-resultat f├╢r {item_count} artiklar",
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
        raw_response = ai_service.last_raw_response or ""
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
            prompt_text=ai3_prompt,
            response_text=raw_response,
        )
        complete_import_stage(
            workflow_run_id,
            "r_ai3",
            success=False,
            message=error_msg,
        )
        _move_to_manual_review(file_id, error_msg)
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
        ai4_prompt = ai_service.prompts.get("accounting_classification", "")
        raw_response = ""
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
            proposal_samples = []
            for proposal in (result.proposals or [])[:5]:
                proposal_samples.append(
                    f"account={proposal.account_code}, "
                    f"debit={proposal.debit}, credit={proposal.credit}"
                )

            raw_response = ai_service.last_raw_response or ""
            log_parts = [
                f"Generated {proposal_count} accounting proposals",
                f"Vendor: {vendor_name or 'N/A'}",
                f"Amounts: gross={gross}, net={net}, vat={vat_amount}",
            ]
            if result.based_on_bas2025:
                log_parts.append("Based on BAS 2025 chart of accounts")
            if proposal_count > 0:
                log_parts.append(f"Proposals: {proposal_count} total")
                if proposal_samples:
                    log_parts.append(
                        f"Sample proposals (first {len(proposal_samples)}): [{'; '.join(proposal_samples)}]"
                    )

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
                prompt_text=ai4_prompt,
                response_text=raw_response,
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
            raw_response = ai_service.last_raw_response or ""
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
                prompt_text=ai4_prompt,
                response_text=raw_response,
            )
            complete_import_stage(
                workflow_run_id,
                "r_ai4",
                success=False,
                message=error_msg,
            )
            _move_to_manual_review(file_id, error_msg)
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
            message="AI4 hoppades ├╢ver ΓÇô saknar konteringsunderlag",
        )

    begin_import_stage(workflow_run_id, "r_queue_match", message="K├╢ar kvitto f├╢r AI5-matchning")
    complete_import_stage(
        workflow_run_id,
        "r_queue_match",
        success=True,
        message=f"Kvitto {file_id} markerat som redo f├╢r matchning",
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

__all__ = [
    "UnsupportedDocumentTypeError",
    "_run_ai_pipeline",
    "_infer_document_type",
    "_rules_file",
    "_load_rules",
]
