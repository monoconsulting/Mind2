# -*- coding: utf-8 -*-
# ÅÄÖ åäö – Swedish encoding test

"""Workflow state coordinator for FirstCard invoice processing.

This module provides centralized workflow orchestration for FirstCard credit card
statements. It manages the complete lifecycle from upload through OCR, AI extraction,
matching, and completion.

The WorkflowCoordinator class ensures proper state transitions and prevents race
conditions by using the atomic transition helpers from services.invoice_status.
"""

from __future__ import annotations

import logging
from typing import Optional

from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceProcessingStatus,
    transition_document_status,
    transition_processing_status,
)

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)


class WorkflowCoordinator:
    """Centralized state machine for FirstCard invoice workflows.

    This class orchestrates the complete lifecycle of a FirstCard credit card
    statement through the following stages:

    Processing Status Flow:
        uploaded → ocr_pending → ocr_done → ai_processing →
        ready_for_matching → matching_completed → completed

    Document Status Flow:
        imported → matching → partially_matched/matched → completed

    All state transitions are atomic and validate the current state before
    updating to prevent race conditions between workers.

    Example:
        coordinator = WorkflowCoordinator()

        # Start processing a new invoice
        if coordinator.start_processing(invoice_id):
            # Successfully transitioned to ocr_pending
            pass

        # Complete OCR stage
        if coordinator.advance_to_ocr_complete(invoice_id):
            # Successfully transitioned to ocr_done
            pass

        # Ready for matching
        if coordinator.advance_to_matching_ready(invoice_id):
            # Successfully transitioned to ready_for_matching
            pass

        # Complete matching
        if coordinator.complete_matching(invoice_id):
            # Successfully transitioned to matching_completed
            pass
    """

    def start_processing(self, invoice_id: str) -> bool:
        """Initialize workflow for a newly uploaded invoice.

        Transitions:
            processing_status: uploaded → ocr_pending
            status: (no change, remains imported)

        Args:
            invoice_id: The invoice document identifier

        Returns:
            True if transition succeeded, False if already in progress or failed
        """
        logger.info(f"Starting workflow for invoice {invoice_id}")

        success = transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.OCR_PENDING,
            (InvoiceProcessingStatus.UPLOADED,),
        )

        if success:
            logger.info(f"Successfully started workflow for invoice {invoice_id}")
        else:
            logger.warning(f"Failed to start workflow for invoice {invoice_id} - may already be in progress")

        return success

    def advance_to_ocr_complete(self, invoice_id: str) -> bool:
        """Mark OCR stage as complete.

        Transitions:
            processing_status: ocr_pending → ocr_done
            status: (no change)

        Args:
            invoice_id: The invoice document identifier

        Returns:
            True if transition succeeded, False otherwise
        """
        logger.info(f"Marking OCR complete for invoice {invoice_id}")

        success = transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.OCR_DONE,
            (InvoiceProcessingStatus.OCR_PENDING,),
        )

        if success:
            logger.info(f"Successfully marked OCR complete for invoice {invoice_id}")
        else:
            logger.warning(f"Failed to mark OCR complete for invoice {invoice_id}")

        return success

    def advance_to_ai_processing(self, invoice_id: str) -> bool:
        """Mark invoice as being processed by AI extraction.

        Transitions:
            processing_status: ocr_done → ai_processing
            status: (no change)

        Args:
            invoice_id: The invoice document identifier

        Returns:
            True if transition succeeded, False otherwise
        """
        logger.info(f"Starting AI processing for invoice {invoice_id}")

        success = transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.AI_PROCESSING,
            (InvoiceProcessingStatus.OCR_DONE,),
        )

        if success:
            logger.info(f"Successfully started AI processing for invoice {invoice_id}")
        else:
            logger.warning(f"Failed to start AI processing for invoice {invoice_id}")

        return success

    def advance_to_matching_ready(self, invoice_id: str) -> bool:
        """Mark invoice as ready for receipt matching.

        Transitions:
            processing_status: ai_processing/ocr_done → ready_for_matching
            status: imported/matching → matching

        This method allows transition from both ai_processing and ocr_done
        to support cases where OCR data is sufficient without AI extraction.

        Args:
            invoice_id: The invoice document identifier

        Returns:
            True if transition succeeded, False otherwise
        """
        logger.info(f"Marking invoice {invoice_id} ready for matching")

        # Transition processing status
        processing_success = transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.READY_FOR_MATCHING,
            (
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.UPLOADED,  # Support manual JSON import
            ),
        )

        # Transition document status to matching
        document_success = transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.MATCHING,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
            ),
        )

        success = processing_success or document_success
        if success:
            logger.info(f"Successfully marked invoice {invoice_id} ready for matching")
        else:
            logger.warning(f"Failed to mark invoice {invoice_id} ready for matching")

        return success

    def complete_matching(self, invoice_id: str) -> bool:
        """Mark matching stage as complete.

        Transitions:
            processing_status: ready_for_matching → matching_completed
            status: matching → matched

        Args:
            invoice_id: The invoice document identifier

        Returns:
            True if transition succeeded, False otherwise
        """
        logger.info(f"Completing matching for invoice {invoice_id}")

        # Transition processing status
        processing_success = transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.MATCHING_COMPLETED,
            (InvoiceProcessingStatus.READY_FOR_MATCHING,),
        )

        # Transition document status to matched
        document_success = transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.MATCHED,
            (
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
            ),
        )

        success = processing_success or document_success
        if success:
            logger.info(f"Successfully completed matching for invoice {invoice_id}")
        else:
            logger.warning(f"Failed to complete matching for invoice {invoice_id}")

        return success

    def mark_as_failed(self, invoice_id: str, reason: Optional[str] = None) -> bool:
        """Mark invoice workflow as failed.

        Transitions:
            processing_status: any → failed
            status: any → failed

        Args:
            invoice_id: The invoice document identifier
            reason: Optional failure reason for logging

        Returns:
            True if transition succeeded, False otherwise
        """
        logger.error(f"Marking invoice {invoice_id} as failed: {reason or 'unknown reason'}")

        # Transition processing status to failed
        processing_success = transition_processing_status(
            invoice_id,
            InvoiceProcessingStatus.FAILED,
            (
                InvoiceProcessingStatus.UPLOADED,
                InvoiceProcessingStatus.OCR_PENDING,
                InvoiceProcessingStatus.OCR_DONE,
                InvoiceProcessingStatus.AI_PROCESSING,
                InvoiceProcessingStatus.READY_FOR_MATCHING,
            ),
        )

        # Transition document status to failed
        document_success = transition_document_status(
            invoice_id,
            InvoiceDocumentStatus.FAILED,
            (
                InvoiceDocumentStatus.IMPORTED,
                InvoiceDocumentStatus.MATCHING,
                InvoiceDocumentStatus.PARTIALLY_MATCHED,
                InvoiceDocumentStatus.MATCHED,
            ),
        )

        success = processing_success or document_success
        if success:
            logger.info(f"Successfully marked invoice {invoice_id} as failed")
        else:
            logger.warning(f"Failed to mark invoice {invoice_id} as failed (may already be failed)")

        return success

    def get_current_state(self, invoice_id: str) -> Optional[tuple[str, str]]:
        """Get current processing and document status.

        Args:
            invoice_id: The invoice document identifier

        Returns:
            (processing_status, document_status) or None if not found
        """
        if db_cursor is None:
            return None

        try:
            with db_cursor() as cur:
                cur.execute(
                    "SELECT processing_status, status FROM invoice_documents WHERE id=%s",
                    (invoice_id,),
                )
                row = cur.fetchone()
                if row:
                    return (row[0], row[1])
        except Exception as e:
            logger.error(f"Failed to get current state for invoice {invoice_id}: {e}")

        return None

    def create_workflow_run(
        self,
        workflow_key: str,
        source_channel: str,
        file_id: str,
        content_hash: str,
    ) -> Optional[int]:
        """Create a new workflow run in the database.

        Args:
            workflow_key: Workflow identifier (e.g., 'WF3_FIRSTCARD_INVOICE')
            source_channel: Source of the workflow (e.g., 'kortmatchning_upload')
            file_id: The file identifier
            content_hash: SHA256 hash of the file content

        Returns:
            workflow_run_id if successful, None otherwise
        """
        if db_cursor is None:
            logger.error("Cannot create workflow run - database not available")
            return None

        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_runs
                    (workflow_key, source_channel, file_id, content_hash, current_stage, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'init', 'running', NOW(), NOW())
                    """,
                    (workflow_key, source_channel, file_id, content_hash),
                )
                workflow_run_id = cur.lastrowid
                logger.info(
                    f"Created workflow run {workflow_run_id} for file {file_id} (workflow={workflow_key})"
                )
                return workflow_run_id
        except Exception as e:
            logger.error(f"Failed to create workflow run for file {file_id}: {e}")
            return None

    def begin_import_stage(
        self,
        workflow_run_id: Optional[int],
        stage_key: str,
        message: Optional[str] = None,
    ) -> bool:
        """Begin an import stage in the workflow.

        Args:
            workflow_run_id: The workflow run identifier
            stage_key: Stage identifier (e.g., 'src_fc', 'fc_create')
            message: Optional message to log

        Returns:
            True if successful, False otherwise
        """
        if workflow_run_id is None:
            return False

        if db_cursor is None:
            logger.error("Cannot begin import stage - database not available")
            return False

        # Import stage boundaries that require start/end markers
        _IMPORT_STAGE_WITH_BOUNDARIES = {
            "src_portal", "src_ftp", "src_fc", "ingest_store", "ingest_wf1",
            "fc_create", "fc_ocr", "fc_parse", "fc_ready", "detect_type",
            "r_ocr", "r_ai3", "r_ai4", "r_persist", "r_queue_match",
            "ai5", "m_link", "m_unmatched", "finalize_ok", "finalize_fail",
        }

        try:
            # Log boundary start marker if applicable
            if stage_key in _IMPORT_STAGE_WITH_BOUNDARIES:
                with db_cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO workflow_stage_runs
                        (workflow_run_id, stage_key, status, started_at, finished_at, message)
                        VALUES (%s, %s, %s, NOW(), NOW(), %s)
                        """,
                        (
                            workflow_run_id,
                            f"{stage_key}_start",
                            "succeeded",
                            message[:200] if message else None,
                        ),
                    )

            # Log stage as running
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_stage_runs
                    (workflow_run_id, stage_key, status, started_at, message)
                    VALUES (%s, %s, %s, NOW(), %s)
                    """,
                    (
                        workflow_run_id,
                        stage_key,
                        "running",
                        message[:200] if message else None,
                    ),
                )

            logger.info(f"Began import stage '{stage_key}' for workflow run {workflow_run_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to begin import stage '{stage_key}': {e}")
            return False

    def complete_import_stage(
        self,
        workflow_run_id: Optional[int],
        stage_key: str,
        success: bool = True,
        message: Optional[str] = None,
    ) -> bool:
        """Complete an import stage in the workflow.

        Args:
            workflow_run_id: The workflow run identifier
            stage_key: Stage identifier (e.g., 'src_fc', 'fc_create')
            success: Whether the stage completed successfully
            message: Optional message to log

        Returns:
            True if successful, False otherwise
        """
        if workflow_run_id is None:
            return False

        if db_cursor is None:
            logger.error("Cannot complete import stage - database not available")
            return False

        # Import stage boundaries that require start/end markers
        _IMPORT_STAGE_WITH_BOUNDARIES = {
            "src_portal", "src_ftp", "src_fc", "ingest_store", "ingest_wf1",
            "fc_create", "fc_ocr", "fc_parse", "fc_ready", "detect_type",
            "r_ocr", "r_ai3", "r_ai4", "r_persist", "r_queue_match",
            "ai5", "m_link", "m_unmatched", "finalize_ok", "finalize_fail",
        }

        status = "succeeded" if success else "failed"

        try:
            # Update stage as completed
            with db_cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_stage_runs
                    SET status=%s, finished_at=NOW(), message=%s
                    WHERE workflow_run_id=%s AND stage_key=%s
                    """,
                    (
                        status,
                        message[:200] if message else None,
                        workflow_run_id,
                        stage_key,
                    ),
                )

            # Log boundary end marker if applicable
            if stage_key in _IMPORT_STAGE_WITH_BOUNDARIES:
                with db_cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO workflow_stage_runs
                        (workflow_run_id, stage_key, status, started_at, finished_at, message)
                        VALUES (%s, %s, %s, NOW(), NOW(), %s)
                        """,
                        (
                            workflow_run_id,
                            f"{stage_key}_end",
                            status,
                            message[:200] if message else None,
                        ),
                    )

            logger.info(
                f"Completed import stage '{stage_key}' for workflow run {workflow_run_id} (success={success})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to complete import stage '{stage_key}': {e}")
            return False

    def dispatch_workflow(self, workflow_run_id: int) -> bool:
        """Dispatch a Celery workflow task based on the workflow_key.

        Args:
            workflow_run_id: The workflow run identifier

        Returns:
            True if dispatched successfully, False otherwise
        """
        if db_cursor is None:
            logger.error("Cannot dispatch workflow - database not available")
            return False

        try:
            # Get workflow run details
            with db_cursor() as cur:
                cur.execute(
                    "SELECT workflow_key FROM workflow_runs WHERE id=%s",
                    (workflow_run_id,),
                )
                row = cur.fetchone()

            if not row:
                logger.error(f"Workflow run {workflow_run_id} not found")
                return False

            workflow_key = row[0]

            # Import Celery app and task
            try:
                from services.tasks.workflow_tasks import dispatch_workflow as wf_dispatch
                success = wf_dispatch(workflow_run_id)
                if success:
                    logger.info(
                        f"Dispatched workflow {workflow_key} for run {workflow_run_id}"
                    )
                else:
                    logger.error(
                        f"Failed to dispatch workflow {workflow_key} for run {workflow_run_id}"
                    )
                return success
            except ImportError as e:
                logger.error(f"Failed to import workflow dispatch function: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to dispatch workflow run {workflow_run_id}: {e}")
            return False
