# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Statement management endpoints for FirstCard reconciliation.

Handles listing, deleting, resuming, restarting, and confirming credit card statements.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from flask import jsonify

from .. import recon_bp
from ..utils.db_helpers import (
    load_invoice_document,
    count_invoice_lines,
    write_invoice_metadata,
)
from ..services.workflow_coordinator import WorkflowCoordinator
from services.tasks import (
    dispatch_workflow,
    log_import_event,
    refresh_invoice_match_state,
)
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    invoice_documents_supports_updated_at,
    transition_document_status,
    transition_processing_status,
)
from observability.events import log_event

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)


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
                           period_start, period_end, metadata_json,
                           (SELECT wr.current_stage
                            FROM workflow_runs wr
                            WHERE wr.file_id = invoice_documents.id
                            ORDER BY wr.created_at DESC
                            LIMIT 1) as current_stage_key
                    FROM invoice_documents
                    WHERE invoice_type IN ('company_card', 'credit_card_invoice')
                      AND deleted_at IS NULL
                    ORDER BY uploaded_at DESC LIMIT 100
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT id, uploaded_at, NULL as updated_at, status, processing_status,
                           period_start, period_end, metadata_json,
                           (SELECT wr.current_stage
                            FROM workflow_runs wr
                            WHERE wr.file_id = invoice_documents.id
                            ORDER BY wr.created_at DESC
                            LIMIT 1) as current_stage_key
                    FROM invoice_documents
                    WHERE invoice_type IN ('company_card', 'credit_card_invoice')
                      AND deleted_at IS NULL
                    ORDER BY uploaded_at DESC LIMIT 100
                    """
                )

            for row in cur.fetchall() or []:
                doc_id, uploaded_at, updated_at, status, processing_status, period_start, period_end, metadata_raw, current_stage_key = row

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
                total_lines, matched_lines = count_invoice_lines(doc_id)
                unmatched_lines = max(total_lines - matched_lines, 0)

                # Extract invoice_summary from metadata
                invoice_summary = metadata.get("invoice_summary")
                if not isinstance(invoice_summary, dict):
                    invoice_summary = {}

                # Get data from creditcard_invoices_main if available
                due_date = None
                amount_to_pay = None
                card_name_from_main = None
                invoice_date_from_main = None
                creditcard_main_id = metadata.get("creditcard_main_id")
                if creditcard_main_id:
                    try:
                        cur.execute(
                            "SELECT due_date, amount_to_pay, card_name, invoice_date FROM creditcard_invoices_main WHERE id=%s",
                            (creditcard_main_id,)
                        )
                        main_row = cur.fetchone()
                        if main_row:
                            due_date = main_row[0]
                            amount_to_pay = main_row[1]
                            card_name_from_main = main_row[2]
                            invoice_date_from_main = main_row[3]
                    except Exception as e:
                        logger.warning(f"Failed to load creditcard_invoices_main data for {creditcard_main_id}: {e}")

                metadata_updated_at = metadata.get("last_progress_at") if isinstance(metadata, dict) else None
                updated_ts = str(updated_at) if updated_at else None
                if not updated_ts and metadata_updated_at:
                    updated_ts = str(metadata_updated_at)
                if not updated_ts and uploaded_at:
                    updated_ts = str(uploaded_at)

                item = {
                    "id": doc_id,
                    "uploaded_at": str(uploaded_at) if uploaded_at else None,
                    "created_at": str(uploaded_at) if uploaded_at else None,
                    "updated_at": updated_ts,
                    "status": status,
                    "processing_status": processing_status or metadata.get("processing_status"),
                    "current_stage_key": current_stage_key,
                    "period_start": str(period_start) if period_start else metadata.get("period_start"),
                    "period_end": str(period_end) if period_end else metadata.get("period_end"),
                    "line_counts": {
                        "total": total_lines,
                        "matched": matched_lines,
                        "unmatched": unmatched_lines,
                    },
                    "overall_confidence": metadata.get("overall_confidence"),
                    "invoice_number": invoice_summary.get("invoice_number") or metadata.get("invoice_number"),
                    "invoice_date": str(invoice_date_from_main) if invoice_date_from_main else invoice_summary.get("invoice_date"),
                    "due_date": str(due_date) if due_date else None,
                    "amount_to_pay": float(amount_to_pay) if amount_to_pay is not None else None,
                    "card_name": card_name_from_main or invoice_summary.get("card_name"),
                    "invoice_summary": invoice_summary,
                }

                # Add card details if available
                if metadata.get("creditcard_main_id"):
                    item["creditcard_main_id"] = metadata["creditcard_main_id"]

                if isinstance(invoice_summary, dict):
                    item["card_type"] = invoice_summary.get("card_type")
                    # Only use invoice_summary values if card_name_from_main is not available
                    if not card_name_from_main:
                        item["card_name"] = invoice_summary.get("card_name")
                    item["card_label"] = invoice_summary.get("card_label")
                    item["card_holder"] = invoice_summary.get("card_holder")
                    item["card_number_masked"] = invoice_summary.get("card_number_masked")

                items.append(item)
    except Exception as e:
        logger.error(f"Failed to list statements: {e}")
        items = []

    return jsonify({"statements": items, "total": len(items)}), 200


@recon_bp.get("/reconciliation/firstcard/summary")
def system_summary() -> Any:
    """Return aggregate stats for receipts, purchases, and invoices."""
    if db_cursor is None:
        return jsonify(
            {
                "receipts": {"matched": 0, "total": 0},
                "purchases": {"unmatched": 0, "total": 0},
                "invoices": {"incomplete": 0, "total": 0},
            }
        ), 200

    receipts = {"matched": 0, "total": 0}
    purchases = {"unmatched": 0, "total": 0}
    invoices = {"incomplete": 0, "total": 0}

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    SUM(CASE WHEN COALESCE(credit_card_match, 0) <> 0 THEN 1 ELSE 0 END) AS matched,
                    COUNT(*) AS total
                  FROM unified_files
                 WHERE deleted_at IS NULL
                   AND COALESCE(workflow_type, '') NOT IN ('creditcard_invoice', 'creditcard_page')
                """
            )
            row = cur.fetchone() or (0, 0)
            receipts = {
                "matched": int(row[0] or 0),
                "total": int(row[1] or 0),
            }

            cur.execute(
                """
                SELECT
                    SUM(
                        CASE
                            WHEN match_status IS NULL OR match_status IN ('pending', 'unmatched', '')
                                THEN 1 ELSE 0 END
                    ) AS unmatched,
                    COUNT(*) AS total
                  FROM invoice_lines
                """
            )
            row = cur.fetchone() or (0, 0)
            purchases = {
                "unmatched": int(row[0] or 0),
                "total": int(row[1] or 0),
            }

            cur.execute(
                """
                SELECT
                    SUM(
                        CASE
                            WHEN processing_status IS NULL
                                 OR processing_status NOT IN ('matching_completed', 'completed')
                                 THEN 1 ELSE 0 END
                    ) AS incomplete,
                    COUNT(*) AS total
                  FROM invoice_documents
                 WHERE invoice_type IN ('company_card', 'credit_card_invoice')
                   AND deleted_at IS NULL
                """
            )
            row = cur.fetchone() or (0, 0)
            invoices = {
                "incomplete": int(row[0] or 0),
                "total": int(row[1] or 0),
            }
    except Exception:
        logger.exception("Failed to build FirstCard summary")

    return jsonify(
        {
            "receipts": receipts,
            "purchases": purchases,
            "invoices": invoices,
        }
    ), 200


@recon_bp.delete("/reconciliation/firstcard/statements/<sid>")
def delete_statement(sid: str) -> Any:
    """Soft delete a FirstCard invoice statement and related files."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    metadata: dict[str, Any] = {}
    related_file_ids: list[str] = [sid]
    existing_deleted_at: Optional[datetime] = None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT metadata_json, deleted_at FROM invoice_documents WHERE id=%s",
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
            existing_deleted_at = row[1]

            cur.execute(
                "SELECT id FROM unified_files WHERE original_file_id=%s",
                (sid,),
            )
            for file_row in cur.fetchall() or []:
                related_file_ids.append(str(file_row[0]))
    except Exception as exc:
        logger.error("Failed to load statement metadata for %s: %s", sid, exc)
        return jsonify({"error": "delete_failed"}), 500

    deletion_iso = metadata.get("deleted_at")
    if not deletion_iso:
        deletion_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        metadata["deleted_at"] = deletion_iso

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE invoice_documents
                   SET metadata_json=%s,
                       deleted_at=COALESCE(deleted_at, NOW())
                 WHERE id=%s
                """,
                (json.dumps(metadata), sid),
            )
            if related_file_ids:
                placeholders = ", ".join(["%s"] * len(related_file_ids))
                cur.execute(
                    f"UPDATE unified_files SET deleted_at=COALESCE(deleted_at, NOW()) WHERE id IN ({placeholders})",
                    tuple(related_file_ids),
                )
    except Exception as exc:
        logger.error("Failed to soft delete FirstCard invoice %s: %s", sid, exc)
        return jsonify({"error": "delete_failed"}), 500

    return jsonify(
        {
            "ok": True,
            "deleted_at": deletion_iso,
            "already_deleted": existing_deleted_at is not None,
        }
    ), 200


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/resume")
def resume_statement_workflow(sid: str) -> Any:
    """Resume a stalled invoice workflow."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    if not load_invoice_document(sid):
        return jsonify({"error": "not_found"}), 404

    # Get the latest workflow_run for this invoice
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, status, current_stage
                FROM workflow_runs
                WHERE file_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (sid,),
            )
            row = cur.fetchone()

            if not row:
                return jsonify({"error": "no_workflow_found"}), 404

            workflow_run_id, status, current_stage = row

            # Update status to show it's processing again using transitions
            coordinator = WorkflowCoordinator()
            try:
                # Transition to OCR_PENDING (resume processing)
                coordinator.start_processing(sid)
                # Transition document status to MATCHING
                transition_document_status(
                    sid,
                    InvoiceDocumentStatus.MATCHING,
                    (
                        InvoiceDocumentStatus.IMPORTED,
                        InvoiceDocumentStatus.MATCHING,
                        InvoiceDocumentStatus.FAILED,
                        InvoiceDocumentStatus.PARTIALLY_MATCHED,
                    ),
                )
            except Exception as e:
                logger.warning(f"Failed to update status for resume {sid}: {e}")

            # Log resume stage to workflow_stage_runs so frontend sees immediate change
            log_import_event(
                workflow_run_id,
                "resume_dispatch",
                status="running",
                message=f"Återupptar matchning (tidigare status: {status})",
            )

            # Dispatch the workflow to resume
            if dispatch_workflow(workflow_run_id):
                log_event(
                    logger,
                    "invoice.workflow.resumed",
                    invoice_id=sid,
                    workflow_run_id=workflow_run_id,
                    previous_status=status,
                    previous_stage=current_stage,
                )
                return jsonify({
                    "ok": True,
                    "workflow_run_id": workflow_run_id,
                    "action": "resumed",
                    "processing_status": InvoiceProcessingStatus.OCR_PENDING.value,
                    "status": "matching",
                    "current_stage_key": "resume_dispatch",
                }), 200
            else:
                return jsonify({"error": "dispatch_failed"}), 500

    except Exception as e:
        logger.error(f"Failed to resume workflow for {sid}: {e}")
        return jsonify({"error": "resume_failed", "details": str(e)}), 500


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/restart")
def restart_statement_workflow(sid: str) -> Any:
    """Restart invoice processing from the beginning (WF3)."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    if not load_invoice_document(sid):
        return jsonify({"error": "not_found"}), 404

    # Get content_hash from unified_files
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT content_hash FROM unified_files WHERE id = %s",
                (sid,),
            )
            row = cur.fetchone()

            if not row or not row[0]:
                return jsonify({"error": "file_not_found"}), 404

            content_hash = row[0]

    except Exception as e:
        logger.error(f"Failed to get content_hash for {sid}: {e}")
        return jsonify({"error": "lookup_failed", "details": str(e)}), 500

    # Create a new workflow run
    coordinator = WorkflowCoordinator()
    workflow_run_id = coordinator.create_workflow_run(
        workflow_key="WF3_FIRSTCARD_INVOICE",
        source_channel="kortmatchning_restart",
        file_id=sid,
        content_hash=content_hash,
    )

    if not workflow_run_id:
        return jsonify({"error": "workflow_creation_failed"}), 500

    # Log restart stage to workflow_stage_runs so frontend sees immediate change
    log_import_event(
        workflow_run_id,
        "restart_dispatch",
        status="running",
        message="Omstartar fakturaimport från början",
    )

    # Dispatch the new workflow
    if dispatch_workflow(workflow_run_id):
        log_event(
            logger,
            "invoice.workflow.restarted",
            invoice_id=sid,
            workflow_run_id=workflow_run_id,
        )

        # Update invoice_documents metadata
        try:
            with db_cursor() as cur:
                cur.execute(
                    "SELECT metadata_json FROM invoice_documents WHERE id=%s",
                    (sid,),
                )
                row = cur.fetchone()
                metadata = {}
                if row and row[0]:
                    try:
                        metadata = json.loads(row[0])
                    except Exception:
                        pass

                metadata["workflow_run_id"] = workflow_run_id
                metadata["processing_status"] = "ocr_pending"
                if not invoice_documents_supports_updated_at():
                    metadata["last_progress_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"

                # Update metadata separately using helper function
                write_invoice_metadata(sid, metadata)

                # Use transitions for status updates
                transition_processing_status(
                    sid,
                    InvoiceProcessingStatus.OCR_PENDING,
                    (
                        InvoiceProcessingStatus.UPLOADED,
                        InvoiceProcessingStatus.FAILED,
                        InvoiceProcessingStatus.COMPLETED,
                        InvoiceProcessingStatus.OCR_PENDING,
                    ),
                )
                transition_document_status(
                    sid,
                    InvoiceDocumentStatus.IMPORTED,
                    (
                        InvoiceDocumentStatus.FAILED,
                        InvoiceDocumentStatus.COMPLETED,
                        InvoiceDocumentStatus.MATCHED,
                        InvoiceDocumentStatus.IMPORTED,
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to update metadata for restart {sid}: {e}")

        return jsonify({
            "ok": True,
            "workflow_run_id": workflow_run_id,
            "action": "restarted",
            "processing_status": "ocr_pending",
            "status": "imported",
            "current_stage_key": "restart_dispatch",
        }), 200
    else:
        return jsonify({"error": "dispatch_failed"}), 500


@recon_bp.post("/reconciliation/firstcard/statements/<sid>/confirm")
def confirm_statement(sid: str) -> Any:
    """Mark a FirstCard invoice as completed once all lines are matched."""
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    if not load_invoice_document(sid):
        return jsonify({"error": "not_found"}), 404

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
        if not load_invoice_document(sid):
            return jsonify({"error": "not_found"}), 404
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
    else:  # pragma: no cover - DB unavailable fallback
        return jsonify({"error": "db_unavailable"}), 503

    return jsonify({"items": items, "total": len(items)}), 200
