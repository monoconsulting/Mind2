import sys
from unittest.mock import MagicMock

# Mock services.tasks.common to avoid heavy imports
mock_common = MagicMock()
sys.modules["services.tasks.common"] = mock_common

# Define the enums that are needed
class InvoiceProcessingStatus:
    OCR_PENDING = "ocr_pending"
    UPLOADED = "uploaded"
    FAILED = "failed"
    COMPLETED = "completed"
    MATCHING_COMPLETED = "matching_completed"
    READY_FOR_MATCHING = "ready_for_matching"
    AI_PROCESSING = "ai_processing"
    OCR_DONE = "ocr_done"
    value = "some_value"

class InvoiceDocumentStatus:
    MATCHING = "matching"
    IMPORTED = "imported"
    FAILED = "failed"
    PARTIALLY_MATCHED = "partially_matched"
    MATCHED = "matched"
    COMPLETED = "completed"
    value = "some_value"

class AiStatus:
    MANUAL_REVIEW = "manual_review"
    value = "some_value"

mock_common.InvoiceProcessingStatus = InvoiceProcessingStatus
mock_common.InvoiceDocumentStatus = InvoiceDocumentStatus
mock_common.AiStatus = AiStatus
mock_common.db_cursor = MagicMock()
mock_common.log_event = MagicMock()

import pytest
from unittest.mock import patch
from services.tasks.workflow_tasks import wf3_firstcard_invoice

@patch("services.tasks.workflow_tasks.FirstCardWorkflowCoordinator")
@patch("services.tasks.workflow_tasks._ensure_creditcard_pages_and_ocr")
@patch("services.tasks.workflow_tasks.classify_document_internal")
@patch("services.tasks.workflow_tasks.AIService")
@patch("services.tasks.workflow_tasks._persist_creditcard_invoice_main")
@patch("services.tasks.workflow_tasks._persist_creditcard_invoice_items")
@patch("services.tasks.workflow_tasks._persist_invoice_lines")
@patch("services.tasks.workflow_tasks.auto_match_invoice_lines")
@patch("services.tasks.workflow_tasks.refresh_invoice_match_state")
@patch("services.tasks.workflow_tasks.transition_processing_status")
@patch("services.tasks.workflow_tasks.transition_document_status")
@patch("services.tasks.workflow_tasks._load_invoice_metadata")
@patch("services.tasks.workflow_tasks._update_invoice_metadata")
@patch("services.tasks.workflow_tasks.ensure_workflow")
@patch("services.tasks.workflow_tasks._load_unified_file_info")
@patch("services.tasks.workflow_tasks.run_box_enrichment")
def test_wf3_firstcard_invoice_success(
    mock_run_box,
    mock_load_file_info,
    mock_ensure_workflow,
    mock_update_meta,
    mock_load_meta,
    mock_trans_doc,
    mock_trans_proc,
    mock_refresh,
    mock_auto_match,
    mock_persist_lines,
    mock_persist_items,
    mock_persist_main,
    MockAIService,
    mock_classify,
    mock_ensure_ocr,
    MockCoordinator
):
    # Setup mocks
    mock_ensure_workflow.return_value = {"file_id": "inv-123"}
    mock_load_meta.return_value = {}
    mock_load_file_info.return_value = {"file_type": "cc_pdf", "workflow_type": "creditcard_invoice"}
    mock_ensure_ocr.return_value = ("OCR TEXT", {"pages": []})
    
    mock_classify.return_value.document_type = "fc_invoice"
    
    mock_ai_service = MockAIService.return_value
    mock_ai_service.prompt_provider_names = {}
    mock_ai_service.prompt_model_names = {}
    mock_ai_service.prompts = {}
    
    # Mock extraction response
    mock_extraction = MagicMock()
    mock_extraction.lines = [MagicMock(amount_sek=100.0, purchase_date=MagicMock(isoformat=lambda: "2023-01-01"))]
    mock_extraction.header.invoice_number = "INV-001"
    mock_extraction.header.amount_to_pay = 100.0
    mock_extraction.overall_confidence = 0.9
    mock_ai_service.parse_credit_card_invoice.return_value = mock_extraction
    
    mock_persist_main.return_value = 1
    mock_persist_items.return_value = 1
    mock_persist_lines.return_value = 1
    
    mock_auto_match.return_value = (1, 1)
    mock_refresh.return_value = (1, 1)
    mock_run_box.return_value = {"success": True}
    
    # Run the task
    wf3_firstcard_invoice(123)
    
    # Verify coordinator calls
    coordinator = MockCoordinator.return_value
    coordinator.begin_fc_import_stage.assert_any_call(123, "firstcard_invoice", "Workflow running")
    coordinator.complete_fc_import_stage.assert_any_call(123, "firstcard_invoice", success=True, message=pytest.any_str)
    
    # Verify status transitions
    # Note: transition_processing_status is called multiple times.
    # We check if it was called with expected statuses.
    calls = [args[1] for args, _ in mock_trans_proc.call_args_list]
    assert InvoiceProcessingStatus.OCR_DONE in calls
    assert InvoiceProcessingStatus.AI_PROCESSING in calls
    assert InvoiceProcessingStatus.READY_FOR_MATCHING in calls
