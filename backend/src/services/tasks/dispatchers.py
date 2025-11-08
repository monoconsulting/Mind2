from __future__ import annotations

from .workflow_state import get_workflow_run, mark_stage


def dispatch_workflow(workflow_run_id: int) -> bool:
    """Dispatch workflow based on workflow_key."""
    wfr = get_workflow_run(workflow_run_id)
    if not wfr:
        return False

    workflow_key = wfr.get("workflow_key")

    if not workflow_key:
        mark_stage(workflow_run_id, "dispatch", "failed", message="Workflow key is missing.")
        return False

    try:
        if workflow_key == "WF1_RECEIPT":
            from .ocr_tasks import wf1_run_ocr
            from .ai_pipeline_tasks import wf1_finalize, wf1_run_ai_pipeline

            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF1 dispatched to new wf1.* chain.")
            (wf1_run_ocr.s(workflow_run_id) | wf1_run_ai_pipeline.s() | wf1_finalize.s()).apply_async()
            return True

        if workflow_key == "WF2_PDF_SPLIT":
            from .ocr_tasks import wf2_prepare_pdf_pages

            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF2 dispatched to new wf2.* chain.")
            wf2_prepare_pdf_pages.s(workflow_run_id).apply_async()
            return True

        if workflow_key == "WF3_FIRSTCARD_INVOICE":
            from .creditcard_tasks import wf3_firstcard_invoice

            mark_stage(workflow_run_id, "dispatch", "succeeded", message="WF3 dispatched to new wf3.* chain.")
            wf3_firstcard_invoice.s(workflow_run_id).apply_async()
            return True

        mark_stage(
            workflow_run_id,
            "dispatch",
            "failed",
            message=f"Unknown workflow_key: {workflow_key}",
        )
        return False

    except Exception as exc:
        mark_stage(workflow_run_id, "dispatch", "failed", message=f"Dispatch exception: {exc}")
        return False


__all__ = ["dispatch_workflow"]
