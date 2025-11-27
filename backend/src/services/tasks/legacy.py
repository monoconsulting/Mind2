from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, List

from .common import (
    AccountingEntry,
    AiStatus,
    Receipt,
    ReceiptStatus,
    celery_app,
    db_cursor,
    enrich_receipt,
    propose_accounting_entries,
    provider_from_env,
    run_ocr,
    track_task,
    validate_receipt,
)
from .ai_pipeline_tasks import _infer_document_type, _load_rules, _run_ai_pipeline
from .file_management_tasks import (
    _collect_text_hints,
    _get_file_type,
    _load_receipt_model,
    _fail_invoice_processing,
    _save_accounting_entries,
    _update_file_fields,
    _update_file_status,
)
from .history import _history
from .utils.invoice_utils import (
    _collect_invoice_ocr_text,
    _get_invoice_parent_id,
    _invoice_page_progress,
    _load_invoice_metadata,
)

logger = logging.getLogger(__name__)

__all__ = [
    "process_ocr",
    "process_classification",
    "process_validation",
    "process_accounting_proposal",
    "process_ai_pipeline",
    "process_invoice_ai_extraction",
    "_enqueue_invoice_ai_extraction",
    "process_matching",
    "hello",
]


def _tasks_attr(name: str, fallback):
    module = sys.modules.get("services.tasks")
    if module and hasattr(module, name):
        return getattr(module, name)
    return fallback


@celery_app.task(name="process_ocr")
@track_task("process_ocr")
def process_ocr(file_id: str) -> dict[str, Any]:
    """Run OCR for receipts/invoices and trigger the next stage."""

    file_type = (_get_file_type(file_id) or "").lower()
    invoice_parent_id = _get_invoice_parent_id(file_id, file_type)
    enable_real = os.getenv("ENABLE_REAL_OCR", "false").lower() in {"1", "true", "yes"}
    result: dict[str, Any] | None = None

    ocr_error: str | None = None

    if enable_real:
        try:
            result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
        except Exception as exc:  # pragma: no cover - OCR provider issues
            logger.warning("OCR failed for %s: %s", file_id, exc)
            result = None
            ocr_error = f"{exc.__class__.__name__}: {exc}"

    if result:
        _update_file_fields(
            file_id,
            merchant=result.get("merchant_name"),
            gross=float(result["gross_amount"]) if result.get("gross_amount") is not None else None,
            purchase_iso=result.get("purchase_datetime"),
            ocr_raw=result.get("text"),
        )
        ok = _update_file_status(file_id, status=AiStatus.OCR_DONE.value, confidence=float(result.get("confidence") or 0.9))
    else:
        if file_type in {"invoice", "invoice_page"}:
            target_invoice = invoice_parent_id or file_id
            _fail_invoice_processing(target_invoice, ocr_error)
            _history(file_id, job="ocr", status="error")
            return {
                "file_id": file_id,
                "invoice_id": target_invoice,
                "status": "ocr_error",
                "ok": False,
            }
        ok = _update_file_status(file_id, status=AiStatus.OCR_DONE.value, confidence=0.5)

    _history(file_id, job="ocr", status="success" if ok else "error")

    if file_type in {"invoice_page", "invoice"}:
        invoice_id = invoice_parent_id or file_id
        metadata = _load_invoice_metadata(invoice_id)
        progress_func = _tasks_attr("_invoice_page_progress", _invoice_page_progress)
        try:
            progress = progress_func(invoice_id, metadata=metadata)
        except TypeError:
            progress = progress_func(invoice_id)
        if isinstance(progress, tuple):
            completed, total = progress
            progress = {
                "completed": completed,
                "total": total,
                "pending": max((total or 0) - (completed or 0), 0),
            }
        if progress.get("total") and progress.get("completed") >= progress.get("total"):
            _enqueue_invoice_ai_extraction(invoice_id)
        else:
            logger.debug(
                "Invoice %s OCR progress: %s/%s",
                invoice_id,
                progress.get("completed"),
                progress.get("total"),
            )
        return {
            "file_id": file_id,
            "invoice_id": invoice_id,
            "pages_completed": progress.get("completed", 0),
            "pages_total": progress.get("total", 0),
            "ok": ok,
        }

    if file_type == "invoice" and invoice_parent_id is None:
        _enqueue_invoice_ai_extraction(file_id)

    # Receipt (or unknown) => continue via AI pipeline
    pipeline_task = _tasks_attr("process_ai_pipeline", process_ai_pipeline)
    try:
        if hasattr(pipeline_task, "delay"):
            pipeline_task.delay(file_id)  # type: ignore[attr-defined]
        else:
            pipeline_task(file_id)
    except Exception:
        try:
            pipeline_task.run(file_id)
        except Exception:
            logger.debug("process_ai_pipeline fallback failed for %s", file_id)

    return {"file_id": file_id, "status": AiStatus.OCR_DONE.value, "ok": ok, "real": bool(result)}


@celery_app.task(name="process_classification")
@track_task("process_classification")
def process_classification(file_id: str) -> dict[str, Any]:
    file_type = _get_file_type(file_id)
    receipt_model = _load_receipt_model(file_id)
    merchant = receipt_model.merchant_name if receipt_model else None
    tags = receipt_model.tags if receipt_model else []
    gross_decimal = receipt_model.gross_amount if receipt_model else None

    merchants_cfg = os.getenv("COMPANY_CARD_MERCHANTS", "")
    cc_merchants = {m.strip().lower() for m in merchants_cfg.split(",") if m.strip()}
    company_card = (merchant or "").lower() in cc_merchants if merchant else False

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
                    merchant_name=merchant,
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

    if enriched_name:
        try:
            _update_file_fields(file_id, merchant=enriched_name)
            merchant = enriched_name
        except Exception:
            pass

    document_type = _infer_document_type(file_type, merchant, tags, _collect_text_hints(file_id), company_card)
    status_map = {
        "receipt": "classified_receipt",
        "invoice": "classified_invoice",
        "other": "classified_other",
        "fc_invoice": "classified_invoice",
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


@celery_app.task(name="process_validation")
@track_task("process_validation")
def process_validation(file_id: str) -> dict[str, Any]:
    receipt = _load_receipt_model(file_id)
    if receipt is None:
        _history(file_id, job="validation", status="error")
        return {"file_id": file_id, "status": "error", "ok": False}

    report = validate_receipt(receipt)
    status_map = {
        ReceiptStatus.PASSED: "passed",
        ReceiptStatus.MANUAL_REVIEW: AiStatus.MANUAL_REVIEW.value,
        ReceiptStatus.FAILED: AiStatus.FAILED.value,
    }
    new_status = status_map.get(report.status, AiStatus.MANUAL_REVIEW.value)
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
        {
            "message": msg.message,
            "severity": getattr(msg.severity, "value", str(msg.severity)),
            "field": msg.field_ref,
        }
        for msg in report.messages
    ]
    return {"file_id": file_id, "status": new_status, "ok": ok, "messages": messages}


@celery_app.task(name="process_accounting_proposal")
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

    return {"file_id": file_id, "entries": len(entries), "ok": saved}


@celery_app.task(name="process_ai_pipeline")
@track_task("process_ai_pipeline")
def process_ai_pipeline(file_id: str) -> dict[str, Any]:
    steps = _run_ai_pipeline(file_id)
    return {"file_id": file_id, "steps": steps, "ok": True}


@celery_app.task(name="process_invoice_ai_extraction")
@track_task("process_invoice_ai_extraction")
def process_invoice_ai_extraction(invoice_id: str) -> dict[str, Any]:
    texts = _collect_invoice_ocr_text(invoice_id)
    combined = "\n\n--- PAGE BREAK ---\n\n".join([text for _, text in texts if text])
    if not combined.strip():
        _history(invoice_id, "invoice_ai", "error", error_message="No OCR text available")
        return {"invoice_id": invoice_id, "status": "no_ocr_text", "ok": False}

    _history(invoice_id, "invoice_ai", "success", log_text=f"Collected {len(texts)} OCR segments")
    return {"invoice_id": invoice_id, "status": "extracted", "ok": True}


def _enqueue_invoice_ai_extraction(invoice_id: str) -> None:
    task = _tasks_attr("process_invoice_ai_extraction", process_invoice_ai_extraction)
    try:
        if hasattr(task, "delay"):
            task.delay(invoice_id)  # type: ignore[attr-defined]
        else:
            task(invoice_id)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to enqueue invoice AI extraction for %s: %s", invoice_id, exc)


@celery_app.task(name="process_matching")
@track_task("process_matching")
def process_matching(statement_id: str) -> dict[str, Any]:
    matched = 0
    file_id = None
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT file_id FROM ai_processing_queue WHERE id=%s", (statement_id,))
                row = cur.fetchone()
                if row:
                    (file_id,) = row
                    _history(file_id, job="firstcard_match", status="success")
        except Exception:
            pass
    return {"statement_id": statement_id, "file_id": file_id, "matched": matched}


@celery_app.task(name="hello")
def hello(name):  # pragma: no cover - utility task
    print(f"Hello, {name}!")
    return f"Hello, {name}!"
