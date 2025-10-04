from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid
import base64
import io
import os
import json
import re
import hashlib

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from api.ingest import (  # type: ignore
    DuplicateFileError,
    _hash_exists,
    _insert_unified_file,
    _update_other_data,
)
from services.file_detection import detect_file
from services.pdf_conversion import pdf_to_png_pages
from services.storage import FileStorage
try:
    from observability.metrics import record_invoice_decision  # type: ignore
except Exception:  # pragma: no cover
    def record_invoice_decision(_d: str) -> None:  # type: ignore
        return None

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

try:
    from services.tasks import process_ocr
except Exception:  # pragma: no cover
    process_ocr = None  # type: ignore
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_line_status_and_link,
    transition_processing_status,
)


recon_bp = Blueprint("reconciliation_firstcard", __name__)


_OCR_COMPLETE_STATUSES = {
    "ocr_done",
    "document_processed",
    "ready_for_matching",
    "matching_completed",
    "completed",
}


def _storage() -> FileStorage:
    base_dir = os.getenv("STORAGE_DIR", "/data/storage")
    return FileStorage(base_dir)


def _queue_ocr(file_id: str) -> None:
    if not file_id:
        return
    if process_ocr is None:  # pragma: no cover - optional runtime dependency
        return
    try:
        if hasattr(process_ocr, "delay"):
            process_ocr.delay(file_id)  # type: ignore[attr-defined]
        else:
            process_ocr(file_id)  # type: ignore[misc]
    except Exception:
        # Queueing is best-effort – failures should not block uploads.
        return


def _create_invoice_document(
    *,
    invoice_id: str,
    invoice_type: str,
    status: str,
    metadata: dict[str, Any],
) -> None:
    if db_cursor is None:  # pragma: no cover - database optional in tests
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO invoice_documents "
                    "(id, invoice_type, status, metadata_json) "
                    "VALUES (%s, %s, %s, %s)"
                ),
                (invoice_id, invoice_type, status, json.dumps(metadata)),
            )
    except Exception:
        # Allow idempotent re-uploads to update metadata.
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "UPDATE invoice_documents "
                        "SET status=%s, metadata_json=%s WHERE id=%s"
                    ),
                    (status, json.dumps(metadata), invoice_id),
                )
        except Exception:
            pass


def _load_invoice_document(invoice_id: str) -> Optional[tuple[str, dict[str, Any]]]:
    if db_cursor is None:  # pragma: no cover
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT status, metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            status, metadata_json = row
            metadata: dict[str, Any]
            if metadata_json:
                try:
                    metadata = json.loads(metadata_json)
                except Exception:
                    metadata = {}
            else:
                metadata = {}
            return status, metadata
    except Exception:
        return None


def _list_invoice_files(invoice_id: str) -> list[dict[str, Any]]:
    if db_cursor is None:  # pragma: no cover
        return []
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, file_type, ai_status, other_data, ocr_raw "
                    "FROM unified_files "
                    "WHERE id=%s OR original_file_id=%s "
                    "ORDER BY created_at ASC"
                ),
                (invoice_id, invoice_id),
            )
            records = []
            for fid, file_type, ai_status, other_data, ocr_raw in cur.fetchall() or []:
                payload: dict[str, Any]
                if other_data:
                    try:
                        payload = json.loads(other_data)
                    except Exception:
                        payload = {}
                else:
                    payload = {}
                records.append(
                    {
                        "id": fid,
                        "file_type": file_type,
                        "ai_status": ai_status,
                        "other_data": payload,
                        "ocr_raw": ocr_raw,
                    }
                )
            return records
    except Exception:
        return []


def _count_invoice_lines(invoice_id: str) -> tuple[int, int]:
    if db_cursor is None:  # pragma: no cover
        return (0, 0)
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT COUNT(1), "
                    "SUM(CASE WHEN match_status IN ('auto','manual') THEN 1 ELSE 0 END) "
                    "FROM invoice_lines WHERE invoice_id=%s"
                ),
                (invoice_id,),
            )
            row = cur.fetchone()
            if not row:
                return (0, 0)
            total, matched = row
            return int(total or 0), int(matched or 0)
    except Exception:
        return (0, 0)


@recon_bp.post("/reconciliation/firstcard/upload-invoice")
def upload_invoice() -> Any:
    """Upload a FirstCard invoice (PDF or image) and enqueue OCR."""

    file = request.files.get("invoice") or request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "missing_file"}), 400

    data = file.read()
    if not data:
        return jsonify({"error": "empty_file"}), 400

    file_hash = hashlib.sha256(data).hexdigest()
    if _hash_exists(file_hash):
        return jsonify({"error": "duplicate_file"}), 409

    safe_name = secure_filename(file.filename) or f"invoice_{uuid.uuid4()}"
    detection = detect_file(data, safe_name)
    invoice_id = str(uuid.uuid4())
    submitted_by = request.headers.get("X-User") or "invoice_upload"
    fs = _storage()

    metadata: dict[str, Any] = {
        "source_file_id": invoice_id,
        "processing_status": "ocr_pending",
        "submitted_by": submitted_by,
        "original_filename": safe_name,
        "detected_kind": detection.kind,
    }

    page_refs: list[dict[str, Any]] = []

    try:
        if detection.kind == "pdf":
            pages = pdf_to_png_pages(data, fs.base / "invoices", invoice_id, dpi=300)
            if not pages:
                return jsonify({"error": "empty_pdf"}), 400

            _insert_unified_file(
                file_id=invoice_id,
                file_type="invoice",
                content_hash=file_hash,
                submitted_by=submitted_by,
                original_filename=safe_name,
                ai_status="uploaded",
                mime_type="application/pdf",
                file_suffix=os.path.splitext(safe_name)[1] or ".pdf",
                original_file_id=invoice_id,
                original_file_name=safe_name,
                original_file_size=len(data),
                other_data={
                    "detected_kind": "pdf",
                    "page_count": len(pages),
                    "source": "invoice_upload",
                },
            )
            fs.save_original(invoice_id, safe_name, data)

            for page in pages:
                page_id = str(uuid.uuid4())
                page_number = int(getattr(page, "index", 0)) + 1
                page_hash = hashlib.sha256(page.bytes).hexdigest()
                stored_name = f"page-{page_number:04d}.png"
                _insert_unified_file(
                    file_id=page_id,
                    file_type="invoice_page",
                    content_hash=page_hash,
                    submitted_by=submitted_by,
                    original_filename=f"{safe_name}-page-{page_number:04d}.png",
                    ai_status="uploaded",
                    mime_type="image/png",
                    file_suffix=".png",
                    original_file_id=invoice_id,
                    original_file_name=safe_name,
                    original_file_size=len(page.bytes),
                    other_data={
                        "detected_kind": "pdf_page",
                        "page_number": page_number,
                        "source_invoice": invoice_id,
                        "source": "invoice_upload",
                    },
                )
                fs.save(page_id, stored_name, page.bytes)
                _queue_ocr(page_id)
                page_refs.append({"file_id": page_id, "page_number": page_number})

            _update_other_data(
                invoice_id,
                {
                    "detected_kind": "pdf",
                    "page_count": len(page_refs),
                    "pages": page_refs,
                    "source": "invoice_upload",
                },
            )

        elif detection.kind == "image":
            _insert_unified_file(
                file_id=invoice_id,
                file_type="invoice",
                content_hash=file_hash,
                submitted_by=submitted_by,
                original_filename=safe_name,
                ai_status="uploaded",
                mime_type=detection.mime_type or "image/octet-stream",
                file_suffix=os.path.splitext(safe_name)[1] or ".png",
                original_file_id=invoice_id,
                original_file_name=safe_name,
                original_file_size=len(data),
                other_data={
                    "detected_kind": "image",
                    "source": "invoice_upload",
                },
            )
            fs.save_original(invoice_id, safe_name, data)
            _queue_ocr(invoice_id)
            page_refs.append({"file_id": invoice_id, "page_number": 1})
        else:
            return jsonify({"error": "unsupported_file_type"}), 400

    except DuplicateFileError:
        return jsonify({"error": "duplicate_file"}), 409
    except Exception as exc:
        return jsonify({"error": "upload_failed", "details": str(exc)}), 500

    metadata["page_ids"] = [ref["file_id"] for ref in page_refs]
    metadata["page_count"] = len(page_refs)

    _create_invoice_document(
        invoice_id=invoice_id,
        invoice_type="credit_card_invoice",
        status="processing",
        metadata=metadata,
    )

    response = {
        "invoice_id": invoice_id,
        "status": "processing",
        "processing_status": metadata["processing_status"],
        "page_count": len(page_refs),
        "page_ids": metadata["page_ids"],
    }
    return jsonify(response), 201


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/status")
def invoice_status(invoice_id: str) -> Any:
    """Return processing status, OCR progress, and match stats for an invoice."""

    doc = _load_invoice_document(invoice_id)
    if not doc:
        return jsonify({"error": "not_found"}), 404

    status, metadata = doc
    source_file_id = metadata.get("source_file_id") or invoice_id
    files = _list_invoice_files(source_file_id)

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

    total_lines, matched_lines = _count_invoice_lines(invoice_id)

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
    }

    return jsonify(response), 200


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

    total = 0
    matched = 0
    items: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(1), "
                "SUM(CASE WHEN match_status IN ('auto','manual') THEN 1 ELSE 0 END) "
                "FROM invoice_lines WHERE invoice_id=%s",
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
                                "INSERT INTO invoice_lines (invoice_id, transaction_date, amount, merchant_name, description, match_status) "
                                "VALUES (%s, %s, %s, %s, %s, %s)"
                            ),
                            (
                                doc_id,
                                ln.get("transaction_date"),
                                ln.get("amount"),
                                (ln.get("merchant_name") or ln.get("merchant") or None),
                                ln.get("description"),
                                InvoiceLineMatchStatus.PENDING.value,
                            ),
                        )
                        inserted += 1
            transition_processing_status(
                doc_id,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                (
                    InvoiceProcessingStatus.UPLOADED,
                    InvoiceProcessingStatus.OCR_DONE,
                    InvoiceProcessingStatus.OCR_PENDING,
                ),
            )
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
    total_lines = 0
    if not document_id or db_cursor is None:
        return jsonify({"matched": matched}), 200

    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM invoice_lines WHERE invoice_id=%s",
                (document_id,),
            )
            total_row = cur.fetchone()
            if total_row:
                total_lines = int(total_row[0] or 0)
            cur.execute(
                (
                    "SELECT id, transaction_date, amount FROM invoice_lines "
                    "WHERE invoice_id=%s AND (match_status IS NULL OR match_status IN ('pending','unmatched'))"
                ),
                (document_id,),
            )
            lines = cur.fetchall() or []

        transition_document_status(
            document_id,
            InvoiceDocumentStatus.MATCHING,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )

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
            except Exception:
                file_id = None

            if not file_id:
                continue

            updated = transition_line_status_and_link(
                line_id,
                file_id,
                0.8,
                InvoiceLineMatchStatus.AUTO,
                (
                    InvoiceLineMatchStatus.PENDING,
                    InvoiceLineMatchStatus.UNMATCHED,
                ),
            )
            if not updated:
                continue
            matched += 1
            try:
                with db_cursor() as cur:
                    cur.execute(
                        (
                            "INSERT INTO invoice_line_history (invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                            "VALUES (%s, 'matched', 'system', NULL, %s, 'auto-match')"
                        ),
                        (line_id, file_id),
                    )
            except Exception:
                pass
            record_invoice_decision("matched")

        # Refresh counts for status transitions
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT COUNT(*), SUM(CASE WHEN match_status IN ('auto','manual','confirmed') THEN 1 ELSE 0 END) "
                    "FROM invoice_lines WHERE invoice_id=%s"
                ),
                (document_id,),
            )
            row = cur.fetchone()
            if row:
                total_lines = int(row[0] or total_lines)
                matched_lines = int(row[1] or 0)
            else:
                matched_lines = matched

        transition_processing_status(
            document_id,
            InvoiceProcessingStatus.MATCHING_COMPLETED,
            (
                InvoiceProcessingStatus.READY_FOR_MATCHING,
                InvoiceProcessingStatus.AI_PROCESSING,
            ),
        )

        if matched_lines == 0:
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.IMPORTED,
                (
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.IMPORTED,
                ),
            )
        elif total_lines and matched_lines < total_lines:
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.MATCHED,
                ),
            )
        else:
            transition_document_status(
                document_id,
                InvoiceDocumentStatus.MATCHED,
                (
                    InvoiceDocumentStatus.IMPORTED,
                    InvoiceDocumentStatus.MATCHING,
                    InvoiceDocumentStatus.PARTIALLY_MATCHED,
                ),
            )
    except Exception:
        matched = 0
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
    transition_processing_status(
        sid,
        InvoiceProcessingStatus.COMPLETED,
        (
            InvoiceProcessingStatus.MATCHING_COMPLETED,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
        ),
    )
    transition_document_status(
        sid,
        InvoiceDocumentStatus.COMPLETED,
        (
            InvoiceDocumentStatus.MATCHED,
            InvoiceDocumentStatus.PARTIALLY_MATCHED,
        ),
    )
    return jsonify({"id": sid, "status": "confirmed"}), 200


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/reject")
def reject_statement(sid: str) -> Any:
    transition_processing_status(
        sid,
        InvoiceProcessingStatus.READY_FOR_MATCHING,
        (
            InvoiceProcessingStatus.MATCHING_COMPLETED,
            InvoiceProcessingStatus.COMPLETED,
        ),
    )
    transition_document_status(
        sid,
        InvoiceDocumentStatus.IMPORTED,
        (
            InvoiceDocumentStatus.MATCHED,
            InvoiceDocumentStatus.PARTIALLY_MATCHED,
            InvoiceDocumentStatus.COMPLETED,
        ),
    )
    return jsonify({"id": sid, "status": "rejected"}), 200


@recon_bp.put("/reconciliation/firstcard/lines/<int:line_id>")
def update_line_match(line_id: int) -> Any:
    payload = request.get_json(silent=True) or {}
    new_file_id = payload.get("matched_file_id") or payload.get("file_id")
    if not new_file_id or db_cursor is None:
        return jsonify({"ok": False}), 400
    try:
        updated = transition_line_status_and_link(
            line_id,
            new_file_id,
            None,
            InvoiceLineMatchStatus.MANUAL,
            (
                InvoiceLineMatchStatus.AUTO,
                InvoiceLineMatchStatus.PENDING,
                InvoiceLineMatchStatus.UNMATCHED,
            ),
        )
        if not updated:
            return jsonify({"ok": False, "reason": "conflict"}), 409
        with db_cursor() as cur:
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