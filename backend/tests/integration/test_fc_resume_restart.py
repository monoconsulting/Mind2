import sys
from unittest.mock import MagicMock

# Mock services.tasks.common to avoid heavy imports
mock_common = MagicMock()
sys.modules["services.tasks.common"] = mock_common

# Define Enums
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

mock_common.InvoiceProcessingStatus = InvoiceProcessingStatus
mock_common.InvoiceDocumentStatus = InvoiceDocumentStatus
mock_common.db_cursor = MagicMock()
mock_common.log_event = MagicMock()

import pytest
from unittest.mock import patch
from flask import Flask
from api.reconciliation_firstcard import recon_bp

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(recon_bp)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@patch("api.reconciliation_firstcard.routes.statements.FirstCardWorkflowCoordinator")
@patch("api.reconciliation_firstcard.routes.statements.transition_processing_status")
@patch("api.reconciliation_firstcard.routes.statements.transition_document_status")
@patch("api.reconciliation_firstcard.routes.statements.log_event")
@patch("api.reconciliation_firstcard.routes.statements.get_workflow_run")
def test_resume_integration(
    mock_get_workflow_run,
    mock_log_event,
    mock_transition_doc,
    mock_transition_proc,
    MockCoordinator,
    client
):
    # Setup mocks
    mock_coordinator = MockCoordinator.return_value
    mock_coordinator.dispatch_fc_workflow.return_value = True
    
    mock_get_workflow_run.return_value = {
        "id": 123,
        "status": "failed",
        "current_stage": "some_stage"
    }
    
    with patch("api.reconciliation_firstcard.routes.statements.db_cursor") as mock_db_cursor:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (123, "failed", "some_stage")
        
        response = client.post("/reconciliation/firstcard/statements/inv-123/resume")
        
        assert response.status_code == 200
        assert response.json["ok"] is True
        
        mock_coordinator.begin_fc_import_stage.assert_called_with(123, "resume_dispatch", message=pytest.any_str)
        mock_coordinator.dispatch_fc_workflow.assert_called_with(123)

@patch("api.reconciliation_firstcard.routes.statements.FirstCardWorkflowCoordinator")
@patch("api.reconciliation_firstcard.routes.statements.transition_processing_status")
@patch("api.reconciliation_firstcard.routes.statements.transition_document_status")
@patch("api.reconciliation_firstcard.routes.statements.log_event")
@patch("api.reconciliation_firstcard.routes.statements.write_invoice_metadata")
def test_restart_integration(
    mock_write_metadata,
    mock_log_event,
    mock_transition_doc,
    mock_transition_proc,
    MockCoordinator,
    client
):
    # Setup mocks
    mock_coordinator = MockCoordinator.return_value
    mock_coordinator.create_workflow_run_for_fc_document.return_value = 456
    mock_coordinator.dispatch_fc_workflow.return_value = True
    
    with patch("api.reconciliation_firstcard.routes.statements.db_cursor") as mock_db_cursor:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = ('{"some": "meta"}',)
        
        response = client.post("/reconciliation/firstcard/statements/inv-123/restart")
        
        assert response.status_code == 200
        assert response.json["ok"] is True
        assert response.json["workflow_run_id"] == 456
        
        mock_coordinator.create_workflow_run_for_fc_document.assert_called_with(
            file_id="inv-123",
            workflow_type="creditcard_invoice",
            workflow_key="WF3_FIRSTCARD_INVOICE"
        )
        mock_coordinator.dispatch_fc_workflow.assert_called_with(456)
