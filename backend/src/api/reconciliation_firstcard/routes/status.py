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

    # Read card details from invoice_summary metadata if available
    summary_payload = metadata.get("invoice_summary")
    if isinstance(summary_payload, dict):
        if any(k in summary_payload for k in ["card_type", "card_name", "card_holder"]):
            card_details = {
                "card_type": summary_payload.get("card_type"),
                "card_name": summary_payload.get("card_name"),
                "card_number_masked": summary_payload.get("card_number_masked"),
                "card_holder": summary_payload.get("card_holder"),
            }

    # Read invoice lines from invoice_lines table (NEW approach)
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT il.id,
                           il.transaction_date,
                           il.merchant_name,
                           il.description,
                           il.amount,
                           NULL AS currency,
                           il.extraction_confidence AS confidence,
                           il.match_status,
                           il.match_score,
                           il.matched_file_id,
                           COALESCE(uf.purchase_datetime, uf.created_at) AS receipt_datetime,
                           COALESCE(
                               NULLIF(uf.gross_amount, 0),
                               NULLIF(uf.gross_amount_sek, 0),
                               NULLIF(uf.net_amount, 0),
                               NULLIF(uf.net_amount_sek, 0)
                           ) AS receipt_gross_amount,
                           uf.credit_card_match,
                           uf.created_at,
                           c.name AS vendor_name
                      FROM invoice_lines AS il
                 LEFT JOIN unified_files AS uf ON uf.id = il.matched_file_id
                 LEFT JOIN companies AS c ON c.id = uf.company_id
                     WHERE il.invoice_id = %s
                  ORDER BY il.id ASC
                    """,
                    (invoice_id,),
                )
                line_rows = cur.fetchall() or []
        except Exception:
            logger.exception("Failed to load invoice lines for %s", invoice_id)
            line_rows = []

        for (
            line_id,
            transaction_date,
            merchant_name,
            description,
            amount,
            currency,
            confidence,
            match_status,
            match_score,
            matched_file_id,
            receipt_purchase_dt,
            receipt_gross_amount,
            receipt_match_flag,
            receipt_created_at,
            receipt_vendor_name,
        ) in line_rows:
            matched_receipt: dict[str, Any] | None = None
            if matched_file_id:
                matched_receipt = {
                    "file_id": matched_file_id,
                    "purchase_datetime": receipt_purchase_dt.isoformat() if hasattr(receipt_purchase_dt, "isoformat") else receipt_purchase_dt,
                    "gross_amount": float(receipt_gross_amount) if receipt_gross_amount is not None else None,
                    "credit_card_match": bool(receipt_match_flag) if receipt_match_flag is not None else False,
                    "vendor_name": receipt_vendor_name,
                    "matched_at": receipt_created_at.isoformat() if hasattr(receipt_created_at, "isoformat") else receipt_created_at,
                }

            # Build lines array
            lines.append(
                {
                    "id": int(line_id),
                    "invoice_id": invoice_id,
                    "transaction_date": transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else transaction_date,
                    "amount": float(amount) if amount is not None else None,
                    "currency": currency,
                    "description": description or merchant_name or "",
                    "merchant_name": merchant_name,
                    "match_status": match_status or "pending",
                    "match_score": float(match_score) if match_score is not None else None,
                    "matched_file_id": matched_file_id,
                    "matched_receipt": matched_receipt,
                    "confidence": float(confidence) if confidence is not None else None,
                }
            )

            # Build items array for backward compatibility (deprecated, but kept for now)
            # Map match_status to legacy matched flag
            matched_flag = 0
            if match_status == "manual":
                matched_flag = 2
            elif match_status in ("auto", "confirmed"):
                matched_flag = 1

            items.append(
                {
                    "id": int(line_id),
                    "line_no": None,  # Not stored in invoice_lines
                    "purchase_date": transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else transaction_date,
                    "merchant_name": merchant_name,
                    "merchant_city": None,  # Not stored in invoice_lines
                    "amount_original": float(amount) if amount is not None else None,
                    "amount_sek": float(amount) if amount is not None else None,
                    "gross_amount": float(amount) if amount is not None else None,
                    "net_amount": None,
                    "vat_rate": None,
                    "currency_original": currency,
                    "matched": matched_flag,
                    "matched_receipt_id": matched_file_id,
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
