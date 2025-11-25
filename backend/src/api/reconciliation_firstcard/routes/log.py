# -*- coding: utf-8 -*-
# Kontrollrad: ÅÄÖ åäö

"""Log endpoint for FirstCard invoice reconciliation.

Provides detailed workflow and AI processing logs for invoice documents.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from flask import jsonify

from .. import recon_bp
from ..utils.db_helpers import load_invoice_document

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)


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

    doc = load_invoice_document(invoice_id)
    if not doc:
        return jsonify({"error": "not_found"}), 404
    _, metadata, _ = doc

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
        # Fix encoding for Swedish characters if needed
        if source_channel and isinstance(source_channel, str):
            try:
                # Check if contains non-ASCII (potential mojibake)
                if any(ord(c) > 127 for c in source_channel):
                    fixed = source_channel.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')
                    if fixed != source_channel and len(fixed) > 0:
                        source_channel = fixed
            except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
                pass

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
            # Fix encoding for Swedish characters if needed
            # The problem: data was saved as UTF-8 but read as latin1, resulting in mojibake
            # Solution: encode as latin1 (to get original bytes) then decode as utf-8
            if message and isinstance(message, str):
                try:
                    # Check if message contains mojibake characters
                    if any(ord(c) > 127 for c in message):
                        # Try to fix: encode back to bytes using latin1, then decode as utf-8
                        fixed = message.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')
                        if fixed != message and len(fixed) > 0:
                            message = fixed
                except (UnicodeDecodeError, UnicodeEncodeError, AttributeError):
                    # If that fails, keep original
                    pass

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
