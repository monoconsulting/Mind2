# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Status endpoints for FirstCard invoice reconciliation.

Provides invoice processing status and detailed invoice information.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flask import jsonify

from .. import recon_bp
from ..utils.db_helpers import (
    count_invoice_lines,
    list_invoice_files,
    load_invoice_document,
    as_decimal,
)

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)

# OCR status constants
_OCR_COMPLETE_STATUSES = {"ocr_done", "completed", "processed", "ready", "ai_done"}


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/status")
def invoice_status(invoice_id: str) -> Any:
    """Return processing status, OCR progress, and match stats for an invoice."""

    doc = load_invoice_document(invoice_id)
    if not doc:
        return jsonify({"error": "not_found"}), 404

    status, metadata, _ = doc
    source_file_id = metadata.get("source_file_id") or invoice_id
    files = list_invoice_files(source_file_id)

    page_records: list[dict[str, Any]] = []
    for record in files:
        page_number = record["other_data"].get("page_number")
        if page_number is None and record["id"] == source_file_id:
            # Single-page uploads reuse the main file without explicit numbering.
            page_number = 1 if metadata.get("detected_kind") != "pdf" else None
        if page_number is None:
            continue
        page_records.append(
            {
                "file_id": record["id"],
                "page_number": int(page_number),
                "status": record.get("ai_status") or "uploaded",
            }
        )

    if not page_records and files:
        # Fallback for legacy metadata without page numbers.
        for idx, record in enumerate(files, 1):
            page_records.append(
                {
                    "file_id": record["id"],
                    "page_number": idx,
                    "status": record.get("ai_status") or "uploaded",
                }
            )

    total_pages = metadata.get("page_count") or len(page_records)
    if total_pages == 0 and page_records:
        total_pages = len(page_records)

    completed_pages = sum(
        1
        for page in page_records
        if (page.get("status") or "").lower() in _OCR_COMPLETE_STATUSES
    )

    if total_pages <= 0:
        total_pages = len(page_records)
    percentage = 0.0
    if total_pages:
        percentage = round((completed_pages / total_pages) * 100, 2)

    processing_status = metadata.get("processing_status")
    if not processing_status:
        processing_status = "ocr_done" if completed_pages >= total_pages and total_pages else "ocr_pending"

    ai_summary = metadata.get("ai_summary")
    if not ai_summary:
        for record in files:
            if record["id"] == source_file_id and record.get("ocr_raw"):
                snippet = (record["ocr_raw"] or "")
                ai_summary = snippet[:400]
                break

    total_lines, matched_lines = count_invoice_lines(invoice_id)

    invoice_summary = metadata.get("invoice_summary")
    if not isinstance(invoice_summary, dict):
        invoice_summary = None

    response = {
        "invoice_id": invoice_id,
        "status": status,
        "processing_status": processing_status,
        "source_file_id": source_file_id,
        "ocr_progress": {
            "total_pages": total_pages,
            "completed_pages": completed_pages,
            "percentage": percentage,
            "pages": page_records,
        },
        "ai_summary": ai_summary or "",
        "line_counts": {
            "total": total_lines,
            "matched": matched_lines,
            "unmatched": max(total_lines - matched_lines, 0),
        },
        "overall_confidence": metadata.get("overall_confidence"),
        "invoice_summary": invoice_summary,
        "creditcard_main_id": metadata.get("creditcard_main_id"),
        "period_start": metadata.get("period_start"),
        "period_end": metadata.get("period_end"),
    }

    return jsonify(response), 200


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>")
def invoice_detail(invoice_id: str) -> Any:
    if db_cursor is None:  # pragma: no cover
        return jsonify({"error": "not_found"}), 404

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT invoice_type,
                       status,
                       processing_status,
                       period_start,
                       period_end,
                       uploaded_at,
                       metadata_json
                  FROM invoice_documents
                 WHERE id = %s
                   AND deleted_at IS NULL
                """,
                (invoice_id,),
            )
            row = cur.fetchone()
    except Exception:
        row = None

    if not row:
        return jsonify({"error": "not_found"}), 404

    (
        invoice_type,
        status,
        processing_status,
        period_start,
        period_end,
        uploaded_at,
        metadata_raw,
    ) = row

    metadata: dict[str, Any] = {}
    if metadata_raw:
        try:
            metadata = json.loads(metadata_raw)
        except Exception:
            metadata = {}

    computed_total, computed_matched = count_invoice_lines(invoice_id)
    stored_counts = metadata.get("line_counts") if isinstance(metadata.get("line_counts"), dict) else None
    if isinstance(stored_counts, dict):
        total_lines = int(stored_counts.get("total") or computed_total)
        matched_lines = int(stored_counts.get("matched") or computed_matched)
        unmatched_lines = stored_counts.get("unmatched")
        if unmatched_lines is None:
            unmatched_lines = max(total_lines - matched_lines, 0)
    else:
        total_lines = computed_total
        matched_lines = computed_matched
        unmatched_lines = max(total_lines - matched_lines, 0)
    line_counts = {
        "total": total_lines,
        "matched": matched_lines,
        "unmatched": unmatched_lines,
    }
    metadata["line_counts"] = line_counts

    creditcard_main_id = metadata.get("creditcard_main_id")
    card_details: dict[str, Any] | None = None
    items: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    if db_cursor is not None and creditcard_main_id:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT id,
                           card_type,
                           card_name,
                           card_number_masked,
                           card_holder
                      FROM creditcard_invoices_main
                     WHERE id = %s
                    """,
                    (creditcard_main_id,),
                )
                row = cur.fetchone()
        except Exception:
            row = None
        if row:
            (
                main_id,
                card_type,
                card_name,
                card_number_masked,
                card_holder,
            ) = row
            card_details = {
                "id": int(main_id),
                "card_type": card_type,
                "card_name": card_name,
                "card_number_masked": card_number_masked,
                "card_holder": card_holder,
            }
            summary_payload = metadata.get("invoice_summary")
            if not isinstance(summary_payload, dict):
                summary_payload = {}
            if card_type:
                summary_payload.setdefault("card_type", card_type)
            if card_name:
                summary_payload.setdefault("card_name", card_name)
            if card_type and card_name:
                summary_payload.setdefault("card_label", f"{card_type} - {card_name}")
            summary_payload.setdefault("card_number_masked", card_number_masked)
            summary_payload.setdefault("card_holder", card_holder)
            metadata["invoice_summary"] = summary_payload
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT ci.id,
                           ci.line_no,
                           ci.purchase_date,
                           ci.merchant_name,
                           ci.merchant_city,
                           ci.amount_original,
                           ci.amount_sek,
                           ci.gross_amount,
                           ci.net_amount,
                           ci.currency_original,
                           ci.vat_rate,
                           ci.matched,
                           crm.receipt_id,
                           crm.matched_amount,
                           uf.purchase_datetime,
                           uf.gross_amount AS receipt_gross_amount,
                           uf.credit_card_match,
                           uf.created_at,
                           c.name AS vendor_name
                      FROM creditcard_invoice_items AS ci
                 LEFT JOIN creditcard_receipt_matches AS crm ON crm.invoice_item_id = ci.id
                 LEFT JOIN unified_files AS uf ON uf.id = crm.receipt_id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                     WHERE ci.main_id = %s
                  ORDER BY ci.line_no ASC, ci.id ASC
                    """,
                    (creditcard_main_id,),
                )
                item_rows = cur.fetchall() or []
        except Exception:
            item_rows = []
        for (
            item_id,
            line_no,
            purchase_date,
            merchant_name,
            merchant_city,
            amount_original,
            amount_sek,
            gross_amount,
            net_amount,
            currency_original,
            vat_rate,
            matched_flag,
            receipt_id,
            matched_amount,
            receipt_purchase_dt,
            receipt_gross_amount,
            receipt_match_flag,
            receipt_created_at,
            receipt_vendor_name,
        ) in item_rows:
            match_value = int(matched_flag or 0)
            match_status_token = "pending"
            if match_value == 2:
                match_status_token = "manual"
            elif match_value >= 1:
                match_status_token = "auto"

            matched_receipt: dict[str, Any] | None = None
            if receipt_id:
                matched_receipt = {
                    "file_id": receipt_id,
                    "purchase_datetime": receipt_purchase_dt.isoformat() if hasattr(receipt_purchase_dt, "isoformat") else receipt_purchase_dt,
                    "gross_amount": float(receipt_gross_amount) if receipt_gross_amount is not None else None,
                    "credit_card_match": bool(receipt_match_flag) if receipt_match_flag is not None else False,
                    "vendor_name": receipt_vendor_name,
                    "matched_at": receipt_created_at.isoformat() if hasattr(receipt_created_at, "isoformat") else receipt_created_at,
                }

            items.append(
                {
                    "id": int(item_id),
                    "line_no": int(line_no) if line_no is not None else None,
                    "purchase_date": purchase_date.isoformat() if hasattr(purchase_date, "isoformat") else purchase_date,
                    "merchant_name": merchant_name,
                    "merchant_city": merchant_city,
                    "amount_original": float(amount_original) if amount_original is not None else None,
                    "amount_sek": float(amount_sek) if amount_sek is not None else None,
                    "gross_amount": float(gross_amount) if gross_amount is not None else None,
                    "net_amount": float(net_amount) if net_amount is not None else None,
                    "vat_rate": float(vat_rate) if vat_rate is not None else None,
                    "currency_original": currency_original,
                    "matched": match_value,
                    "matched_receipt_id": receipt_id,
                }
            )

            display_amount = (
                as_decimal(amount_sek)
                or as_decimal(gross_amount)
                or as_decimal(amount_original)
                or as_decimal(net_amount)
            )

            lines.append(
                {
                    "id": int(item_id),
                    "invoice_id": invoice_id,
                    "transaction_date": purchase_date.isoformat() if hasattr(purchase_date, "isoformat") else purchase_date,
                    "amount": float(display_amount) if display_amount is not None else None,
                    "currency": currency_original,
                    "description": merchant_name or merchant_city or "",
                    "match_status": match_status_token,
                    "match_score": 1.0 if matched_receipt else None,
                    "matched_file_id": receipt_id,
                    "matched_receipt": matched_receipt,
                }
            )

    summary_payload = metadata.get("invoice_summary") if isinstance(metadata.get("invoice_summary"), dict) else None

    invoice_payload = {
        "id": invoice_id,
        "invoice_type": invoice_type,
        "status": status,
        "processing_status": processing_status or metadata.get("processing_status"),
        "period_start": metadata.get("period_start") or period_start,
        "period_end": metadata.get("period_end") or period_end,
        "uploaded_at": str(uploaded_at) if uploaded_at else None,
        "submitted_by": metadata.get("submitted_by"),
        "line_counts": line_counts,
        "invoice_summary": summary_payload,
        "overall_confidence": metadata.get("overall_confidence"),
        "creditcard_main_id": metadata.get("creditcard_main_id"),
        "invoice_number": (summary_payload or {}).get("invoice_number") or metadata.get("invoice_number"),
        "metadata": metadata,
    }
    if card_details:
        invoice_payload["creditcard_details"] = card_details

    return jsonify({"invoice": invoice_payload, "lines": lines, "items": items}), 200
