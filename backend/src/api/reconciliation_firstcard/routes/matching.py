# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Matching endpoints for FirstCard reconciliation.

Handles automatic and manual matching of invoice lines to receipts.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from flask import jsonify, request

from .. import recon_bp
from ..utils.db_helpers import (
    load_invoice_document,
    find_invoice_id_for_main,
    find_invoice_line_id_for_item,
    log_line_history,
    as_decimal,
)
from ..services.workflow_coordinator import WorkflowCoordinator
from services.tasks import (
    auto_match_invoice_lines,
    refresh_invoice_match_state,
)
from services.invoice_status import (
    InvoiceLineMatchStatus,
    transition_line_status_and_link,
)
from api.ai_processing import _backfill_receipt_card_from_fc, _persist_credit_card_match
from observability.events import log_event

try:
    from observability.metrics import record_invoice_decision  # type: ignore
except Exception:  # pragma: no cover
    def record_invoice_decision(_d: str) -> None:  # type: ignore
        return None

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)


@recon_bp.post("/reconciliation/firstcard/match")
def match_invoice_lines() -> Any:
    """Attempt automatic matching of invoice lines against receipts."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    payload = request.get_json(silent=True) or {}
    invoice_id = payload.get("document_id") or payload.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "missing_document_id"}), 400

    doc = load_invoice_document(invoice_id)
    if not doc:
        return jsonify({"error": "not_found"}), 404

    log_event(
        logger,
        "matching.api.invoice.requested",
        invoice_id=invoice_id,
        actor="reconciliation_ui",
    )

    try:
        matched_new, evaluated = auto_match_invoice_lines(invoice_id)
    except Exception as exc:
        logger.error("Auto-match failed for %s: %s", invoice_id, exc)
        log_event(
            logger,
            "matching.api.invoice.failed",
            invoice_id=invoice_id,
            level="error",
            reason=str(exc),
        )
        return jsonify({"error": "auto_match_failed"}), 500

    total_lines, matched_lines = refresh_invoice_match_state(invoice_id)
    log_event(
        logger,
        "matching.api.invoice.completed",
        invoice_id=invoice_id,
        matched=matched_new,
        evaluated=evaluated,
        total_lines=total_lines,
        matched_total=matched_lines,
    )
    return (
        jsonify(
            {
                "invoice_id": invoice_id,
                "matched": matched_new,
                "total": total_lines,
                "matched_total": matched_lines,
                "unmatched": max(total_lines - matched_lines, 0),
                "evaluated": evaluated,
            }
        ),
        200,
    )


@recon_bp.put("/reconciliation/firstcard/lines/<int:line_id>")
def update_line_match(line_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    new_file_id = payload.get("matched_file_id") or payload.get("file_id")
    invoice_id = payload.get("invoice_id")

    if not new_file_id or db_cursor is None:
        return jsonify({"ok": False, "reason": "invalid_request"}), 400
    log_event(
        logger,
        "matching.api.line.requested",
        line_id=line_id,
        invoice_id=invoice_id,
        receipt_id=new_file_id,
        actor="reconciliation_ui",
    )

    # Read from invoice_lines instead of creditcard_invoice_items
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT invoice_id,
                       transaction_date,
                       amount
                  FROM invoice_lines
                 WHERE id=%s
                """,
                (line_id,),
            )
            row = cur.fetchone()
    except Exception:
        row = None

    if not row:
        log_event(
            logger,
            "matching.api.line.failed",
            line_id=line_id,
            level="error",
            reason="invoice_line_missing",
        )
        return jsonify({"ok": False, "reason": "not_found"}), 404

    line_invoice_id = row[0]
    transaction_date = row[1]
    matched_amount = as_decimal(row[2])

    if not invoice_id:
        invoice_id = line_invoice_id
    if not invoice_id:
        log_event(
            logger,
            "matching.api.line.failed",
            line_id=line_id,
            level="error",
            reason="invoice_not_found",
        )
        return jsonify({"ok": False, "reason": "invoice_not_found"}), 404

    # Check for conflicts - if another line is already matched to this file
    try:
        with db_cursor() as cur:
            cur.execute("SELECT id FROM invoice_lines WHERE matched_file_id=%s AND id<>%s LIMIT 1", (new_file_id, line_id))
            conflict = cur.fetchone()
    except Exception:
        conflict = None

    if conflict:
        log_event(
            logger,
            "matching.api.line.failed",
            line_id=line_id,
            invoice_id=invoice_id,
            receipt_id=new_file_id,
            level="warning",
            reason="receipt_in_use",
        )
        return jsonify({"ok": False, "reason": "receipt_in_use"}), 409

    try:
        old_match: Optional[str] = None
        with db_cursor() as cur:
            cur.execute("SELECT matched_file_id FROM invoice_lines WHERE id=%s", (line_id,))
            row = cur.fetchone()
            if row:
                old_match = row[0]

        updated = transition_line_status_and_link(
            line_id,
            new_file_id,
            1.0,
            InvoiceLineMatchStatus.MANUAL,
            (
                InvoiceLineMatchStatus.PENDING,
                InvoiceLineMatchStatus.UNMATCHED,
                InvoiceLineMatchStatus.AUTO,
            ),
        )
        if not updated:
            log_event(
                logger,
                "matching.api.line.failed",
                line_id=line_id,
                invoice_id=invoice_id,
                receipt_id=new_file_id,
                level="warning",
                reason="line_state_conflict",
            )
            return jsonify({"ok": False, "reason": "line_state_conflict"}), 409

        log_line_history(
            line_id,
            "matched",
            "manual",
            old_file_id=old_match,
            new_file_id=new_file_id,
            reason="manual-match",
        )
        record_invoice_decision("matched")
    except Exception:
        log_event(
            logger,
            "matching.api.line.failed",
            line_id=line_id,
            invoice_id=invoice_id,
            receipt_id=new_file_id,
            level="error",
            reason="persist_failed",
        )
        return jsonify({"ok": False, "reason": "persist_failed"}), 500

    if invoice_id:
        refresh_invoice_match_state(invoice_id)

    try:
        _backfill_receipt_card_from_fc(
            new_file_id,
            invoice_id=invoice_id,
        )
    except Exception:
        logger.exception("Failed to backfill card details after manual match for %s", new_file_id)

    log_event(
        logger,
        "matching.api.line.completed",
        line_id=line_id,
        invoice_id=invoice_id,
        receipt_id=new_file_id,
        matched_amount=matched_amount,
    )
    return jsonify({"ok": True}), 200
