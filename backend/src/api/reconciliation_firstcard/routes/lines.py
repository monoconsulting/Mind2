# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Invoice lines endpoints for FirstCard reconciliation.

Provides line item listing and candidate matching.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, TypedDict

from flask import jsonify, request

from .. import recon_bp
from ..utils.db_helpers import (
    load_invoice_document,
    as_date,
    as_decimal,
)
from services.status_constants import InvoiceLineMatchStatus

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)
MATCH_DATE_WINDOW_DAYS = 60
MATCH_AMOUNT_TOLERANCE = Decimal("10")


class MatchedReceiptPayload(TypedDict):
    file_id: str
    purchase_datetime: str | None
    gross_amount: float | None
    credit_card_match: bool
    vendor_name: str | None


class CandidatePayload(TypedDict):
    file_id: str
    purchase_datetime: str | None
    gross_amount: float | None
    vendor_name: str | None
    credit_card_match: bool
    amount_difference: float | None
    date_difference_days: int | None
    match_score: float
    is_current_match: bool


class LinePayload(TypedDict):
    id: int
    invoice_id: str | None
    transaction_date: str | None
    amount: float | None
    currency: str | None
    description: str
    match_status: str
    matched_file_id: str | None
    matched_receipt: MatchedReceiptPayload | None
    candidates_found: int


def _shape_payload(payload: dict[str, Any], allowed_keys: set[str]) -> dict[str, Any]:
    """Return a deterministic payload with only the allowed keys."""
    return {key: payload.get(key) for key in allowed_keys}


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/lines")
def invoice_lines(invoice_id: str) -> Any:
    """Return invoice line items with pagination guards."""

    limit_param = request.args.get("limit", "50")
    offset_param = request.args.get("offset", "0")
    try:
        limit = max(1, min(int(limit_param), 200))
    except ValueError:
        limit = 50
    try:
        offset = max(0, int(offset_param))
    except ValueError:
        offset = 0

    if db_cursor is None:  # pragma: no cover
        return jsonify({"items": [], "total": 0, "matched": 0, "limit": limit, "offset": offset, "next_offset": None}), 200

    if not load_invoice_document(invoice_id):
        return jsonify({"error": "not_found"}), 404

    total = 0
    matched = 0
    items: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                f"SELECT COUNT(1), "
                f"SUM(CASE WHEN match_status IN ('{InvoiceLineMatchStatus.AUTO.value}','{InvoiceLineMatchStatus.MANUAL.value}','{InvoiceLineMatchStatus.CONFIRMED.value}') THEN 1 ELSE 0 END) "
                f"FROM invoice_lines WHERE invoice_id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
            if row:
                total, matched = int(row[0] or 0), int(row[1] or 0)

            cur.execute(
                (
                    "SELECT id, transaction_date, amount, merchant_name, description, "
                    "match_status, match_score, matched_file_id "
                    "FROM invoice_lines WHERE invoice_id=%s "
                    "ORDER BY transaction_date ASC, id ASC LIMIT %s OFFSET %s"
                ),
                (invoice_id, limit, offset),
            )
            for row in cur.fetchall() or []:
                (
                    line_id,
                    transaction_date,
                    amount,
                    merchant_name,
                    description,
                    match_status,
                    match_score,
                    matched_file_id,
                ) = row
                items.append(
                    {
                        "id": int(line_id),
                        "transaction_date": (
                            transaction_date.isoformat()
                            if hasattr(transaction_date, "isoformat")
                            else transaction_date
                        ),
                        "amount": float(amount) if amount is not None else None,
                        "merchant_name": merchant_name,
                        "description": description,
                        "match_status": match_status,
                        "match_score": float(match_score) if match_score is not None else None,
                        "matched_file_id": matched_file_id,
                    }
                )
    except Exception:
        items = []

    next_offset = offset + limit if (offset + limit) < total else None

    return (
        jsonify(
            {
                "items": items,
                "total": total,
                "matched": matched,
                "limit": limit,
                "offset": offset,
                "next_offset": next_offset,
            }
        ),
        200,
    )



@recon_bp.get("/reconciliation/firstcard/lines/<int:line_id>/candidates")
def line_candidates(line_id: int) -> Any:
    if db_cursor is None:  # pragma: no cover
        return jsonify({"line": None, "candidates": []}), 200

    invoice_id = request.args.get("invoice_id")

    # Read from invoice_lines instead of creditcard_invoice_items
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT il.id,
                       il.invoice_id,
                       il.transaction_date,
                       il.amount,
                       il.merchant_name,
                       il.description,
                       il.match_status,
                       il.matched_file_id,
                       uf.purchase_datetime,
                       uf.gross_amount AS receipt_gross_amount,
                       uf.credit_card_match,
                       uf.created_at,
                       c.name AS vendor_name
                  FROM invoice_lines AS il
             LEFT JOIN unified_files AS uf ON uf.id = il.matched_file_id
             LEFT JOIN companies AS c ON c.id = uf.company_id
                 WHERE il.id = %s
                """,
                (line_id,),
            )
            line_row = cur.fetchone()
    except Exception:
        line_row = None

    if not line_row:
        return jsonify({"line": None, "candidates": []}), 200

    (
        line_id_val,
        line_invoice_id,
        transaction_date,
        amount,
        merchant_name,
        description,
        match_status,
        matched_file_id,
        matched_purchase_dt,
        matched_gross_amount,
        matched_credit_flag,
        matched_created_at,
        matched_vendor_name,
    ) = line_row

    matched_receipt_payload: MatchedReceiptPayload | None = None
    if matched_file_id:
        matched_receipt_payload = MatchedReceiptPayload(
            file_id=matched_file_id,
            purchase_datetime=matched_purchase_dt.isoformat()
            if hasattr(matched_purchase_dt, "isoformat")
            else matched_purchase_dt,
            gross_amount=float(matched_gross_amount) if matched_gross_amount is not None else None,
            credit_card_match=bool(matched_credit_flag) if matched_credit_flag is not None else False,
            vendor_name=matched_vendor_name,
        )

    display_amount = as_decimal(amount)

    line_payload: LinePayload = LinePayload(
        id=int(line_id_val),
        invoice_id=line_invoice_id or invoice_id,
        transaction_date=transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else transaction_date,
        amount=float(display_amount) if display_amount is not None else None,
        currency=None,
        description=description or merchant_name or "",
        match_status=match_status or "pending",
        matched_file_id=matched_file_id,
        matched_receipt=matched_receipt_payload,
        candidates_found=0,
    )

    target_date = as_date(transaction_date)
    target_amount = display_amount

    candidates: list[CandidatePayload] = []

    try:
        match_datetime_expr = "COALESCE(uf.purchase_datetime, uf.created_at)"
        match_amount_expr = (
            "COALESCE("
            "NULLIF(uf.gross_amount, 0), "
            "NULLIF(uf.gross_amount_sek, 0), "
            "NULLIF(uf.net_amount, 0), "
            "NULLIF(uf.net_amount_sek, 0)"
            ")"
        )
        clauses = [
            "SELECT uf.id,",
            f"       {match_datetime_expr} AS match_datetime,",
            f"       CAST({match_amount_expr} AS DECIMAL(13, 2)) AS match_amount,",
            "       uf.credit_card_match,",
            "       uf.created_at,",
            "       c.name",
            "  FROM unified_files AS uf",
            " LEFT JOIN invoice_lines AS il ON il.matched_file_id = uf.id AND il.id != %s",
            " LEFT JOIN companies AS c ON c.id = uf.company_id",
            " WHERE (il.id IS NULL OR il.id = %s)",
            "   AND uf.file_type = 'receipt'",
            "   AND uf.expense_type = 'corporate'",
        ]
        params: list[Any] = [line_id, line_id]
        if target_date is not None:
            clauses.append(f"   AND ABS(DATEDIFF(DATE({match_datetime_expr}), %s)) <= %s")
            params.append(target_date)
            params.append(MATCH_DATE_WINDOW_DAYS)
        if target_amount is not None:
            clauses.append(f"   AND ABS({match_amount_expr} - %s) <= %s")
            params.append(target_amount)
            params.append(float(MATCH_AMOUNT_TOLERANCE))
        clauses.append(
            " ORDER BY "
            "CASE WHEN match_amount IS NULL THEN 1 ELSE 0 END, "
            "ABS(match_amount - %s), "
            f"ABS(DATEDIFF(DATE({match_datetime_expr}), %s)) ASC, "
            "uf.created_at DESC LIMIT 50"
        )
        params.extend(
            [
                target_amount if target_amount is not None else Decimal("0"),
                target_date if target_date is not None else date.today(),
            ]
        )
        query = "\n".join(clauses)
        with db_cursor() as cur:
            cur.execute(query, tuple(params))
            candidate_rows = cur.fetchall() or []
    except Exception:
        candidate_rows = []

    for (
        receipt_id,
        match_datetime,
        match_amount_value,
        credit_flag,
        created_at,
        vendor_name,
    ) in candidate_rows:
        receipt_amount = as_decimal(match_amount_value)
        amount_diff = None
        if target_amount is not None and receipt_amount is not None:
            amount_diff = abs(Decimal(str(target_amount)) - receipt_amount)
        date_diff = None
        candidate_date = as_date(match_datetime)
        if target_date is not None and candidate_date is not None:
            date_diff = abs((candidate_date - target_date).days)

        score = Decimal("1.0")
        if amount_diff is not None and target_amount not in (None, 0):
            denom = abs(Decimal(str(target_amount))) or Decimal("1")
            score -= Decimal(min((amount_diff / denom), Decimal("1"))) * Decimal("0.7")
        if date_diff is not None:
            score -= Decimal(min(Decimal(date_diff) / Decimal("30"), Decimal("1"))) * Decimal("0.3")
        if score < 0:
            score = Decimal("0")

        candidates.append(
            CandidatePayload(
                file_id=receipt_id,
                purchase_datetime=match_datetime.isoformat() if hasattr(match_datetime, "isoformat") else match_datetime,
                gross_amount=float(receipt_amount) if receipt_amount is not None else None,
                vendor_name=vendor_name,
                credit_card_match=bool(credit_flag) if credit_flag is not None else False,
                amount_difference=float(amount_diff) if amount_diff is not None else None,
                date_difference_days=date_diff,
                match_score=float(score),
                is_current_match=receipt_id == matched_file_id,
            )
        )


    if matched_receipt_payload and not any(c["is_current_match"] for c in candidates):
        candidates.insert(
            0,
            CandidatePayload(
                file_id=matched_file_id,
                purchase_datetime=matched_purchase_dt.isoformat()
                if hasattr(matched_purchase_dt, "isoformat")
                else matched_purchase_dt,
                gross_amount=matched_receipt_payload.get("gross_amount"),
                vendor_name=matched_vendor_name,
                credit_card_match=bool(matched_credit_flag) if matched_credit_flag is not None else False,
                amount_difference=0.0,
                date_difference_days=0,
                match_score=1.0,
                is_current_match=True,
            ),
        )

    candidates.sort(
        key=lambda entry: (
            entry.get("is_current_match") is not True,
            entry.get("amount_difference") if entry.get("amount_difference") is not None else float("inf"),
            entry.get("date_difference_days") if entry.get("date_difference_days") is not None else 999,
        )
    )

    line_payload["candidates_found"] = len(candidates)

    line_payload = LinePayload(
        **_shape_payload(line_payload, set(LinePayload.__annotations__.keys()))
    )
    candidates = [
        CandidatePayload(**_shape_payload(candidate, set(CandidatePayload.__annotations__.keys())))
        for candidate in candidates
    ]

    return jsonify({"line": line_payload, "candidates": candidates}), 200
