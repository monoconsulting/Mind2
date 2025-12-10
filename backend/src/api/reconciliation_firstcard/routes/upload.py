# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Upload endpoints for FirstCard invoice reconciliation.

Handles invoice file uploads and manual JSON imports.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from flask import jsonify, request
from werkzeug.utils import secure_filename

from .. import recon_bp
from ..utils.db_helpers import (
    create_invoice_document,
    find_file_id_by_hash,
    ensure_invoice_document,
    write_invoice_metadata,
)
from ..services.workflow_coordinator import WorkflowCoordinator
from services.file_detection import detect_file
from services.storage import FileStorage
from services.db.files import create_unified_file, DuplicateFileError
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)


def _storage() -> FileStorage:
    """Return FileStorage instance."""
    base = os.getenv("STORAGE_DIR", "/data/storage")
    return FileStorage(base)


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
        unified_file = create_unified_file(
            file_id=invoice_id,
            file_type=unified_file_type,
            workflow_type="WF3_FIRSTCARD_INVOICE",
            content_hash=file_hash,
            submitted_by=submitted_by,
            source="kortmatchning_upload",
            original_filename=safe_name,
            initial_ai_status="uploaded",
            initial_process_status=InvoiceProcessingStatus.UPLOADED.value,
            mime_type=mime_type,
            file_suffix=file_suffix,
            original_file_id=invoice_id,
            original_file_name=safe_name,
            original_file_size=len(data),
            extra_metadata=other_data,
        )
        workflow_run_id = unified_file.workflow_run_id
    except DuplicateFileError:
        existing_id = find_file_id_by_hash(file_hash)
        return (
            jsonify(
                {
                    "error": "duplicate_file",
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

    create_invoice_document(
        invoice_id=invoice_id,
        invoice_type="credit_card_invoice",
        status=InvoiceDocumentStatus.IMPORTED.value,
        metadata=metadata,
        processing_status=metadata.get("processing_status"),
    )
    ensure_invoice_document(invoice_id=invoice_id, invoice_type="credit_card_invoice")

    coordinator = WorkflowCoordinator()
    
    if workflow_run_id:
        coordinator.begin_import_stage(
            workflow_run_id,
            "src_fc",
            message=f"Fil {safe_name} ({len(data)} bytes)",
        )

    if not workflow_run_id or not coordinator.dispatch_workflow(workflow_run_id):
        logger.error(
            "Failed to dispatch WF3 workflow for invoice %s (run_id=%s)",
            invoice_id,
            workflow_run_id,
        )
        if workflow_run_id:
            coordinator.complete_import_stage(
                workflow_run_id,
                "src_fc",
                success=False,
                message="Kunde inte starta WF3",
            )
        return jsonify({"error": "workflow_dispatch_failed"}), 500

    metadata["workflow_run_id"] = workflow_run_id
    coordinator.begin_import_stage(
        workflow_run_id,
        "fc_create",
        message="Skapar invoice_document-post",
    )
    create_invoice_document(
        invoice_id=invoice_id,
        invoice_type="credit_card_invoice",
        status=InvoiceDocumentStatus.IMPORTED.value,
        metadata=metadata,
        processing_status=metadata.get("processing_status"),
    )
    ensure_invoice_document(invoice_id=invoice_id, invoice_type="credit_card_invoice")
    coordinator.complete_import_stage(
        workflow_run_id,
        "fc_create",
        success=True,
        message="Invoice_document registrerat",
    )
    coordinator.complete_import_stage(
        workflow_run_id,
        "src_fc",
        success=True,
        message="Fil uppladdad",
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
    write_invoice_metadata(invoice_id, metadata)

    return jsonify({"id": invoice_id, "imported": inserted}), 200
