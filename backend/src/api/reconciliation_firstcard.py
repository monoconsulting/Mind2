from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
import base64
import io
import re

from flask import Blueprint, jsonify, request
try:
    from observability.metrics import record_invoice_decision  # type: ignore
except Exception:  # pragma: no cover
    def record_invoice_decision(_d: str) -> None:  # type: ignore
        return None

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


recon_bp = Blueprint("reconciliation_firstcard", __name__)



def _decode_pdf_payload(payload: dict[str, Any]) -> Optional[bytes]:
    pdf_b64 = payload.get('pdf_base64') or payload.get('pdf')
    if pdf_b64:
        try:
            return base64.b64decode(pdf_b64)
        except Exception:
            return None
    return None


def _parse_pdf_statement(pdf_bytes: bytes) -> dict[str, Any]:
    text = ''
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(io.BytesIO(pdf_bytes)) or ''
    except Exception:
        try:
            text = pdf_bytes.decode('utf-8', errors='ignore')
        except Exception:
            text = ''
    lines: list[dict[str, Any]] = []
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    pattern = re.compile(r'(20\d{2}-\d{2}-\d{2})\s+(.+?)\s+(-?\d+[\.,]\d{2})')
    for match in pattern.finditer(text):
        tx_date, merchant, amount = match.groups()
        amount_val = float(amount.replace(',', '.'))
        lines.append(
            {
                "transaction_date": tx_date,
                "merchant_name": merchant.strip(),
                "amount": amount_val,
                "description": merchant.strip(),
            }
        )
    period_match = re.search(r'Period\s*:?\s*(20\d{2}-\d{2}-\d{2})\s*(?:to|-)\s*(20\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
    if period_match:
        period_start, period_end = period_match.groups()
    return {
        "period_start": period_start,
        "period_end": period_end,
        "lines": lines,
        "raw_text": text,
    }



@recon_bp.post("/reconciliation/firstcard/import")
def firstcard_import() -> Any:
    """Import a company card statement into invoice_documents/invoice_lines.

    Accepts JSON payload of shape:
      {
        "period_start": "YYYY-MM-DD", "period_end": "YYYY-MM-DD",
        "lines": [
          {"transaction_date": "YYYY-MM-DD", "amount": 123.45, "merchant_name": "Shop", "description": "..."}, ...
        ]
      }
    Returns: { id: <document_id>, lines: <count> }
    """
    payload = request.get_json(silent=True) or {}
    doc_id = payload.get("document_id") or str(uuid.uuid4())
    period_start = payload.get("period_start")
    period_end = payload.get("period_end")
    lines = payload.get("lines") or []
    pdf_bytes = _decode_pdf_payload(payload)
    if not lines and pdf_bytes:
        parsed = _parse_pdf_statement(pdf_bytes)
        lines = parsed.get("lines") or []
        period_start = period_start or parsed.get("period_start")
        period_end = period_end or parsed.get("period_end")
    inserted = 0
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                # Create invoice document (company card)
                cur.execute(
                    (
                        "INSERT INTO invoice_documents (id, invoice_type, period_start, period_end, status) "
                        "VALUES (%s, %s, %s, %s, 'imported')"
                    ),
                    (doc_id, "company_card", period_start, period_end),
                )
                # Insert lines if provided
                if isinstance(lines, list) and lines:
                    for ln in lines:
                        cur.execute(
                            (
                                "INSERT INTO invoice_lines (invoice_id, transaction_date, amount, merchant_name, description) "
                                "VALUES (%s, %s, %s, %s, %s)"
                            ),
                            (
                                doc_id,
                                ln.get("transaction_date"),
                                ln.get("amount"),
                                (ln.get("merchant_name") or ln.get("merchant") or None),
                                ln.get("description"),
                            ),
                        )
                        inserted += 1
        except Exception:
            pass
    return jsonify({"status": "ok", "id": doc_id, "lines": inserted}), 200


@recon_bp.post("/reconciliation/firstcard/match")
def firstcard_match() -> Any:
    """Naive matching of invoice_lines to receipts in unified_files.

    Input JSON: { "document_id": "..." }
    Strategy: for each line without a match, find a unified_files row where
      DATE(purchase_datetime) == transaction_date and |gross_amount - amount| < 0.01
    Updates invoice_lines.matched_file_id/match_score/match_status and inserts invoice_line_history.
    """
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id") or payload.get("doc_id") or payload.get("file_id")
    matched = 0
    if not document_id or db_cursor is None:
        return jsonify({"matched": matched}), 200

    try:
        with db_cursor() as cur:
            # Fetch candidate lines
            cur.execute(
                (
                    "SELECT id, transaction_date, amount FROM invoice_lines "
                    "WHERE invoice_id=%s AND matched_file_id IS NULL"
                ),
                (document_id,),
            )
            lines = cur.fetchall() or []

        for line_id, tx_date, amount in lines:
            file_id = None
            try:
                with db_cursor() as cur:
                    cur.execute(
                        (
                            "SELECT id FROM unified_files "
                            "WHERE purchase_datetime IS NOT NULL "
                            "AND DATE(purchase_datetime)=%s "
                            "AND gross_amount IS NOT NULL "
                            "AND ABS(gross_amount - %s) < 0.01 "
                            "ORDER BY created_at DESC LIMIT 1"
                        ),
                        (tx_date, amount),
                    )
                    row = cur.fetchone()
                    if row:
                        (file_id,) = row
                        cur.execute(
                            (
                                "UPDATE invoice_lines SET matched_file_id=%s, match_score=%s, match_status='auto' WHERE id=%s"
                            ),
                            (file_id, 0.8, line_id),
                        )
                        cur.execute(
                            (
                                "INSERT INTO invoice_line_history (invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                                "VALUES (%s, 'matched', 'system', NULL, %s, 'auto-match')"
                            ),
                            (line_id, file_id),
                        )
                        matched += 1
                        record_invoice_decision("matched")
            except Exception:
                continue

        # If any matched, bump document status
        if matched > 0:
            try:
                with db_cursor() as cur:
                    cur.execute(
                        "UPDATE invoice_documents SET status='matched' WHERE id=%s AND status='imported'",
                        (document_id,),
                    )
            except Exception:
                pass
    except Exception:
        pass
    return jsonify({"matched": matched, "document_id": document_id}), 200


@recon_bp.get("/reconciliation/firstcard/statements")
def list_statements() -> Any:
    items: list[dict[str, Any]] = []
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT id, uploaded_at, status FROM invoice_documents "
                        "WHERE invoice_type='company_card' ORDER BY uploaded_at DESC LIMIT 100"
                    )
                )
                for sid, uploaded_at, status in cur.fetchall():
                    items.append(
                        {
                            "id": sid,
                            "uploaded_at": str(uploaded_at),
                            "created_at": str(uploaded_at),
                            "status": status,
                        }
                    )
        except Exception:
            items = []
    return jsonify({"items": items, "total": len(items)}), 200


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/confirm")
def confirm_statement(sid: str) -> Any:
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE invoice_documents SET status='completed' WHERE id=%s",
                    (sid,),
                )
        except Exception:
            pass
    return jsonify({"id": sid, "status": "confirmed"}), 200


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/reject")
def reject_statement(sid: str) -> Any:
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE invoice_documents SET status='imported' WHERE id=%s",
                    (sid,),
                )
        except Exception:
            pass
    return jsonify({"id": sid, "status": "rejected"}), 200


@recon_bp.put("/reconciliation/firstcard/lines/<int:line_id>")
def update_line_match(line_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    new_file_id = payload.get("matched_file_id") or payload.get("file_id")
    if not new_file_id or db_cursor is None:
        return jsonify({"ok": False}), 400
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE invoice_lines SET matched_file_id=%s, match_status='manual' WHERE id=%s",
                (new_file_id, line_id),
            )
            cur.execute(
                (
                    "INSERT INTO invoice_line_history (invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                    "VALUES (%s, 'matched', 'admin', NULL, %s, 'manual-edit')"
                ),
                (line_id, new_file_id),
            )
        record_invoice_decision("matched")
        return jsonify({"ok": True}), 200
    except Exception:
        return jsonify({"ok": False}), 500


@recon_bp.get("/reconciliation/firstcard/statements/<sid>/lines")
def list_statement_lines(sid: str) -> Any:
    items: list[dict[str, Any]] = []
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT id, transaction_date, amount, merchant_name, description, matched_file_id, match_status "
                        "FROM invoice_lines WHERE invoice_id=%s ORDER BY transaction_date ASC, id ASC"
                    ),
                    (sid,),
                )
                for (lid, tx, amt, mname, desc, mid, mstatus) in cur.fetchall() or []:
                    items.append(
                        {
                            "id": int(lid),
                            "transaction_date": (tx.isoformat() if hasattr(tx, "isoformat") else tx),
                            "amount": float(amt) if amt is not None else None,
                            "merchant_name": mname,
                            "description": desc,
                            "matched_file_id": mid,
                            "match_status": mstatus,
                        }
                    )
        except Exception:
            items = []
    return jsonify({"items": items, "total": len(items)}), 200