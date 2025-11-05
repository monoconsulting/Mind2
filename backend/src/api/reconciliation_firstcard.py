from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal
import uuid
import base64
import io
import os
import json
import hashlib

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.tasks import dispatch_workflow, auto_match_invoice_lines, refresh_invoice_match_state
from services.file_detection import detect_file
from services.pdf_conversion import pdf_to_png_pages
from services.storage import FileStorage
from services.invoice_parser import parse_credit_card_statement
from services.db.files import insert_unified_file, DuplicateFileError
from services.validation import _as_decimal
from api.ai_processing import _persist_credit_card_match
from services.workflow_runs import create_workflow_run
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


from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_line_status_and_link,
    transition_processing_status,
)


recon_bp = Blueprint("reconciliation_firstcard", __name__)
logger = logging.getLogger(__name__)

# OCR status constants
_OCR_COMPLETE_STATUSES = {"ocr_done", "completed", "processed", "ready", "ai_done"}


# Helper functions
def _storage() -> FileStorage:
    """Return FileStorage instance."""
    base = os.getenv("STORAGE_DIR", "/data/storage")
    return FileStorage(base)


def _as_date(val: Any) -> Optional[date]:
    """Convert value to date object."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).date()
        except Exception:
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except Exception:
                pass
    return None


def _count_invoice_lines(invoice_id: str) -> tuple[int, int]:
    """Count total and matched invoice lines.
    
    Returns:
        (total_lines, matched_lines)
    """
    if db_cursor is None:
        return (0, 0)
    
    # First try creditcard_invoice_items table
    try:
        with db_cursor() as cur:
            # Get main_id from metadata
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                try:
                    metadata = json.loads(row[0])
                    main_id = metadata.get("creditcard_main_id")
                    if main_id:
                        cur.execute(
                            "SELECT COUNT(*), SUM(CASE WHEN matched >= 1 THEN 1 ELSE 0 END) "
                            "FROM creditcard_invoice_items WHERE main_id=%s",
                            (main_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            return (int(row[0] or 0), int(row[1] or 0))
                except Exception:
                    pass
    except Exception:
        pass
    
    # Fallback to invoice_lines table
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), "
                "SUM(CASE WHEN match_status IN ('auto','manual','confirmed') THEN 1 ELSE 0 END) "
                "FROM invoice_lines WHERE invoice_id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
            if row:
                return (int(row[0] or 0), int(row[1] or 0))
    except Exception:
        pass
    
    return (0, 0)


def _load_invoice_document(invoice_id: str) -> Optional[tuple[str, dict[str, Any]]]:
    """Load invoice document status and metadata.
    
    Returns:
        (status, metadata) or None if not found
    """
    if db_cursor is None:
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
            
            status = row[0]
            metadata_raw = row[1]
            metadata: dict[str, Any] = {}
            
            if metadata_raw:
                try:
                    if isinstance(metadata_raw, (bytes, bytearray)):
                        metadata_raw = metadata_raw.decode("utf-8")
                    metadata = json.loads(metadata_raw)
                except Exception:
                    metadata = {}
            
            return (status, metadata)
    except Exception:
        return None


def _list_invoice_files(source_file_id: str) -> list[dict[str, Any]]:
    """List all files related to an invoice."""
    if db_cursor is None:
        return []
    
    files: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, file_type, ai_status, ocr_raw, other_data, created_at
                FROM unified_files
                WHERE id = %s OR original_file_id = %s
                ORDER BY created_at ASC
                """,
                (source_file_id, source_file_id),
            )
            for row in cur.fetchall() or []:
                file_id, file_type, ai_status, ocr_raw, other_json, created_at = row
                other_data: dict[str, Any] = {}
                if other_json:
                    try:
                        other_data = json.loads(other_json)
                    except Exception:
                        other_data = {}
                
                files.append({
                    "id": file_id,
                    "file_type": file_type,
                    "ai_status": ai_status,
                    "ocr_raw": ocr_raw,
                    "other_data": other_data,
                    "created_at": created_at,
                })
    except Exception:
        pass
    
    return files


def _create_invoice_document(
    invoice_id: str,
    invoice_type: str,
    status: str,
    metadata: dict[str, Any],
    processing_status: Optional[str] = None,
) -> bool:
    """Create or update invoice document record."""
    if db_cursor is None:
        return False
    
    try:
        with db_cursor() as cur:
            # Check if exists
            cur.execute(
                "SELECT id FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            exists = cur.fetchone() is not None
            
            metadata_json = json.dumps(metadata or {})
            
            if exists:
                # Update existing
                cur.execute(
                    """
                    UPDATE invoice_documents
                    SET invoice_type=%s,
                        status=%s,
                        processing_status=COALESCE(%s, processing_status),
                        metadata_json=%s
                    WHERE id=%s
                    """,
                    (
                        invoice_type,
                        status,
                        processing_status,
                        metadata_json,
                        invoice_id,
                    ),
                )
            else:
                # Insert new
                cur.execute(
                    """
                    INSERT INTO invoice_documents
                    (id, invoice_type, status, processing_status, metadata_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        invoice_type,
                        status,
                        processing_status or InvoiceProcessingStatus.UPLOADED.value,
                        metadata_json,
                    ),
                )
        return True
    except Exception as e:
        logger.error(f"Failed to create/update invoice document: {e}")
        return False


def _write_invoice_metadata(invoice_id: str, metadata: dict[str, Any]) -> bool:
    """Write metadata to invoice document."""
    if db_cursor is None:
        return False
    
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE invoice_documents SET metadata_json=%s WHERE id=%s",
                (json.dumps(metadata or {}), invoice_id),
            )
        return True
    except Exception as e:
        logger.error(f"Failed to write invoice metadata: {e}")
        return False


def _create_workflow_run(
    workflow_key: str,
    source_channel: str,
    file_id: str,
    content_hash: str,
) -> Optional[int]:
    """Create workflow run and return ID."""
    run_id = create_workflow_run(
        workflow_key=workflow_key,
        source_channel=source_channel,
        file_id=file_id,
        content_hash=content_hash,
    )

    if run_id is None or db_cursor is None:
        return run_id

    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE workflow_runs SET current_stage=%s WHERE id=%s",
                ("init", run_id),
            )
    except Exception as exc:
        logger.warning(
            "Failed to set initial workflow stage for run %s (%s)",
            run_id,
            exc,
        )
    return run_id


def _find_file_id_by_hash(file_hash: str) -> Optional[str]:
    """Find existing file by content hash."""
    if db_cursor is None:
        return None
    
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT id FROM unified_files WHERE content_hash=%s ORDER BY created_at DESC LIMIT 1",
                (file_hash,),
            )
            row = cur.fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass
    
    return None


def _find_invoice_id_for_main(main_id: int) -> Optional[str]:
    """Find invoice_document.id from creditcard_invoices_main.id."""
    if db_cursor is None:
        return None
    
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id FROM invoice_documents
                WHERE metadata_json LIKE CONCAT('%%"creditcard_main_id":', %s, '%%')
                LIMIT 1
                """,
                (main_id,),
            )
            row = cur.fetchone()
            if row:
                return str(row[0])
    except Exception:
        pass
    
    return None


def _find_invoice_line_id_for_item(
    item_id: int,
    invoice_id: Optional[str] = None,
) -> Optional[int]:
    """Best-effort lookup of invoice_lines.id matching a creditcard invoice item."""
    if db_cursor is None:
        return None

    item_row = None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT main_id,
                       purchase_date,
                       amount_original,
                       amount_sek,
                       gross_amount,
                       description,
                       merchant_name
                  FROM creditcard_invoice_items
                 WHERE id=%s
                """,
                (item_id,),
            )
            item_row = cur.fetchone()
    except Exception:
        return None

    if not item_row:
        return None

    (
        main_id,
        purchase_date,
        amount_original,
        amount_sek,
        gross_amount,
        description,
        merchant_name,
    ) = item_row

    target_invoice_id = invoice_id
    if not target_invoice_id:
        target_invoice_id = _find_invoice_id_for_main(int(main_id or 0))
    if not target_invoice_id:
        return None

    target_amount: Optional[Decimal] = None
    for candidate in (amount_sek, gross_amount, amount_original):
        decimal_candidate = _as_decimal(candidate)
        if decimal_candidate is not None:
            target_amount = decimal_candidate
            break
    amount_for_order = target_amount if target_amount is not None else Decimal("0")
    date_value = _as_date(purchase_date)
    merchant_hint = (merchant_name or description or "").strip()

    try:
        with db_cursor() as cur:
            params: list[Any] = [target_invoice_id]
            query = [
                "SELECT id",
                "  FROM invoice_lines",
                " WHERE invoice_id=%s",
                "   AND (match_status IS NULL OR match_status IN ('pending','unmatched','auto'))",
            ]
            if merchant_hint:
                query.append(" ORDER BY ")
                query.append(
                    "CASE WHEN merchant_name = %s THEN 0 ELSE 1 END,"
                )
                params.append(merchant_hint)
            else:
                query.append(" ORDER BY ")

            if date_value is not None:
                query.append("CASE WHEN transaction_date = %s THEN 0 ELSE 1 END,")
                params.append(date_value)
            else:
                query.append("0,")

            query.append(
                "ABS(IFNULL(amount, 0) - %s), id ASC LIMIT 1"
            )
            params.append(amount_for_order)
            cur.execute("".join(query), tuple(params))
            row = cur.fetchone()
            if row:
                return int(row[0])
    except Exception:
        return None

    return None


def _ensure_processing_state(invoice_id: str) -> None:
    """Initialise processing_status to 'uploaded' when missing."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                "UPDATE invoice_documents SET processing_status=%s WHERE id=%s AND processing_status IS NULL",
                (InvoiceProcessingStatus.UPLOADED.value, invoice_id),
            )
    except Exception:
        logger.warning("Failed to initialise processing status for invoice %s", invoice_id)


def _log_line_history(
    line_id: int,
    action: str,
    performed_by: str,
    *,
    old_file_id: Optional[str] = None,
    new_file_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> None:
    """Best-effort insert into invoice_line_history."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO invoice_line_history "
                    "(invoice_line_id, action, performed_by, old_matched_file_id, new_matched_file_id, reason) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                ),
                (line_id, action, performed_by, old_file_id, new_file_id, reason),
            )
    except Exception:
        logger.debug("Failed to write invoice line history for %s", line_id)




@recon_bp.post("/reconciliation/firstcard/upload-invoice")
def upload_invoice() -> Any:
    """Upload a FirstCard invoice (PDF or image) and dispatch a workflow."""

    file = request.files.get("invoice") or request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "missing_file"}), 400

    data = file.read()
    if not data:
        return jsonify({"error": "empty_file"}), 400

    safe_name = secure_filename(file.filename) or f"invoice_{uuid.uuid4()}"
    detection = detect_file(data, safe_name)
    invoice_id = str(uuid.uuid4())
    submitted_by = request.headers.get("X-User") or "invoice_upload"
    file_hash = hashlib.sha256(data).hexdigest()
    file_suffix = Path(safe_name).suffix

    mime_type = detection.mime_type or getattr(file, "mimetype", None)
    is_pdf = detection.kind == "pdf" or (mime_type == "application/pdf")
    unified_file_type = "cc_pdf" if is_pdf else "cc_image"

    other_data = {
        "detected_kind": detection.kind,
        "source": "kortmatchning_upload",
        "original_filename": safe_name,
        "workflow_type": "creditcard_invoice",
    }

    fs = _storage()

    try:
        insert_unified_file(
            file_id=invoice_id,
            file_type=unified_file_type,
            workflow_type="creditcard_invoice",
            content_hash=file_hash,
            submitted_by=submitted_by,
            original_filename=safe_name,
            ai_status="uploaded",
            mime_type=mime_type,
            file_suffix=file_suffix,
            original_file_id=invoice_id,
            original_file_name=safe_name,
            original_file_size=len(data),
            other_data=other_data,
        )
    except DuplicateFileError:
        existing_id = _find_file_id_by_hash(file_hash)
        return (
            jsonify(
                {
                    "error": "duplicate_invoice",
                    "invoice_id": existing_id,
                }
            ),
            409,
        )

    fs.save_original(invoice_id, safe_name, data)
    logger.info(
        "Stored FirstCard invoice %s with file_type=%s workflow_type=creditcard_invoice (detected_kind=%s, mime_type=%s)",
        invoice_id,
        unified_file_type,
        detection.kind,
        mime_type,
    )

    metadata: dict[str, Any] = {
        "source_file_id": invoice_id,
        "processing_status": InvoiceProcessingStatus.UPLOADED.value,
        "submitted_by": submitted_by,
        "original_filename": safe_name,
        "detected_kind": detection.kind,
        "mime_type": detection.mime_type,
    }

    _create_invoice_document(
        invoice_id=invoice_id,
        invoice_type="credit_card_invoice",
        status=InvoiceDocumentStatus.IMPORTED.value,
        metadata=metadata,
        processing_status=metadata.get("processing_status"),
    )

    workflow_run_id = _create_workflow_run(
        workflow_key="WF3_FIRSTCARD_INVOICE",
        source_channel="kortmatchning_upload",
        file_id=invoice_id,
        content_hash=file_hash,
    )

    if not workflow_run_id or not dispatch_workflow(workflow_run_id):
        logger.error(
            "Failed to dispatch WF3 workflow for invoice %s (run_id=%s)",
            invoice_id,
            workflow_run_id,
        )
        return jsonify({"error": "workflow_dispatch_failed"}), 500

    metadata["workflow_run_id"] = workflow_run_id
    _create_invoice_document(
        invoice_id=invoice_id,
        invoice_type="credit_card_invoice",
        status=InvoiceDocumentStatus.IMPORTED.value,
        metadata=metadata,
        processing_status=metadata.get("processing_status"),
    )

    response = {
        "invoice_id": invoice_id,
        "status": "processing",
        "processing_status": metadata["processing_status"],
        "workflow_run_id": workflow_run_id,
    }
    return jsonify(response), 201


@recon_bp.post("/reconciliation/firstcard/import")
def import_invoice() -> Any:
    """Import invoice lines from JSON payload (used for manual/admin flows)."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    payload = request.get_json(silent=True) or {}
    lines = payload.get("lines") or []
    if not isinstance(lines, list) or not lines:
        return jsonify({"error": "missing_lines"}), 400

    invoice_id = payload.get("id") or payload.get("invoice_id") or str(uuid.uuid4())
    period_start = payload.get("period_start")
    period_end = payload.get("period_end")

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO invoice_documents (id, invoice_type, period_start, period_end)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE period_start=VALUES(period_start), period_end=VALUES(period_end)
                """,
                (invoice_id, "credit_card_invoice", period_start, period_end),
            )
    except Exception as exc:
        logger.error("Failed to upsert invoice document %s: %s", invoice_id, exc)
        return jsonify({"error": "document_upsert_failed"}), 500

    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
    except Exception:
        logger.debug("Failed to clear previous invoice lines for %s", invoice_id)

    inserted = 0
    for entry in lines:
        if not isinstance(entry, dict):
            continue
        tx_date = entry.get("transaction_date") or entry.get("purchase_date")
        amount = entry.get("amount") or entry.get("amount_sek") or entry.get("gross_amount")
        merchant_name = entry.get("merchant_name") or entry.get("merchant") or entry.get("vendor") or ""
        description = entry.get("description") or entry.get("memo") or ""
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO invoice_lines
                    (invoice_id, transaction_date, amount, merchant_name, description, match_status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        tx_date,
                        amount,
                        merchant_name[:255],
                        description[:1024],
                        InvoiceLineMatchStatus.PENDING.value,
                    ),
                )
            inserted += 1
        except Exception:
            logger.debug("Failed to insert invoice line for %s", invoice_id)

    _ensure_processing_state(invoice_id)
    try:
        transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            (
                InvoiceProcessingStatus.UPLOADED,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
            ),
        )
    except Exception:
        logger.debug("Processing status transition failed for %s", invoice_id)

    try:
        transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.IMPORTED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
            ),
        )
    except Exception:
        logger.debug("Document status transition failed for %s", invoice_id)

    metadata: dict[str, Any] = {
        "period_start": period_start,
        "period_end": period_end,
        "line_counts": {
            "total": inserted,
            "matched": 0,
            "unmatched": inserted,
        },
    }
    _write_invoice_metadata(invoice_id, metadata)

    return jsonify({"id": invoice_id, "imported": inserted}), 200



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

    computed_total, computed_matched = _count_invoice_lines(invoice_id)
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
    card_details: Optional[dict[str, Any]] = None
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

            matched_receipt: Optional[dict[str, Any]] = None
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
                _as_decimal(amount_sek)
                or _as_decimal(gross_amount)
                or _as_decimal(amount_original)
                or _as_decimal(net_amount)
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


@recon_bp.get("/reconciliation/firstcard/invoices/<invoice_id>/log")
def invoice_log(invoice_id: str) -> Any:
    """Return detailed workflow and AI logs for a FirstCard invoice."""
    if db_cursor is None:  # pragma: no cover
        return jsonify(
            {
                "invoice_id": invoice_id,
                "workflow_runs": [],
                "ai_history": [],
                "files": [],
                "metadata": {},
            }
        ), 200

    metadata: dict[str, Any] = {}
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (invoice_id,),
            )
            row = cur.fetchone()
            if row and row[0]:
                try:
                    metadata = json.loads(row[0])
                except Exception:
                    metadata = {}
    except Exception:
        metadata = {}

    file_records: list[dict[str, Any]] = []
    related_file_ids: list[str] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    file_type,
                    workflow_type,
                    ai_status,
                    ai_confidence,
                    created_at,
                    updated_at,
                    ocr_raw,
                    other_data
                FROM unified_files
                WHERE id = %s OR original_file_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (invoice_id, invoice_id),
            )
            rows = cur.fetchall() or []
    except Exception:
        rows = []

    file_id_set: set[str] = set()
    for (
        file_id,
        file_type,
        workflow_type,
        ai_status,
        ai_confidence,
        created_at,
        updated_at,
        ocr_raw,
        other_json,
    ) in rows:
        other_payload: dict[str, Any]
        if other_json:
            try:
                other_payload = json.loads(other_json)
            except Exception:
                other_payload = {}
        else:
            other_payload = {}
        file_records.append(
            {
                "id": str(file_id),
                "file_type": file_type,
                "workflow_type": workflow_type,
                "ai_status": ai_status,
                "ai_confidence": float(ai_confidence) if ai_confidence is not None else None,
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
                "ocr_raw": ocr_raw or "",
                "ocr_raw_length": len(ocr_raw or ""),
                "other_data": other_payload,
            }
        )
        file_id_set.add(str(file_id))

    file_id_set.add(str(invoice_id))
    related_file_ids = list(sorted(file_id_set))

    workflow_runs: list[dict[str, Any]] = []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    workflow_key,
                    status,
                    current_stage,
                    source_channel,
                    created_at,
                    updated_at
                FROM workflow_runs
                WHERE file_id = %s
                ORDER BY created_at DESC, id DESC
                """,
                (invoice_id,),
            )
            run_rows = cur.fetchall() or []
    except Exception:
        run_rows = []

    for (
        workflow_run_id,
        workflow_key,
        status,
        current_stage,
        source_channel,
        created_at,
        updated_at,
    ) in run_rows:
        stages: list[dict[str, Any]] = []
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        stage_key,
                        status,
                        started_at,
                        finished_at,
                        message
                    FROM workflow_stage_runs
                    WHERE workflow_run_id = %s
                    ORDER BY
                        COALESCE(started_at, finished_at, NOW()) ASC,
                        id ASC
                    """,
                    (workflow_run_id,),
                )
                stage_rows = cur.fetchall() or []
        except Exception:
            stage_rows = []

        for (
            stage_key,
            stage_status,
            started_at,
            finished_at,
            message,
        ) in stage_rows:
            duration_ms: int | None = None
            if started_at and finished_at:
                try:
                    duration_ms = int((finished_at - started_at).total_seconds() * 1000)
                except Exception:
                    duration_ms = None
            stages.append(
                {
                    "stage_key": stage_key,
                    "status": stage_status,
                    "started_at": started_at.isoformat() if hasattr(started_at, "isoformat") else (str(started_at) if started_at else None),
                    "finished_at": finished_at.isoformat() if hasattr(finished_at, "isoformat") else (str(finished_at) if finished_at else None),
                    "duration_ms": duration_ms,
                    "message": message,
                }
            )

        workflow_runs.append(
            {
                "id": int(workflow_run_id),
                "workflow_key": workflow_key,
                "status": status,
                "current_stage": current_stage,
                "source_channel": source_channel,
                "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at),
                "stages": stages,
            }
        )

    ai_history: list[dict[str, Any]] = []
    if related_file_ids:
        placeholders = ", ".join(["%s"] * len(related_file_ids))
        query = f"""
            SELECT
                id,
                file_id,
                job_type,
                status,
                created_at,
                ai_stage_name,
                log_text,
                error_message,
                confidence,
                processing_time_ms,
                provider,
                model_name
            FROM ai_processing_history
            WHERE file_id IN ({placeholders})
            ORDER BY created_at ASC, id ASC
        """
        try:
            with db_cursor() as cur:
                cur.execute(query, tuple(related_file_ids))
                history_rows = cur.fetchall() or []
        except Exception:
            history_rows = []

        for (
            history_id,
            file_id,
            job_type,
            status,
            created_at,
            ai_stage_name,
            log_text,
            error_message,
            confidence,
            processing_time_ms,
            provider,
            model_name,
        ) in history_rows:
            ai_history.append(
                {
                    "id": int(history_id),
                    "file_id": file_id,
                    "job_type": job_type,
                    "status": status,
                    "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                    "ai_stage_name": ai_stage_name,
                    "log_text": log_text,
                    "error_message": error_message,
                    "confidence": float(confidence) if confidence is not None else None,
                    "processing_time_ms": processing_time_ms,
                    "provider": provider,
                    "model": model_name,
                }
            )

    payload = {
        "invoice_id": invoice_id,
        "workflow_runs": workflow_runs,
        "ai_history": ai_history,
        "files": file_records,
        "metadata": metadata,
    }
    return jsonify(payload), 200


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
                "SUM(CASE WHEN match_status IN ('auto','manual','confirmed') THEN 1 ELSE 0 END) "
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



@recon_bp.get("/reconciliation/firstcard/lines/<int:line_id>/candidates")
def line_candidates(line_id: int) -> Any:
    if db_cursor is None:  # pragma: no cover
        return jsonify({"line": None, "candidates": []}), 200

    invoice_id = request.args.get("invoice_id")

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT ci.id,
                       ci.main_id,
                       ci.purchase_date,
                       ci.amount_original,
                       ci.amount_sek,
                       ci.gross_amount,
                       ci.net_amount,
                       ci.currency_original,
                       ci.merchant_name,
                       ci.description,
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
                 WHERE ci.id = %s
                """,
                (line_id,),
            )
            item_row = cur.fetchone()
    except Exception:
        item_row = None

    if not item_row:
        return jsonify({"line": None, "candidates": []}), 200

    (
        item_id,
        main_id,
        purchase_date,
        amount_original,
        amount_sek,
        gross_amount,
        net_amount,
        currency_original,
        merchant_name,
        description,
        matched_flag,
        matched_receipt_id,
        matched_amount,
        matched_purchase_dt,
        matched_gross_amount,
        matched_credit_flag,
        matched_created_at,
        matched_vendor_name,
    ) = item_row

    match_value = int(matched_flag or 0)
    match_status_token = "pending"
    if match_value == 2:
        match_status_token = "manual"
    elif match_value >= 1:
        match_status_token = "auto"

    matched_receipt_payload: Optional[dict[str, Any]] = None
    if matched_receipt_id:
        matched_receipt_payload = {
            "file_id": matched_receipt_id,
            "purchase_datetime": matched_purchase_dt.isoformat() if hasattr(matched_purchase_dt, "isoformat") else matched_purchase_dt,
            "gross_amount": float(matched_gross_amount) if matched_gross_amount is not None else None,
            "credit_card_match": bool(matched_credit_flag) if matched_credit_flag is not None else False,
            "vendor_name": matched_vendor_name,
            "matched_amount": float(matched_amount) if matched_amount is not None else None,
        }

    display_amount = (
        _as_decimal(amount_sek)
        or _as_decimal(gross_amount)
        or _as_decimal(amount_original)
        or _as_decimal(net_amount)
    )

    line_payload = {
        "id": int(item_id),
        "invoice_id": invoice_id,
        "transaction_date": purchase_date.isoformat() if hasattr(purchase_date, "isoformat") else purchase_date,
        "amount": float(display_amount) if display_amount is not None else None,
        "currency": currency_original,
        "description": description or merchant_name or "",
        "match_status": match_status_token,
        "matched_file_id": matched_receipt_id,
        "matched_receipt": matched_receipt_payload,
    }

    target_date = _as_date(purchase_date)
    target_amount = display_amount

    candidates: list[dict[str, Any]] = []
    try:
        clauses = [
            "SELECT uf.id,",
            "       uf.purchase_datetime,",
            "       uf.gross_amount,",
            "       uf.credit_card_match,",
            "       uf.created_at,",
            "       c.name",
            "  FROM unified_files AS uf",
            " LEFT JOIN creditcard_receipt_matches AS crm ON crm.receipt_id = uf.id",
            " LEFT JOIN companies AS c ON c.id = uf.company_id",
            " WHERE uf.purchase_datetime IS NOT NULL",
            "   AND uf.gross_amount IS NOT NULL",
            "   AND (crm.invoice_item_id IS NULL OR crm.invoice_item_id = %s)",
        ]
        params: list[Any] = [line_id]
        if target_date is not None:
            clauses.append("   AND ABS(DATEDIFF(DATE(uf.purchase_datetime), %s)) <= 7")
            params.append(target_date)
        if target_amount is not None:
            clauses.append("   AND ABS(uf.gross_amount - %s) <= 200")
            params.append(target_amount)
        clauses.append(
            " ORDER BY ABS(uf.gross_amount - %s), ABS(DATEDIFF(DATE(uf.purchase_datetime), %s)), uf.created_at DESC LIMIT 50"
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
        purchase_dt,
        gross_amount_value,
        credit_flag,
        created_at,
        vendor_name,
    ) in candidate_rows:
        receipt_amount = _as_decimal(gross_amount_value)
        amount_diff = None
        if target_amount is not None and receipt_amount is not None:
            amount_diff = abs(Decimal(str(target_amount)) - receipt_amount)
        date_diff = None
        candidate_date = _as_date(purchase_dt)
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
            {
                "file_id": receipt_id,
                "purchase_datetime": purchase_dt.isoformat() if hasattr(purchase_dt, "isoformat") else purchase_dt,
                "gross_amount": float(receipt_amount) if receipt_amount is not None else None,
                "vendor_name": vendor_name,
                "credit_card_match": bool(credit_flag) if credit_flag is not None else False,
                "amount_difference": float(amount_diff) if amount_diff is not None else None,
                "date_difference_days": date_diff,
                "match_score": float(score),
                "is_current_match": receipt_id == matched_receipt_id,
            }
        )

    if matched_receipt_payload and not any(c["is_current_match"] for c in candidates):
        candidates.insert(
            0,
            {
                "file_id": matched_receipt_id,
                "purchase_datetime": matched_purchase_dt.isoformat() if hasattr(matched_purchase_dt, "isoformat") else matched_purchase_dt,
                "gross_amount": matched_receipt_payload.get("gross_amount"),
                "vendor_name": matched_vendor_name,
                "credit_card_match": bool(matched_credit_flag) if matched_credit_flag is not None else False,
                "amount_difference": 0.0,
                "date_difference_days": 0,
                "match_score": 1.0,
                "is_current_match": True,
            },
        )

    candidates.sort(
        key=lambda entry: (
            entry.get("is_current_match") is not True,
            entry.get("amount_difference") if entry.get("amount_difference") is not None else float("inf"),
            entry.get("date_difference_days") if entry.get("date_difference_days") is not None else 999,
        )
    )

    line_payload["candidates_found"] = len(candidates)

    return jsonify({"line": line_payload, "candidates": candidates}), 200


@recon_bp.post("/reconciliation/firstcard/match")
def match_invoice_lines() -> Any:
    """Attempt automatic matching of invoice lines against receipts."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    payload = request.get_json(silent=True) or {}
    invoice_id = payload.get("document_id") or payload.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "missing_document_id"}), 400

    log_event(
        logger,
        "matching.api.invoice.requested",
        invoice_id=invoice_id,
        actor="reconciliation_ui",
    )
    _ensure_processing_state(invoice_id)

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

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT main_id,
                       purchase_date,
                       amount_original,
                       amount_sek,
                       gross_amount
                  FROM creditcard_invoice_items
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
            reason="invoice_item_missing",
        )
        return jsonify({"ok": False, "reason": "not_found"}), 404

    main_id = int(row[0] or 0)
    purchase_date = row[1]
    amount_candidates = (_as_decimal(row[2]), _as_decimal(row[3]), _as_decimal(row[4]))
    matched_amount = next((val for val in amount_candidates if val is not None), None)

    if not invoice_id:
        invoice_id = _find_invoice_id_for_main(main_id)
    if not invoice_id:
        log_event(
            logger,
            "matching.api.line.failed",
            line_id=line_id,
            level="error",
            reason="invoice_not_found",
        )
        return jsonify({"ok": False, "reason": "invoice_not_found"}), 404

    invoice_line_id = _find_invoice_line_id_for_item(line_id, invoice_id)
    if invoice_line_id is None:
        log_event(
            logger,
            "matching.api.line.failed",
            line_id=line_id,
            invoice_id=invoice_id,
            level="error",
            reason="line_mapping_missing",
        )
        return jsonify({"ok": False, "reason": "line_mapping_missing"}), 404

    try:
        with db_cursor() as cur:
            cur.execute("SELECT invoice_item_id FROM creditcard_receipt_matches WHERE receipt_id=%s AND invoice_item_id<>%s LIMIT 1", (new_file_id, line_id))
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
            cur.execute("SELECT matched_file_id FROM invoice_lines WHERE id=%s", (invoice_line_id,))
            row = cur.fetchone()
            if row:
                old_match = row[0]

        updated = transition_line_status_and_link(
            invoice_line_id,
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

        _log_line_history(
            invoice_line_id,
            "matched",
            "manual",
            old_file_id=old_match,
            new_file_id=new_file_id,
            reason="manual-match",
        )

        _persist_credit_card_match(
            new_file_id,
            line_id,
            matched_amount,
            None,
            True,
            match_origin="manual",
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

    log_event(
        logger,
        "matching.api.line.completed",
        line_id=line_id,
        invoice_id=invoice_id,
        receipt_id=new_file_id,
        matched_amount=matched_amount,
    )
    return jsonify({"ok": True}), 200


@recon_bp.get("/reconciliation/firstcard/statements")
def list_statements() -> Any:
    """List all company card statements/invoices."""
    items: list[dict[str, Any]] = []
    if db_cursor is None:
        return jsonify({"statements": items, "total": 0}), 200

    try:
        with db_cursor() as cur:
            # Check if updated_at column exists
            cur.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'invoice_documents'
                  AND COLUMN_NAME = 'updated_at'
                """
            )
            has_updated_at = cur.fetchone()[0] > 0

            if has_updated_at:
                cur.execute(
                    """
                    SELECT id, uploaded_at, updated_at, status, processing_status,
                           period_start, period_end, metadata_json
                    FROM invoice_documents
                    WHERE invoice_type IN ('company_card', 'credit_card_invoice')
                    ORDER BY uploaded_at DESC LIMIT 100
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT id, uploaded_at, NULL as updated_at, status, processing_status,
                           period_start, period_end, metadata_json
                    FROM invoice_documents
                    WHERE invoice_type IN ('company_card', 'credit_card_invoice')
                    ORDER BY uploaded_at DESC LIMIT 100
                    """
                )

            for row in cur.fetchall() or []:
                doc_id, uploaded_at, updated_at, status, processing_status, period_start, period_end, metadata_raw = row

                # Parse metadata to get line counts
                metadata: dict[str, Any] = {}
                if metadata_raw:
                    try:
                        if isinstance(metadata_raw, (bytes, bytearray)):
                            metadata_raw = metadata_raw.decode("utf-8")
                        metadata = json.loads(metadata_raw)
                    except Exception:
                        metadata = {}

                # Get line counts
                total_lines, matched_lines = _count_invoice_lines(doc_id)
                unmatched_lines = max(total_lines - matched_lines, 0)

                # Extract invoice_summary from metadata
                invoice_summary = metadata.get("invoice_summary")
                if not isinstance(invoice_summary, dict):
                    invoice_summary = {}

                item = {
                    "id": doc_id,
                    "uploaded_at": str(uploaded_at) if uploaded_at else None,
                    "created_at": str(uploaded_at) if uploaded_at else None,
                    "updated_at": str(updated_at) if updated_at else str(uploaded_at) if uploaded_at else None,
                    "status": status,
                    "processing_status": processing_status or metadata.get("processing_status"),
                    "period_start": str(period_start) if period_start else metadata.get("period_start"),
                    "period_end": str(period_end) if period_end else metadata.get("period_end"),
                    "line_counts": {
                        "total": total_lines,
                        "matched": matched_lines,
                        "unmatched": unmatched_lines,
                    },
                    "overall_confidence": metadata.get("overall_confidence"),
                    "invoice_number": invoice_summary.get("invoice_number") or metadata.get("invoice_number"),
                    "invoice_date": invoice_summary.get("invoice_date"),
                    "invoice_summary": invoice_summary,
                }

                # Add card details if available
                if metadata.get("creditcard_main_id"):
                    item["creditcard_main_id"] = metadata["creditcard_main_id"]

                if isinstance(invoice_summary, dict):
                    item["card_type"] = invoice_summary.get("card_type")
                    item["card_name"] = invoice_summary.get("card_name")
                    item["card_label"] = invoice_summary.get("card_label")
                    item["card_holder"] = invoice_summary.get("card_holder")
                    item["card_number_masked"] = invoice_summary.get("card_number_masked")

                items.append(item)
    except Exception as e:
        logger.error(f"Failed to list statements: {e}")
        items = []

    return jsonify({"statements": items, "total": len(items)}), 200


@recon_bp.delete("/reconciliation/firstcard/statements/<sid>")
def delete_statement(sid: str) -> Any:
    """Delete a FirstCard invoice statement and all derived artifacts."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    metadata: dict[str, Any] = {}
    related_file_ids: list[str] = [sid]
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                (sid,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "not_found"}), 404
            if row[0]:
                try:
                    metadata = json.loads(row[0])
                except Exception:
                    metadata = {}

            cur.execute(
                "SELECT id FROM unified_files WHERE original_file_id=%s",
                (sid,),
            )
            for file_row in cur.fetchall() or []:
                related_file_ids.append(str(file_row[0]))
    except Exception as exc:
        logger.error("Failed to load statement metadata for %s: %s", sid, exc)
        return jsonify({"error": "delete_failed"}), 500

    creditcard_main_id: Optional[int] = None
    try:
        main_val = metadata.get("creditcard_main_id")
        if isinstance(main_val, (int, float)) and not isinstance(main_val, bool):
            creditcard_main_id = int(main_val)
        elif isinstance(main_val, str) and main_val.isdigit():
            creditcard_main_id = int(main_val)
    except Exception:
        creditcard_main_id = None

    try:
        with db_cursor() as cur:
            # Remove workflow run history (cascade clears stages)
            cur.execute("DELETE FROM workflow_runs WHERE file_id=%s", (sid,))

            # Remove AI processing logs tied to invoice or derived files
            if related_file_ids:
                placeholders = ", ".join(["%s"] * len(related_file_ids))
                cur.execute(
                    f"DELETE FROM ai_processing_history WHERE file_id IN ({placeholders})",
                    tuple(related_file_ids),
                )

            # Remove invoice line artifacts
            cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (sid,))

            if creditcard_main_id is not None:
                cur.execute(
                    """
                    DELETE FROM creditcard_receipt_matches
                    WHERE invoice_item_id IN (
                        SELECT id FROM creditcard_invoice_items WHERE main_id=%s
                    )
                    """,
                    (creditcard_main_id,),
                )
                cur.execute(
                    "DELETE FROM creditcard_invoice_items WHERE main_id=%s",
                    (creditcard_main_id,),
                )
                cur.execute(
                    "DELETE FROM creditcard_invoices_main WHERE id=%s",
                    (creditcard_main_id,),
                )

            # Remove unified file entries (original + derived)
            cur.execute(
                "DELETE FROM unified_files WHERE id=%s OR original_file_id=%s",
                (sid, sid),
            )

            # Finally remove invoice document
            cur.execute(
                "DELETE FROM invoice_documents WHERE id=%s",
                (sid,),
            )
    except Exception as exc:
        logger.error("Failed to delete FirstCard invoice %s: %s", sid, exc)
        return jsonify({"error": "delete_failed"}), 500

    return jsonify({"ok": True}), 200


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/confirm")
def confirm_statement(sid: str) -> Any:
    """Mark a FirstCard invoice as completed once all lines are matched."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    total_lines, matched_lines = refresh_invoice_match_state(sid)
    if total_lines and matched_lines < total_lines:
        return jsonify({"error": "lines_unmatched", "total": total_lines, "matched": matched_lines}), 409

    try:
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
    except Exception as exc:
        logger.error("Failed to confirm invoice %s: %s", sid, exc)
        return jsonify({"error": "confirm_failed"}), 500

    return jsonify({"ok": True, "status": "completed"}), 200


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
