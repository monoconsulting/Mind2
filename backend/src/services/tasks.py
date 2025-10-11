from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


from services.queue_manager import get_celery
from observability.metrics import track_task
from services.ocr import run_ocr
from services.enrichment import enrich_receipt, provider_from_env
from services.validation import validate_receipt
from services.accounting import propose_accounting_entries
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)
from models.accounting import AccountingRule
from models.ai_processing import (
    AccountingClassificationRequest,
    DataExtractionRequest,
    DocumentClassificationRequest,
    ExpenseClassificationRequest,
    ReceiptItem,
)
from models.receipts import AccountingEntry, Receipt, ReceiptStatus
from api.ai_processing import (
    classify_accounting_internal,
    classify_document_internal,
    classify_expense_internal,
    extract_data_internal,
)


_INVOICE_PAGE_COMPLETE_STATUSES = {
    "ocr_done",
    InvoiceProcessingStatus.OCR_DONE.value,
    InvoiceProcessingStatus.READY_FOR_MATCHING.value,
    InvoiceProcessingStatus.MATCHING_COMPLETED.value,
    InvoiceProcessingStatus.COMPLETED.value,
}

celery_app = get_celery()


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
    """Log processing history with detailed information.

    Args:
        file_id: The file being processed
        job: Job type (e.g., 'ai1', 'ai2', 'ocr', 'classification')
        status: 'success' or 'error'
        ai_stage_name: Human-readable stage name (e.g., 'AI1-DocumentClassification')
        log_text: Detailed explanation of what happened
        error_message: Error details if status is 'error'
        confidence: Confidence score for this stage
        processing_time_ms: Time taken in milliseconds
        provider: AI provider used (e.g., 'rule-based', 'openai')
        model_name: Model name used
    """
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


def _update_file_status(file_id: str, status: str, confidence: float | None = None) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            if confidence is None:
                cur.execute(
                    "UPDATE unified_files SET ai_status=%s, updated_at=NOW() WHERE id=%s",
                    (status, file_id),
                )
            else:
                cur.execute(
                    "UPDATE unified_files SET ai_status=%s, ai_confidence=%s, updated_at=NOW() "
                    "WHERE id=%s",
                    (status, confidence, file_id),
                )
            return cur.rowcount > 0
    except Exception:
        return False


def _update_file_fields(
    file_id: str,
    ocr_raw: str | None = None,
) -> bool:
    """Update ONLY OCR raw text. All business data set by AI, not OCR."""
    if db_cursor is None:
        return False
    try:
        if ocr_raw is None:
            return False
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET ocr_raw=%s, updated_at=NOW() WHERE id=%s",
                (ocr_raw, file_id)
            )
            return cur.rowcount > 0
    except Exception:
        return False


def _load_unified_file_info(file_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id, file_type, original_file_id, other_data FROM unified_files WHERE id=%s",
                (file_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    raw_other = row[3]
    other_data: dict[str, Any]
    if raw_other:
        try:
            other_data = json.loads(raw_other)
        except Exception:
            other_data = {}
    else:
        other_data = {}
    return {
        "id": row[0],
        "file_type": row[1] or "",
        "original_file_id": row[2],
        "other_data": other_data,
    }


def _get_invoice_parent_id(file_id: str) -> Optional[str]:
    info = _load_unified_file_info(file_id)
    if not info:
        return None
    file_type = str(info.get("file_type") or "").lower()
    if file_type == "invoice_page":
        parent = info.get("original_file_id")
        return str(parent) if isinstance(parent, str) and parent else None
    if file_type == "invoice":
        identifier = info.get("id")
        return str(identifier) if isinstance(identifier, str) and identifier else None
    return None


def _load_invoice_metadata(invoice_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    payload = row[0]
    if not payload:
        return {}
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except Exception:
            payload = payload.decode("latin1", errors="ignore")
    try:
        return json.loads(payload)
    except Exception:
        return {}


def _update_invoice_metadata(invoice_id: str, metadata: dict[str, Any]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE invoice_documents SET metadata_json=%s WHERE id=%s",
                (json.dumps(metadata or {}), invoice_id),
            )
        return True
    except Exception:
        return False


def _set_invoice_metadata_field(invoice_id: str, field: str, value: Any) -> dict[str, Any] | None:
    metadata = _load_invoice_metadata(invoice_id)
    if metadata is None:
        return None
    metadata[field] = value
    if _update_invoice_metadata(invoice_id, metadata):
        return metadata
    return None


def _invoice_page_progress(invoice_id: str, metadata: dict[str, Any] | None = None) -> dict[str, int]:
    data = metadata if metadata is not None else (_load_invoice_metadata(invoice_id) or {})
    page_ids = data.get("page_ids")
    if not isinstance(page_ids, list):
        page_ids = []
    page_status = data.get("page_status")
    if not isinstance(page_status, dict):
        page_status = {}
    completed = 0
    for pid in page_ids:
        status = (page_status.get(pid) or "").lower()
        if status in _INVOICE_PAGE_COMPLETE_STATUSES:
            completed += 1
    if not page_ids and page_status:
        completed = sum(
            1
            for status in page_status.values()
            if (status or "").lower() in _INVOICE_PAGE_COMPLETE_STATUSES
        )
    total = data.get("page_count")
    if not isinstance(total, int) or total <= 0:
        fallback = len(page_ids) or len(page_status)
        total = fallback if fallback > 0 else 0
    pending = max(total - completed, 0)
    return {"total": total, "completed": completed, "pending": pending}


def _enqueue_invoice_document(invoice_id: str) -> bool:
    try:
        task = process_invoice_document  # type: ignore[name-defined]
    except NameError:
        return False
    try:
        if hasattr(task, "delay"):
            task.delay(invoice_id)  # type: ignore[attr-defined]
        else:
            task(invoice_id)  # type: ignore[misc]
        return True
    except Exception:
        return False


def _maybe_advance_invoice_from_file(file_id: str, success: bool) -> None:
    invoice_id = _get_invoice_parent_id(file_id)
    if not invoice_id:
        return

    metadata = _load_invoice_metadata(invoice_id) or {}
    page_ids = metadata.get("page_ids")
    if not isinstance(page_ids, list):
        page_ids = []
    if file_id not in page_ids:
        page_ids.append(file_id)
        metadata["page_ids"] = page_ids

    page_status = metadata.get("page_status")
    if not isinstance(page_status, dict):
        page_status = {}
    page_status[file_id] = "ocr_done" if success else "ocr_failed"
    metadata["page_status"] = page_status

    progress = _invoice_page_progress(invoice_id, metadata)
    metadata["ocr_completed_pages"] = progress["completed"]
    existing_count = metadata.get("page_count")
    if isinstance(existing_count, int) and existing_count > 0:
        metadata["page_count"] = max(existing_count, progress["total"])
    else:
        metadata["page_count"] = progress["total"]

    should_schedule = False
    if success and progress["total"] > 0 and progress["completed"] >= progress["total"]:
        metadata["processing_status"] = InvoiceProcessingStatus.OCR_DONE.value
        next_state = InvoiceProcessingStatus.OCR_DONE
        allowed_states = (
            InvoiceProcessingStatus.UPLOADED,
            InvoiceProcessingStatus.OCR_PENDING,
            InvoiceProcessingStatus.OCR_DONE,
        )
        should_schedule = not metadata.get("invoice_document_scheduled")
    elif success:
        metadata["processing_status"] = InvoiceProcessingStatus.OCR_PENDING.value
        next_state = InvoiceProcessingStatus.OCR_PENDING
        allowed_states = (
            InvoiceProcessingStatus.UPLOADED,
            InvoiceProcessingStatus.OCR_PENDING,
        )
    else:
        metadata["processing_status"] = InvoiceProcessingStatus.FAILED.value
        next_state = InvoiceProcessingStatus.FAILED
        allowed_states = (
            InvoiceProcessingStatus.UPLOADED,
            InvoiceProcessingStatus.OCR_PENDING,
            InvoiceProcessingStatus.OCR_DONE,
            InvoiceProcessingStatus.AI_PROCESSING,
        )

    _update_invoice_metadata(invoice_id, metadata)
    transition_processing_status(invoice_id, next_state, allowed_states)

    if should_schedule and _enqueue_invoice_document(invoice_id):
        _set_invoice_metadata_field(invoice_id, "invoice_document_scheduled", True)


def _load_receipt_model(file_id: str) -> Optional[Receipt]:
    """Load receipt model with company name from companies table, not merchant_name."""
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT uf.id, uf.submitted_by, uf.created_at, c.name AS company_name,
                       uf.orgnr, uf.purchase_datetime, uf.gross_amount, uf.net_amount,
                       uf.ai_confidence
                FROM unified_files uf
                LEFT JOIN companies c ON uf.company_id = c.id
                WHERE uf.id = %s
                """,
                (file_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        (
            rid,
            submitted_by,
            created_at,
            company_name,
            orgnr,
            purchase_dt,
            gross,
            net,
            ai_conf,
        ) = row

        tags: List[str] = []
        try:
            with db_cursor() as cur:
                cur.execute("SELECT tag FROM file_tags WHERE file_id=%s", (file_id,))
                tags = [tag for (tag,) in cur.fetchall() or []]
        except Exception:
            tags = []

        submitted_at = created_at or datetime.now(timezone.utc)
        if isinstance(submitted_at, datetime):
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
        else:
            submitted_at = datetime.now(timezone.utc)

        if isinstance(purchase_dt, datetime):
            purchase_at: Optional[datetime] = (
                purchase_dt if purchase_dt.tzinfo is not None else purchase_dt.replace(tzinfo=timezone.utc)
            )
        elif isinstance(purchase_dt, str):
            try:
                parsed = datetime.fromisoformat(purchase_dt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                purchase_at = parsed
            except Exception:
                purchase_at = None
        else:
            purchase_at = None

        gross_dec = Decimal(str(gross)) if gross is not None else None
        net_dec = Decimal(str(net)) if net is not None else None
        confidence = float(ai_conf) if ai_conf is not None else None

        return Receipt(
            id=rid,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            merchant_name=company_name,  # From companies table via JOIN
            orgnr=orgnr,
            purchase_datetime=purchase_at,
            gross_amount=gross_dec,
            net_amount=net_dec,
            vat_breakdown={},
            tags=tags,
            location_opt_in=False,
            company_card_flag=False,
            status=ReceiptStatus.PROCESSING,
            confidence_summary=confidence,
        )
    except Exception:
        return None




def _get_file_type(file_id: str) -> Optional[str]:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute("SELECT file_type FROM unified_files WHERE id=%s", (file_id,))
            row = cur.fetchone()
            if row:
                (file_type,) = row
                return file_type
    except Exception:
        return None
    return None


def _collect_text_hints(file_id: str) -> str:
    base = Path(os.getenv("STORAGE_DIR", "/data/storage"))
    hints: List[str] = []
    line_items_path = base / "line_items" / f"{file_id}.json"
    if line_items_path.exists():
        try:
            data = json.loads(line_items_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if data is not None:
            def _consume(value: Any) -> None:
                if isinstance(value, str) and value.strip():
                    hints.append(value.strip().lower())
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for v in item.values():
                            _consume(v)
                    else:
                        _consume(item)
            elif isinstance(data, dict):
                for v in data.values():
                    _consume(v)
            else:
                _consume(data)
    return " ".join(hints)


def _load_ai_context(file_id: str):
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT ocr_raw, file_type, expense_type FROM unified_files WHERE id=%s",
                (file_id,),
            )
            return cur.fetchone()
    except Exception:
        return None


def _load_accounting_inputs(file_id: str):
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT gross_amount_sek, net_amount_sek,
                       (gross_amount_sek - net_amount_sek) AS vat_amount,
                       c.name AS vendor_name
                  FROM unified_files uf
             LEFT JOIN companies c ON uf.company_id = c.id
                 WHERE uf.id = %s
                """,
                (file_id,),
            )
            return cur.fetchone()
    except Exception:
        return None


def _load_receipt_items(file_id: str):
    """Load receipt items with their IDs from the database."""
    if db_cursor is None:
        return []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, main_id, article_id, name, number,
                       item_price_ex_vat, item_price_inc_vat,
                       item_total_price_ex_vat, item_total_price_inc_vat,
                       currency, vat, vat_percentage
                FROM receipt_items
                WHERE main_id = %s
                """,
                (file_id,),
            )
            rows = cur.fetchall()
            items = []
            for row in rows:
                items.append(ReceiptItem(
                    id=row[0],
                    main_id=row[1],
                    article_id=row[2] or "",
                    name=row[3],
                    number=row[4],
                    item_price_ex_vat=Decimal(str(row[5] or 0)),
                    item_price_inc_vat=Decimal(str(row[6] or 0)),
                    item_total_price_ex_vat=Decimal(str(row[7] or 0)),
                    item_total_price_inc_vat=Decimal(str(row[8] or 0)),
                    currency=row[9] or "SEK",
                    vat=Decimal(str(row[10] or 0)),
                    vat_percentage=Decimal(str(row[11] or 0)),
                ))
            return items
    except Exception:
        return []


def _run_ai_pipeline(file_id: str) -> List[str]:
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
    try:
        result = classify_document_internal(
            DocumentClassificationRequest(file_id=file_id, ocr_text=ocr_text or "")
        )
        elapsed = int((time.time() - start_time) * 1000)
        steps.append("AI1")

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
        raise

    # AI4 - Accounting Classification
    accounting_inputs = _load_accounting_inputs(file_id)
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

            log_parts = [
                f"Generated {proposal_count} accounting proposals",
                f"Vendor: {vendor_name or 'N/A'}",
                f"Amounts: gross={gross}, net={net}, vat={vat_amount}",
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
            raise
    else:
        _history(
            file_id,
            "ai4",
            "skipped",
            ai_stage_name="AI4-AccountingClassification",
            log_text="Skipped: No accounting inputs available (missing gross_amount_sek, net_amount_sek, or company_id)",
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


def _save_accounting_entries(file_id: str, entries: List[AccountingEntry]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (file_id,))
            for entry in entries:
                cur.execute(
                    (
                        "INSERT INTO ai_accounting_proposals "
                        "(receipt_id, item_id, account_code, debit, credit, vat_rate, notes) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        file_id,
                        entry.item_id if hasattr(entry, 'item_id') and entry.item_id else None,
                        entry.account_code,
                        float(entry.debit or 0),
                        float(entry.credit or 0),
                        (float(entry.vat_rate) if entry.vat_rate is not None else None),
                        (entry.notes[:255] if entry.notes else None),
                    ),
                )
        return True
    except Exception:
        return False


@celery_app.task
@track_task("process_ocr")
def process_ocr(file_id: str) -> dict[str, Any]:
    import time

    start_time = time.time()

    # Run real OCR
    result: dict[str, Any] | None = None
    error_msg: str | None = None

    try:
        result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
    except Exception as exc:
        result = None
        error_msg = f"{type(exc).__name__}: {str(exc)}"

    if result:
        # OCR ONLY writes raw text - NO business data extraction
        _update_file_fields(
            file_id,
            ocr_raw=result.get("text"),
        )
        ok = _update_file_status(file_id, status="ocr_done", confidence=None)

        elapsed = int((time.time() - start_time) * 1000)
        text_len = len(result.get("text", ""))
        text_preview = result.get("text", "")[:100].replace('\n', ' ') if result.get("text") else ""

        # Build detailed log message
        log_parts = [f"OCR completed successfully: extracted {text_len} characters of raw text"]
        if text_preview:
            log_parts.append(f"preview: '{text_preview}{'...' if text_len > 100 else ''}'")

        # Add detected patterns if available
        detected = []
        if result.get("merchant_name"):
            detected.append(f"merchant='{result.get('merchant_name')}'")
        if result.get("gross_amount") is not None:
            detected.append(f"amount={result.get('gross_amount')}")
        if result.get("purchase_datetime"):
            detected.append(f"date={result.get('purchase_datetime')}")
        if detected:
            log_parts.append(f"detected: {', '.join(detected)}")

        _history(
            file_id,
            job="ocr",
            status="success",
            ai_stage_name="OCR-TextExtraction",
            log_text="; ".join(log_parts),
            confidence=None,
            processing_time_ms=elapsed,
            provider="paddleocr",
        )

        _maybe_advance_invoice_from_file(file_id, success=True)

        # Only continue to AI pipeline if OCR succeeded
        try:
            process_ai_pipeline.delay(file_id)  # type: ignore[attr-defined]
        except Exception:
            try:
                process_ai_pipeline.run(file_id)
            except Exception:
                pass

        return {"file_id": file_id, "status": "ocr_done", "ok": ok, "real": True}
    else:
        # OCR failed
        ok = _update_file_status(file_id, status="manual_review", confidence=0.0)
        elapsed = int((time.time() - start_time) * 1000)

        _history(
            file_id,
            job="ocr",
            status="error",
            ai_stage_name="OCR-TextExtraction",
            log_text="OCR processing failed or returned no results",
            error_message=error_msg or "OCR returned no results",
            confidence=0.0,
            processing_time_ms=elapsed,
            provider="paddleocr",
        )

        _maybe_advance_invoice_from_file(file_id, success=False)

        return {"file_id": file_id, "status": "manual_review", "ok": False, "error": error_msg or "OCR failed"}


@celery_app.task
@track_task("process_ai_pipeline")
def process_ai_pipeline(file_id: str) -> dict[str, Any]:
    import time

    start_time = time.time()
    try:
        steps = _run_ai_pipeline(file_id)
        elapsed = int((time.time() - start_time) * 1000)

        _history(
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
        error_msg = f"{type(exc).__name__}: {str(exc)}"

        _history(
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


@celery_app.task
@track_task("process_audio_transcription")
def process_audio_transcription(file_id: str) -> dict[str, Any]:
    import time

    start_time = time.time()
    try:
        ok = _update_file_status(file_id, status="transcription_queued")
        elapsed = int((time.time() - start_time) * 1000)
        _history(
            file_id,
            job="transcription",
            status="success",
            ai_stage_name="Audio-Queued",
            log_text="Audio file queued for transcription pipeline",
            processing_time_ms=elapsed,
            provider="audio_pipeline",
        )
        return {"file_id": file_id, "status": "transcription_queued", "ok": ok}
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        _history(
            file_id,
            job="transcription",
            status="error",
            ai_stage_name="Audio-Queued",
            log_text="Failed to queue audio for transcription",
            error_message=str(exc),
            processing_time_ms=elapsed,
            provider="audio_pipeline",
        )
        return {"file_id": file_id, "status": "error", "ok": False, "error": str(exc)}


@celery_app.task
@track_task("process_classification")
def process_classification(file_id: str) -> dict[str, Any]:
    """Legacy task - most processing now done via AI pipeline."""
    file_type = _get_file_type(file_id)
    receipt_model = _load_receipt_model(file_id)
    company_name = receipt_model.merchant_name if receipt_model else None  # From companies table
    tags = receipt_model.tags if receipt_model else []
    gross_decimal = receipt_model.gross_amount if receipt_model else None

    merchants_cfg = os.getenv("COMPANY_CARD_MERCHANTS", "")
    cc_merchants = {m.strip().lower() for m in merchants_cfg.split(",") if m.strip()}
    company_card = (company_name or "").lower() in cc_merchants if company_name else False

    enriched_name = None
    try:
        orgnr_val = None
        if db_cursor is not None:
            with db_cursor() as cur:
                cur.execute("SELECT orgnr FROM unified_files WHERE id=%s", (file_id,))
                row = cur.fetchone()
                if row:
                    (orgnr_val,) = row
        if orgnr_val:
            company = enrich_receipt(
                Receipt(
                    id=file_id,
                    submitted_by=None,
                    submitted_at=datetime.now(timezone.utc),
                    pages=[],
                    tags=[],
                    location_opt_in=False,
                    merchant_name=company_name,
                    orgnr=str(orgnr_val),
                    purchase_datetime=None,
                    gross_amount=gross_decimal,
                    net_amount=None,
                    vat_breakdown={},
                    company_card_flag=company_card,
                    status=ReceiptStatus.PROCESSING,
                    confidence_summary=None,
                ),
                provider_from_env(),
            )
            if company:
                enriched_name = company.legal_name
    except Exception:
        pass

    # NOTE: enriched_name not saved - companies table is source of truth

    text_hints = _collect_text_hints(file_id)
    document_type = _infer_document_type(file_type, company_name, tags, text_hints, company_card)

    status_map = {
        "receipt": "classified_receipt",
        "invoice": "classified_invoice",
        "other": "classified_other",
    }
    status_value = status_map.get(document_type, "classified_other")

    ok = _update_file_status(file_id, status=status_value)
    _history(file_id, job="classification", status="success" if ok else "error")

    validation_triggered = False
    if document_type == "receipt":
        try:
            process_validation.delay(file_id)  # type: ignore[attr-defined]
            validation_triggered = True
        except Exception:
            try:
                process_validation.run(file_id)
                validation_triggered = True
            except Exception:
                validation_triggered = False

    return {
        "file_id": file_id,
        "status": status_value,
        "document_type": document_type,
        "ok": ok,
        "company_card": company_card,
        "validation_triggered": validation_triggered,
    }


@celery_app.task
@track_task("process_validation")
def process_validation(file_id: str) -> dict[str, Any]:
    receipt = _load_receipt_model(file_id)
    if receipt is None:
        _history(file_id, job="validation", status="error")
        return {"file_id": file_id, "status": "error", "ok": False}

    report = validate_receipt(receipt)
    status_map = {
        ReceiptStatus.PASSED: "passed",
        ReceiptStatus.MANUAL_REVIEW: "manual_review",
        ReceiptStatus.FAILED: "failed",
    }
    new_status = status_map.get(report.status, "manual_review")
    ok = _update_file_status(file_id, status=new_status)
    _history(file_id, job="validation", status="success" if ok else "error")

    if report.status == ReceiptStatus.PASSED:
        try:
            process_accounting_proposal.delay(file_id)  # type: ignore[attr-defined]
        except Exception:
            try:
                process_accounting_proposal.run(file_id)
            except Exception:
                pass

    messages = [
        {"message": msg.message, "severity": getattr(msg.severity, "value", str(msg.severity)), "field": msg.field_ref}
        for msg in report.messages
    ]
    return {"file_id": file_id, "status": new_status, "ok": ok, "messages": messages}


@celery_app.task
@track_task("process_accounting_proposal")
def process_accounting_proposal(file_id: str) -> dict[str, Any]:
    receipt = _load_receipt_model(file_id)
    if receipt is None:
        _history(file_id, job="accounting_proposal", status="error")
        return {"file_id": file_id, "status": "error", "ok": False}

    rules = _load_rules()
    entries = propose_accounting_entries(receipt, rules)
    saved = _save_accounting_entries(file_id, entries)
    if saved and entries:
        _update_file_status(file_id, status="accounting_proposed")
    _history(file_id, job="accounting_proposal", status="success" if saved else "error")
    return {
        "file_id": file_id,
        "entries": len(entries),
        "ok": saved,
    }


@celery_app.task
@track_task("process_invoice_document")
def process_invoice_document(document_id: str) -> dict[str, Any]:
    transitioned = transition_processing_status(
        document_id,
        InvoiceProcessingStatus.AI_PROCESSING,
        (
            InvoiceProcessingStatus.OCR_DONE,
            InvoiceProcessingStatus.OCR_PENDING,
            InvoiceProcessingStatus.UPLOADED,
        ),
    )
    if not transitioned:
        _history(document_id, job="invoice_document", status="error", log_text="invalid_processing_state")
        return {
            "document_id": document_id,
            "status": "invalid_state",
            "ok": False,
        }

    # Placeholder for AI extraction work. Once implemented this block will call
    # the dedicated invoice extraction service and populate invoice_lines.
    _history(document_id, job="invoice_document", status="success", log_text="ai_processing_started")

    ready = transition_processing_status(
        document_id,
        InvoiceProcessingStatus.READY_FOR_MATCHING,
        (InvoiceProcessingStatus.AI_PROCESSING,),
    )
    if ready:
        transition_document_status(
            document_id,
            InvoiceDocumentStatus.MATCHING,
            (InvoiceDocumentStatus.IMPORTED,),
        )
    return {
        "document_id": document_id,
        "status": InvoiceProcessingStatus.READY_FOR_MATCHING.value,
        "ok": ready,
    }


@celery_app.task
@track_task("process_matching")
def process_matching(statement_id: str) -> dict[str, Any]:
    matched = 0
    total_lines = 0
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT COUNT(*), SUM(CASE WHEN match_status IN ('auto','manual','confirmed') "
                        "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%s"
                    ),
                    (statement_id,),
                )
                row = cur.fetchone()
                if row:
                    total_lines = int(row[0] or 0)
                    matched = int(row[1] or 0)
        except Exception:
            total_lines = 0
            matched = 0

    processing_ok = transition_processing_status(
        statement_id,
        InvoiceProcessingStatus.MATCHING_COMPLETED,
        (
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            InvoiceProcessingStatus.AI_PROCESSING,
        ),
    )

    if matched == 0:
        transition_document_status(
            statement_id,
            InvoiceDocumentStatus.IMPORTED,
            (
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
            ),
        )
    elif total_lines and matched < total_lines:
        transition_document_status(
            statement_id,
            InvoiceDocumentStatus.PARTIALLY_MATCHED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.MATCHED,
            ),
        )
    else:
        transition_document_status(
            statement_id,
            InvoiceDocumentStatus.MATCHED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
            ),
        )

    return {
        "statement_id": statement_id,
        "matched": matched,
        "total": total_lines,
        "processing_ok": processing_ok,
    }


@celery_app.task
def hello(name):
    print(f"Hello, {name}!")
    return f"Hello, {name}!"

