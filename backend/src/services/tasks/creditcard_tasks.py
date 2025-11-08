from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from observability.events import log_event
from observability.metrics import record_invoice_decision
from services.ai_service import AIService
from services.box_enrichment import run_box_enrichment
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_line_status,
    transition_line_status_and_link,
    transition_processing_status,
)

from api.ai_processing import _persist_credit_card_match
from models.ai_processing import (
    CreditCardInvoiceExtractionRequest,
    CreditCardInvoiceExtractionResponse,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
)

from . import celery_app
from .common import db_cursor
from .history import _history, _update_file_status
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
    _load_invoice_metadata,
    _set_invoice_metadata_field,
    _update_invoice_metadata,
)
from .workflow_state import (
    begin_import_stage,
    complete_import_stage,
    ensure_workflow,
    log_finalize_failure,
    log_import_decision,
    log_import_event,
    mark_stage,
)

logger = logging.getLogger(__name__)

def process_invoice_document(invoice_id: str) -> dict[str, Any]:
    """Legacy-compatible processing entrypoint for credit card invoices."""
    metadata = _load_invoice_metadata(invoice_id) or {}
    try:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.AI_PROCESSING,
            (
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
            ),
        )
    except Exception:
        pass

    ocr_entries = _collect_invoice_ocr_text(invoice_id)
    combined_text = "\n".join(text for _, text in ocr_entries if text)
    if not combined_text.strip():
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
            ),
        )
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.PROCESSING,
            ),
        )
        raise ValueError("Combined OCR text is missing.")

    page_ids = [file_id for file_id, _ in ocr_entries if file_id != invoice_id]
    if page_ids:
        metadata.setdefault("page_ids", page_ids)
        metadata.setdefault("page_count", len(page_ids))
    metadata["combined_ocr_text"] = combined_text
    _update_invoice_metadata(invoice_id, metadata)

    from services.ai_service import AIService

    ai_service = AIService()
    request = CreditCardInvoiceExtractionRequest(
        invoice_id=invoice_id,
        ocr_text=combined_text,
        page_ids=page_ids,
    )

    extraction = ai_service.parse_credit_card_invoice(request)

    main_id = _persist_creditcard_invoice_main(invoice_id, extraction.header, combined_text)
    if not main_id:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
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
        raise RuntimeError("Failed to persist credit card invoice header")

    _persist_creditcard_invoice_items(main_id, extraction.lines)

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

    inserted_invoice_lines = _persist_invoice_lines(invoice_id, invoice_line_payloads)

    metadata = _load_invoice_metadata(invoice_id) or {}
    metadata["creditcard_main_id"] = main_id
    metadata["overall_confidence"] = extraction.overall_confidence
    metadata["invoice_summary"] = {
        "invoice_number": extraction.header.invoice_number,
        "card_holder": extraction.header.card_holder,
        "card_number_masked": extraction.header.card_number_masked,
        "currency": extraction.header.currency,
        "period_start": extraction.header.period_start.isoformat() if hasattr(extraction.header.period_start, "isoformat") else None,
        "period_end": extraction.header.period_end.isoformat() if hasattr(extraction.header.period_end, "isoformat") else None,
    }
    metadata["line_counts"] = {
        "total": inserted_invoice_lines,
        "matched": 0,
        "unmatched": inserted_invoice_lines,
    }
    _update_invoice_metadata(invoice_id, metadata)

    try:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
            ),
        )
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.MATCHING,
            (
                InvoiceDocumentStatus.PROCESSING,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.IMPORTED,
            ),
        )
    except Exception:
        pass

    return {
        "ok": True,
        "status": InvoiceProcessingStatus.READY_FOR_MATCHING.value,
        "lines": inserted_invoice_lines,
        "creditcard_main_id": main_id,
        "confidence": extraction.overall_confidence,
    }

def auto_match_invoice_lines(document_id: str) -> tuple[int, int]:
    if db_cursor is None:
        return (0, 0)

    pending_rows: list[Any] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id,
                       transaction_date,
                       amount,
                       COALESCE(merchant_name, description) AS merchant_hint,
                       match_status
                  FROM invoice_lines
                 WHERE invoice_id=%s
                   AND (match_status IS NULL OR match_status IN ('pending','unmatched'))
                """,
                (document_id,),
            )
            pending_rows = cur.fetchall() or []
    except Exception:
        log_event(
            logger,
            "matching.auto.lines_fetch_failed",
            invoice_id=document_id,
            reason="db_error",
        )
        return (0, 0)

    pending_total = len(pending_rows)
    log_event(
        logger,
        "matching.auto.lines_fetched",
        invoice_id=document_id,
        pending=pending_total,
    )

    if pending_total == 0:
        log_event(
            logger,
            "matching.auto.skipped",
            invoice_id=document_id,
            reason="no_pending_lines",
        )
        return (0, 0)

    def _safe_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _normalize_date(value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        if isinstance(value, str):
            return value.split(" ")[0]
        return str(value)

    pending: dict[int, dict[str, Any]] = {}
    metadata = _load_invoice_metadata(document_id) or {}
    _, credit_items = _load_credit_items_for_invoice(document_id, metadata)
    log_event(
        logger,
        "matching.auto.credit_items_loaded",
        invoice_id=document_id,
        credit_items=len(credit_items),
    )

    def _fetch_receipt_candidates(tx_date: Any, amount: Optional[Decimal]) -> list[Any]:
        if amount is None or db_cursor is None or tx_date is None:
            return []
        date_value = _normalize_date(tx_date)
        if date_value is None:
            return []
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT uf.id,
                           COALESCE(uf.purchase_datetime, uf.created_at) AS match_datetime,
                           CAST(
                               COALESCE(
                                   uf.gross_amount,
                                   NULLIF(uf.gross_amount_sek, 0),
                                   uf.net_amount,
                                   NULLIF(uf.net_amount_sek, 0)
                               ) AS DECIMAL(13, 2)
                           ) AS match_amount,
                           c.name
                      FROM unified_files AS uf
                 LEFT JOIN creditcard_receipt_matches AS m ON m.receipt_id = uf.id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                      WHERE COALESCE(uf.purchase_datetime, uf.created_at) IS NOT NULL
                        AND DATE(COALESCE(uf.purchase_datetime, uf.created_at)) = %s
                        AND COALESCE(
                            uf.gross_amount,
                            NULLIF(uf.gross_amount_sek, 0),
                            uf.net_amount,
                            NULLIF(uf.net_amount_sek, 0)
                        ) IS NOT NULL
                        AND ABS(
                            COALESCE(
                                uf.gross_amount,
                                NULLIF(uf.gross_amount_sek, 0),
                                uf.net_amount,
                                NULLIF(uf.net_amount_sek, 0)
                            ) - %s
                        ) <= 5
                        AND (uf.credit_card_match IS NULL OR uf.credit_card_match = 0)
                        AND m.receipt_id IS NULL
                  ORDER BY ABS(
                               COALESCE(
                                   uf.gross_amount,
                                   NULLIF(uf.gross_amount_sek, 0),
                                   uf.net_amount,
                                   NULLIF(uf.net_amount_sek, 0)
                               ) - %s
                           ) ASC,
                           COALESCE(uf.purchase_datetime, uf.created_at) DESC
                      LIMIT 10
                    """,
                    (date_value, amount, amount),
                )
                return cur.fetchall() or []
        except Exception:
            return []

    for row in pending_rows:
        line_id = int(row[0])
        tx_date = row[1]
        amount = _safe_decimal(row[2])
        merchant_hint = row[3]
        match_status = row[4]
        pending[line_id] = {
            "transaction_date": tx_date,
            "amount": amount,
            "merchant_hint": merchant_hint,
            "initial_status": match_status,
            "matched": False,
            "candidates": [],
        }
        if amount is None or tx_date is None:
            continue
        for candidate in _fetch_receipt_candidates(tx_date, amount):
            receipt_id = str(candidate[0])
            purchase_dt = candidate[1]
            candidate_amount = _safe_decimal(candidate[2])
            company_name = candidate[3]
            if isinstance(purchase_dt, datetime):
                receipt_date = purchase_dt.date()
            elif isinstance(purchase_dt, date):
                receipt_date = purchase_dt
            else:
                receipt_date = None
            if isinstance(tx_date, datetime):
                line_dt = tx_date.date()
            elif isinstance(tx_date, date):
                line_dt = tx_date
            elif isinstance(tx_date, str):
                try:
                    line_dt = datetime.fromisoformat(tx_date[:10]).date()
                except Exception:
                    line_dt = None
            else:
                line_dt = None
            if line_dt is not None and receipt_date is not None:
                date_diff = abs((line_dt - receipt_date).days)
            else:
                date_diff = 9999
            if amount is not None and candidate_amount is not None and amount != 0:
                amount_diff = abs(amount - candidate_amount)
                ratio = min((amount_diff / abs(amount)), Decimal("1"))
            else:
                amount_diff = Decimal("999999")
                ratio = Decimal("1")
            confidence = max(
                0.25,
                float(
                    min(
                        Decimal("0.95"),
                        Decimal("1")
                        - ratio * Decimal("0.6")
                        - Decimal(min(date_diff, 30)) / Decimal("120"),
                    )
                ),
            )
            pending[line_id]["candidates"].append(
                {
                    "receipt_id": receipt_id,
                    "purchase_datetime": purchase_dt,
                    "amount": candidate_amount,
                    "company_name": company_name,
                    "amount_diff": amount_diff,
                    "date_diff": date_diff,
                    "confidence": confidence,
                }
            )
        log_event(
            logger,
            "matching.auto.candidates_collected",
            invoice_id=document_id,
            line_id=line_id,
            candidates=len(pending[line_id]["candidates"]),
            merchant_hint=merchant_hint,
            amount=amount,
        )

    matched = 0
    used_receipts: set[str] = set()
    line_order = sorted(
        pending.keys(),
        key=lambda lid: (len(pending[lid].get("candidates") or []), lid),
    )

    for line_id in line_order:
        line_ctx = pending.get(line_id)
        if not line_ctx or line_ctx.get("matched"):
            continue
        candidates = line_ctx.get("candidates") or []
        if not candidates:
            log_event(
                logger,
                "matching.auto.no_candidates",
                invoice_id=document_id,
                line_id=line_id,
                merchant_hint=line_ctx.get("merchant_hint"),
                amount=line_ctx.get("amount"),
            )
            continue

        item_id, matched_amount = _select_credit_item_for_line(line_ctx, credit_items)
        if item_id is None:
            log_event(
                logger,
                "matching.auto.no_invoice_item",
                invoice_id=document_id,
                line_id=line_id,
                merchant_hint=line_ctx.get("merchant_hint"),
            )
            continue

        for candidate in sorted(
            candidates, key=lambda c: (c["amount_diff"], c["date_diff"])
        ):
            receipt_id = candidate["receipt_id"]
            if receipt_id in used_receipts:
                continue

            updated = transition_line_status_and_link(
                line_id,
                receipt_id,
                candidate["confidence"],
                InvoiceLineMatchStatus.AUTO,
                (
                    InvoiceLineMatchStatus.PENDING,
                    InvoiceLineMatchStatus.UNMATCHED,
                ),
            )
            if not updated:
                log_event(
                    logger,
                    "matching.auto.transition_blocked",
                    invoice_id=document_id,
                    line_id=line_id,
                    receipt_id=receipt_id,
                )
                continue

            line_ctx["matched"] = True
            line_ctx["matched_file_id"] = receipt_id
            used_receipts.add(receipt_id)
            matched += 1

            try:
                with db_cursor() as cur:
                    cur.execute(
                        (
                            "INSERT INTO invoice_line_history "
                            "(invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                            "VALUES (%s, 'matched', 'system', NULL, %s, %s)"
                        ),
                        (line_id, receipt_id, "auto-match-ai5"),
                    )
            except Exception:
                pass

            if matched_amount is None:
                matched_amount = line_ctx.get("amount")

            persist_ok = True
            try:
                _persist_credit_card_match(
                    receipt_id,
                    item_id,
                    matched_amount,
                    candidate["confidence"],
                    True,
                    match_origin="auto",
                )
            except Exception:
                persist_ok = False
                logger.exception(
                    "Failed to persist credit card match (auto) for line %s -> %s",
                    line_id,
                    receipt_id,
                )
                log_event(
                    logger,
                    "matching.auto.persist_failed",
                    invoice_id=document_id,
                    line_id=line_id,
                    receipt_id=receipt_id,
                    invoice_item_id=item_id,
                    level="error",
                )
            record_invoice_decision("matched")
            log_event(
                logger,
                "matching.auto.matched",
                invoice_id=document_id,
                line_id=line_id,
                receipt_id=receipt_id,
                invoice_item_id=item_id,
                amount_diff=candidate["amount_diff"],
                date_diff=candidate["date_diff"],
                confidence=candidate["confidence"],
                matched_amount=matched_amount,
                persisted=persist_ok,
            )
            break

    for line_id, ctx in pending.items():
        if ctx.get("matched"):
            continue
        if ctx.get("initial_status") == InvoiceLineMatchStatus.UNMATCHED.value:
            continue
        updated = transition_line_status(
            line_id,
            InvoiceLineMatchStatus.UNMATCHED,
            (
                InvoiceLineMatchStatus.PENDING,
                InvoiceLineMatchStatus.UNMATCHED,
            ),
        )
        if not updated:
            continue
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "INSERT INTO invoice_line_history "
                        "(invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                        "VALUES (%s, 'no_match', 'system', NULL, NULL, %s)"
                    ),
                    (line_id, "auto-match-ai5-unmatched"),
                )
        except Exception:
            pass
        record_invoice_decision("unmatched")
        log_event(
            logger,
            "matching.auto.marked_unmatched",
            invoice_id=document_id,
            line_id=line_id,
            previous_status=ctx.get("initial_status"),
        )

    total_lines_db: Optional[int] = None
    matched_lines_db: Optional[int] = None
    if db_cursor is not None:
        try:
            total_lines = 0
            matched_lines = 0
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT COUNT(*), SUM(CASE WHEN match_status IN ('auto','manual','confirmed') "
                        "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%s"
                    ),
                    (document_id,),
                )
                row = cur.fetchone()
                if row:
                    total_lines = int(row[0] or 0)
                    matched_lines = int(row[1] or 0)
                    total_lines_db = total_lines
                    matched_lines_db = matched_lines
            metadata = _load_invoice_metadata(document_id) or {}
            metadata.setdefault("line_counts", {})
            metadata["line_counts"] = {
                "total": total_lines,
                "matched": matched_lines,
                "unmatched": max(total_lines - matched_lines, 0),
            }
            _update_invoice_metadata(document_id, metadata)
        except Exception:
            pass

    log_event(
        logger,
        "matching.auto.completed",
        invoice_id=document_id,
        matched=matched,
        evaluated=len(pending_rows),
        total_lines=total_lines_db,
        matched_lines=matched_lines_db,
    )
    return (matched, len(pending_rows))

def refresh_invoice_match_state(document_id: str) -> tuple[int, int]:
    """Recompute invoice match counters and update lifecycle states."""
    if db_cursor is None:
        return (0, 0)

    total_lines = 0
    matched_lines = 0
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT COUNT(*), SUM(CASE WHEN match_status IN ('auto','manual','confirmed') "
                    "THEN 1 ELSE 0 END) FROM invoice_lines WHERE invoice_id=%s"
                ),
                (document_id,),
            )
            row = cur.fetchone()
            if row:
                total_lines = int(row[0] or 0)
                matched_lines = int(row[1] or 0)
    except Exception:
        log_event(
            logger,
            "matching.invoice_state.refresh_failed",
            invoice_id=document_id,
            reason="line_count_query_failed",
            level="error",
        )
        return (0, 0)

    try:
        metadata = _load_invoice_metadata(document_id) or {}
        metadata.setdefault("line_counts", {})
        metadata["line_counts"] = {
            "total": total_lines,
            "matched": matched_lines,
            "unmatched": max(total_lines - matched_lines, 0),
        }
        metadata["processing_status"] = metadata.get("processing_status")
        _update_invoice_metadata(document_id, metadata)
    except Exception:
        pass

    try:
        if total_lines == 0:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                (
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.MATCHED,
                (
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    InvoiceDocumentStatus.MATCHED,
                ),
            )
        elif matched_lines == 0:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                (
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.IMPORTED,
                (
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.IMPORTED,
                ),
            )
        elif matched_lines < total_lines:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                (
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.MATCHED,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                ),
            )
        else:
            transition_processing_status(
                document_id,
                InvoiceProcessingStatus.MATCHING_COMPLETED,
                (
                    InvoiceProcessingStatus.READY_FOR_MATCHING,
                    InvoiceProcessingStatus.AI_PROCESSING,
                    InvoiceProcessingStatus.MATCHING_COMPLETED,
                ),
            )
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.MATCHED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    InvoiceDocumentStatus.MATCHED,
                ),
            )
    except Exception:
        pass

def wf3_firstcard_invoice(workflow_run_id: int) -> int:
    """
    Workflow 3: FirstCard Invoice Processing.
    """
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF3_")
    mark_stage(workflow_run_id, "firstcard_invoice", "running", start=True)

    file_id = wfr.get("file_id")
    if not file_id:
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message="Workflow run missing file_id.",
            end=True,
            workflow_status_override="failed",
        )
        log_finalize_failure(workflow_run_id, "Workflow run saknar file_id")
        raise ValueError("Workflow run missing file_id")

    metadata = _load_invoice_metadata(file_id) or {}

    begin_import_stage(
        workflow_run_id,
        "fc_ocr",
        message=f"Förbereder OCR för FirstCard {file_id}",
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
        pass

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
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "running",
            message=f"file_type={parent_file_type}; workflow_type={parent_workflow_type}; pages={page_count}",
        )
        mark_stage(
            workflow_run_id,
            "ocr_merge",
            "running",
            start=True,
            update_workflow_status=False,
        )

        merged_main_id: Optional[int] = None
        if combined_text:
            merged_main_id = _persist_creditcard_invoice_ocr(file_id, combined_text, metadata)

        ocr_length = len(combined_text or "")
        if merged_main_id:
            if not metadata.get("creditcard_main_id"):
                metadata["creditcard_main_id"] = merged_main_id
            metadata.setdefault("creditcard_invoice_number", f"INV-{file_id}")
            mark_stage(
                workflow_run_id,
                "ocr_merge",
                "succeeded",
                message=f"Persisted merged OCR ({ocr_length} chars) to creditcard_invoices_main id={merged_main_id}",
                end=True,
                update_workflow_status=False,
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
                mark_stage(
                    workflow_run_id,
                    "ocr_merge",
                    "skipped",
                    message="No OCR text available to persist",
                    end=True,
                    update_workflow_status=False,
                )
            else:
                mark_stage(
                    workflow_run_id,
                    "ocr_merge",
                    "failed",
                    message="Failed to persist merged OCR text to creditcard_invoices_main",
                    end=True,
                    update_workflow_status=False,
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
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message=f"OCR preparation failed: {exc}",
            end=True,
            workflow_status_override="failed",
        )
        complete_import_stage(
            workflow_run_id,
            "fc_ocr",
            success=False,
            message=str(exc),
        )
        log_finalize_failure(workflow_run_id, f"OCR-misslyckande: {exc}")
        raise
    else:
        complete_import_stage(
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
        log_import_decision(
            workflow_run_id,
            "fc_is_fc",
            success=is_fc_invoice,
            message=f"AI1 identifierade dokumenttyp: {classification.document_type}",
        )
        if not is_fc_invoice:
            reason = (
                f"AI1 klassificerade dokumentet som '{classification.document_type}' "
                "men endast FC-fakturor tillåts i detta flöde."
            )
            log_import_event(workflow_run_id, "manual_review", message=reason)
            _move_to_manual_review(file_id, reason)
            log_finalize_failure(workflow_run_id, reason)
            mark_stage(
                workflow_run_id,
                "firstcard_invoice",
                "failed",
                message=reason,
                end=True,
                workflow_status_override="failed",
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
        pass

    page_ids = [page.get("file_id") for page in (other_data.get("pages") or []) if page.get("file_id")]

    from services.ai_service import AIService

    ai_service = AIService()
    request = CreditCardInvoiceExtractionRequest(
        invoice_id=file_id,
        ocr_text=combined_text,
        page_ids=page_ids,
    )

    import time
    start_time = time.time()
    ai6_provider = ai_service.prompt_provider_names.get("credit_card_invoice_parsing", "unknown")
    ai6_model = ai_service.prompt_model_names.get("credit_card_invoice_parsing", "unknown")
    begin_import_stage(workflow_run_id, "fc_parse", message="AI6 tolkning av faktura")
    try:
        extraction = ai_service.parse_credit_card_invoice(request)
        elapsed = int((time.time() - start_time) * 1000)

        ai6_prompt = ai_service.prompts.get("credit_card_invoice_parsing", "")
        raw_response = ai_service.last_raw_response or ""
        log_parts = [
            f"Successfully parsed credit card invoice.",
            f"--- PROMPT ---\n{ai6_prompt}",
            f"--- RAW RESPONSE ---\n{raw_response}",
        ]

        _history(
            file_id,
            "ai6",
            "success",
            ai_stage_name="AI6-CreditCardInvoiceParsing",
            log_text="; ".join(log_parts),
            confidence=extraction.overall_confidence,
            processing_time_ms=elapsed,
            provider=ai6_provider,
            model_name=ai6_model,
        )
        complete_import_stage(
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
    except Exception as exc:
        elapsed = int((time.time() - start_time) * 1000)
        error_msg = f"{type(exc).__name__}: {exc}"

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
        )
        complete_import_stage(
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
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message=f"AI6 parsing failed: {type(exc).__name__}: {exc}",
            end=True,
            workflow_status_override="failed",
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
        mark_stage(
            workflow_run_id,
            "firstcard_invoice",
            "failed",
            message="Failed to persist credit card invoice header.",
            end=True,
            workflow_status_override="failed",
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
    metadata["line_counts"] = {
        "total": len(extraction.lines),
        "matched": 0,
        "unmatched": len(extraction.lines),
    }
    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
    _update_invoice_metadata(file_id, metadata)

    begin_import_stage(
        workflow_run_id,
        "fc_ready",
        message="Förbereder fakturan för matchning",
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
    complete_import_stage(
        workflow_run_id,
        "fc_ready",
        success=True,
        message="Fakturan redo för AI5",
    )

    try:
        mark_stage(
            workflow_run_id,
            "auto_match",
            "running",
            start=True,
            update_workflow_status=False,
        )
        begin_import_stage(
            workflow_run_id,
            "ai5",
            message="AI5 kortmatchning startar",
        )
        matched_auto, evaluated = auto_match_invoice_lines(file_id)
        total_lines, matched_lines = refresh_invoice_match_state(file_id)
        mark_stage(
            workflow_run_id,
            "auto_match",
            "succeeded",
            message=f"Auto-matched {matched_lines} of {total_lines} lines (new matches: {matched_auto})",
            end=True,
            update_workflow_status=False,
        )
        complete_import_stage(
            workflow_run_id,
            "ai5",
            success=True,
            message=f"AI5 matchade {matched_lines}/{total_lines} rader",
        )
        has_match = matched_lines > 0
        log_import_decision(
            workflow_run_id,
            "m_found",
            success=has_match,
            message="Match hittad" if has_match else "Inga automatiska matchningar",
        )
        if has_match:
            begin_import_stage(
                workflow_run_id,
                "m_link",
                message="Länkar kvitton till fakturarader",
            )
            complete_import_stage(
                workflow_run_id,
                "m_link",
                success=True,
                message=f"{matched_lines} rader länkade",
            )
        unmatched_count = max(total_lines - matched_lines, 0)
        if unmatched_count > 0:
            begin_import_stage(
                workflow_run_id,
                "m_unmatched",
                message="Flaggar omatchade rader",
            )
            complete_import_stage(
                workflow_run_id,
                "m_unmatched",
                success=True,
                message=f"{unmatched_count} rader kvar att hantera",
            )
    except Exception as exc:
        mark_stage(
            workflow_run_id,
            "auto_match",
            "failed",
            message=f"Auto-match failed: {exc}",
            end=True,
            update_workflow_status=False,
        )
        complete_import_stage(
            workflow_run_id,
            "ai5",
            success=False,
            message=f"AI5 misslyckades: {exc}",
        )

    mark_stage(
        workflow_run_id,
        "firstcard_invoice",
        "succeeded",
        message=f"Parsed credit card invoice: main_id={main_id}, lines={items_inserted}/{inserted_invoice_lines}",
        end=True,
        workflow_status_override="succeeded",
    )
    begin_import_stage(
        workflow_run_id,
        "finalize_ok",
        message="FirstCard-flödet klart",
    )
    complete_import_stage(
        workflow_run_id,
        "finalize_ok",
        success=True,
        message="Fakturaflödet avslutades utan fel",
    )
    log_import_event(
        workflow_run_id,
        "KLAR",
        message="WF3 slutförd",
    )
    return workflow_run_id
