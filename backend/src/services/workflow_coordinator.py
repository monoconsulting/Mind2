from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from services.tasks.common import (
    db_cursor,
    log_event,
    InvoiceProcessingStatus,
    InvoiceDocumentStatus,
)

logger = logging.getLogger(__name__)


class FirstCardWorkflowCoordinator:
    """
    Coordinator for FirstCard (credit card) workflow operations.
    Centralizes logic for creating and updating workflow runs and stages for FC documents.
    """

    def create_workflow_run_for_fc_document(
        self,
        file_id: str,
        workflow_key: str = "WF3_FIRSTCARD_INVOICE",
    ) -> int:
        """
        Creates a new workflow_runs entry for a FirstCard document.

        Args:
            file_id: The unified_file_id (or invoice_document_id).
            workflow_key: The specific workflow key (default: "WF3_FIRSTCARD_INVOICE").

        Returns:
            The ID of the created workflow_run.
        """
        if not db_cursor:
            raise RuntimeError("Database cursor not available")

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO workflow_runs (
                    file_id,
                    workflow_key,
                    status,
                    created_at,
                    updated_at
                ) VALUES (%s, %s, 'queued', NOW(), NOW())
                """,
                (file_id, workflow_key),
            )
            workflow_run_id = cur.lastrowid
            if not workflow_run_id:
                raise RuntimeError("Failed to create workflow_run")

        logger.info(
            "Created workflow_run %s for file %s (key=%s)",
            workflow_run_id,
            file_id,
            workflow_key,
        )
        return workflow_run_id

    def begin_fc_import_stage(
        self,
        workflow_run_id: int,
        stage_name: str,
        message: Optional[str] = None,
    ) -> int:
        """
        Marks the beginning of a workflow stage.

        Args:
            workflow_run_id: The ID of the workflow run.
            stage_name: The name of the stage (e.g., "fc_ocr", "fc_parse").
            message: Optional message to log.

        Returns:
            The ID of the created/updated workflow_stage_run.
        """
        if not db_cursor:
            raise RuntimeError("Database cursor not available")

        with db_cursor() as cur:
            # Check if stage already exists to avoid duplicates if called idempotently
            cur.execute(
                """
                SELECT id FROM workflow_stage_runs
                WHERE workflow_run_id = %s AND stage_key = %s
                """,
                (workflow_run_id, stage_name),
            )
            existing = cur.fetchone()

            if existing:
                stage_id = existing[0]
                cur.execute(
                    """
                    UPDATE workflow_stage_runs
                    SET status = 'running',
                        started_at = NOW(),
                        finished_at = NULL,
                        message = %s
                    WHERE id = %s
                    """,
                    (message, stage_id),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO workflow_stage_runs (
                        workflow_run_id,
                        stage_key,
                        status,
                        started_at,
                        message
                    ) VALUES (%s, %s, 'running', NOW(), %s)
                    """,
                    (workflow_run_id, stage_name, message),
                )
                stage_id = cur.lastrowid
                if not stage_id:
                    raise RuntimeError(f"Failed to create stage run for {stage_name}")

        logger.info(
            "Started stage '%s' for workflow_run %s (msg=%s)",
            stage_name,
            workflow_run_id,
            message,
        )

        # Update workflow_runs current_stage
        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE workflow_runs
                SET current_stage = %s,
                    status = 'running',
                    updated_at = NOW()
                WHERE id = %s
                """,
                (stage_name, workflow_run_id),
            )

        return stage_id

    def complete_fc_import_stage(
        self,
        workflow_run_id: int,
        stage_name: str,
        success: bool,
        message: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Marks the completion of a workflow stage.

        Args:
            workflow_run_id: The ID of the workflow run.
            stage_name: The name of the stage.
            success: True if succeeded, False otherwise.
            message: Optional completion message.
            meta: Optional metadata to store (not currently used in schema but good for extensibility).
        """
        if not db_cursor:
            raise RuntimeError("Database cursor not available")

        status = "succeeded" if success else "failed"

        with db_cursor() as cur:
            cur.execute(
                """
                UPDATE workflow_stage_runs
                SET status = %s,
                    finished_at = NOW(),
                    message = %s
                WHERE workflow_run_id = %s AND stage_key = %s
                """,
                (status, message, workflow_run_id, stage_name),
            )
            if cur.rowcount == 0:
                # Fallback: create if it didn't exist (shouldn't happen if begin was called, but safe)
                cur.execute(
                    """
                    INSERT INTO workflow_stage_runs (
                        workflow_run_id,
                        stage_key,
                        status,
                        finished_at,
                        message
                    ) VALUES (%s, %s, %s, NOW(), %s)
                    """,
                    (workflow_run_id, stage_name, status, message),
                )

        logger.info(
            "Completed stage '%s' for workflow_run %s: %s (msg=%s)",
            stage_name,
            workflow_run_id,
            status,
            message,
        )

        if not success:
             with db_cursor() as cur:
                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET status = 'failed',
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (workflow_run_id,),
                )

    def dispatch_fc_workflow(self, workflow_run_id: int) -> bool:
        """
        Dispatches the FirstCard workflow.
        Currently, this wraps the Celery task invocation.

        Args:
            workflow_run_id: The ID of the workflow run to dispatch.

        Returns:
            True if dispatched successfully.
        """
        # Import here to avoid circular imports if tasks import coordinator
        from services.tasks.workflow_tasks import wf3_firstcard_invoice

        try:
            # We use apply_async to start the task
            wf3_firstcard_invoice.s(workflow_run_id).apply_async()
            
            # Log the dispatch in the workflow history
            self.begin_fc_import_stage(
                workflow_run_id, 
                "dispatch", 
                message="WF3 dispatched to wf3_firstcard_invoice task"
            )
            self.complete_fc_import_stage(
                workflow_run_id, 
                "dispatch", 
                success=True, 
                message="WF3 dispatched successfully"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch WF3 for run {workflow_run_id}: {e}")
            self.begin_fc_import_stage(
                workflow_run_id, 
                "dispatch", 
                message=f"Dispatch failed: {e}"
            )
            self.complete_fc_import_stage(
                workflow_run_id, 
                "dispatch", 
                success=False, 
                message=f"Dispatch failed: {e}"
            )
            return False
