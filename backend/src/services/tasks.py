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
from models.accounting import AccountingRule
from models.receipts import AccountingEntry, Receipt, ReceiptStatus

celery_app = get_celery()


INSERT_HISTORY_SQL = (
    "INSERT INTO ai_processing_history (file_id, job_type, status) VALUES (%s, %s, %s)"
)


def _history(file_id: str, job: str, status: str) -> None:
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(INSERT_HISTORY_SQL, (file_id, job, status))
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
    merchant: str | None = None,
    gross: float | None = None,
    purchase_iso: str | None = None,
    ocr_raw: str | None = None,
) -> bool:
    if db_cursor is None:
        return False
    try:
        sets: List[str] = []
        vals: List[Any] = []
        if merchant is not None:
            sets.append("merchant_name=%s")
            vals.append(merchant)
        if gross is not None:
            sets.append("gross_amount=%s")
            vals.append(gross)
        if purchase_iso is not None:
            sets.append("purchase_datetime=%s")
            vals.append(purchase_iso)
        if ocr_raw is not None:
            sets.append("ocr_raw=%s")
            vals.append(ocr_raw)
        if not sets:
            return False
        sets.append("updated_at=NOW()")
        vals.append(file_id)
        with db_cursor() as cur:
            cur.execute("UPDATE unified_files SET " + ", ".join(sets) + " WHERE id=%s", tuple(vals))
            return cur.rowcount > 0
    except Exception:
        return False


def _load_receipt_model(file_id: str) -> Optional[Receipt]:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, submitted_by, created_at, merchant_name, orgnr, purchase_datetime, "
                    "gross_amount, net_amount, ai_confidence FROM unified_files WHERE id=%s"
                ),
                (file_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        (
            rid,
            submitted_by,
            created_at,
            merchant_name,
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
            merchant_name=merchant_name,
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
                        "(receipt_id, account_code, debit, credit, vat_rate, notes) "
                        "VALUES (%s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        file_id,
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
    enable_real = (os.getenv("ENABLE_REAL_OCR", "false").lower() in {"1", "true", "yes"})
    result: dict[str, Any] | None = None
    if enable_real:
        try:
            result = run_ocr(file_id, os.getenv("STORAGE_DIR", "/data/storage"))
        except Exception:
            result = None
    if result:
        _update_file_fields(
            file_id,
            merchant=result.get("merchant_name"),
            gross=float(result["gross_amount"]) if result.get("gross_amount") is not None else None,
            purchase_iso=result.get("purchase_datetime"),
            ocr_raw=result.get("text"),  # Save the raw OCR text
        )
        ok = _update_file_status(file_id, status="ocr_done", confidence=float(result.get("confidence") or 0.9))
    else:
        ok = _update_file_status(file_id, status="ocr_done", confidence=0.5)
    _history(file_id, job="ocr", status="success" if ok else "error")
    try:
        process_classification.delay(file_id)  # type: ignore[attr-defined]
    except Exception:
        try:
            process_classification.run(file_id)
        except Exception:
            pass
    return {"file_id": file_id, "status": "ocr_done", "ok": ok, "real": bool(result)}


@celery_app.task
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

    text_hints = _collect_text_hints(file_id)
    document_type = _infer_document_type(file_type, merchant, tags, text_hints, company_card)

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
    ok = _update_file_status(document_id, status="document_processed")
    _history(document_id, job="invoice_document", status="success" if ok else "error")
    return {"document_id": document_id, "status": "document_processed", "ok": ok}


@celery_app.task
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


@celery_app.task
def hello(name):
    print(f"Hello, {name}!")
    return f"Hello, {name}!"

