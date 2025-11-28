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

mock_common.InvoiceProcessingStatus = InvoiceProcessingStatus
mock_common.InvoiceDocumentStatus = InvoiceDocumentStatus
mock_common.db_cursor = MagicMock()
mock_common.log_event = MagicMock()

import pytest
from services.workflow_coordinator import FirstCardWorkflowCoordinator


class TestFirstCardWorkflowCoordinator:
    @pytest.fixture
    def coordinator(self):
        return FirstCardWorkflowCoordinator()

    @pytest.fixture
    def mock_db_cursor(self):
        with patch("services.workflow_coordinator.db_cursor") as mock_cursor:
            mock_conn = MagicMock()
            mock_cursor.return_value.__enter__.return_value = mock_conn
            yield mock_conn

    def test_create_workflow_run_for_fc_document(self, coordinator, mock_db_cursor):
        mock_db_cursor.fetchone.return_value = [123]
        
        run_id = coordinator.create_workflow_run_for_fc_document("file_1")
        
        assert run_id == 123
        mock_db_cursor.execute.assert_called_once()
        args = mock_db_cursor.execute.call_args[0]
        assert "INSERT INTO workflow_runs" in args[0]
        assert args[1] == ("file_1", "creditcard_invoice", "WF3_FIRSTCARD_INVOICE")

    def test_begin_fc_import_stage_new(self, coordinator, mock_db_cursor):
        # Setup: Stage does not exist
        mock_db_cursor.fetchone.side_effect = [None, [456]]
        
        stage_id = coordinator.begin_fc_import_stage(123, "fc_ocr", "Starting OCR")
        
        assert stage_id == 456
        # First check for existence
        assert "SELECT id FROM workflow_stage_runs" in mock_db_cursor.execute.call_args_list[0][0][0]
        # Then insert
        assert "INSERT INTO workflow_stage_runs" in mock_db_cursor.execute.call_args_list[1][0][0]
        assert mock_db_cursor.execute.call_args_list[1][0][1] == (123, "fc_ocr", "Starting OCR")

    def test_begin_fc_import_stage_existing(self, coordinator, mock_db_cursor):
        # Setup: Stage exists
        mock_db_cursor.fetchone.return_value = [456]
        
        stage_id = coordinator.begin_fc_import_stage(123, "fc_ocr", "Restarting OCR")
        
        assert stage_id == 456
        # Update existing
        assert "UPDATE workflow_stage_runs" in mock_db_cursor.execute.call_args_list[1][0][0]
        assert "SET status = 'running'" in mock_db_cursor.execute.call_args_list[1][0][0]

    def test_complete_fc_import_stage_success(self, coordinator, mock_db_cursor):
        mock_db_cursor.rowcount = 1
        
        coordinator.complete_fc_import_stage(123, "fc_ocr", True, "OCR Done")
        
        assert "UPDATE workflow_stage_runs" in mock_db_cursor.execute.call_args[0][0]
        assert "SET status = %s" in mock_db_cursor.execute.call_args[0][0]
        assert mock_db_cursor.execute.call_args[0][1] == ("succeeded", "OCR Done", 123, "fc_ocr")

    def test_complete_fc_import_stage_failure(self, coordinator, mock_db_cursor):
        mock_db_cursor.rowcount = 1
        
        coordinator.complete_fc_import_stage(123, "fc_ocr", False, "OCR Failed")
        
        assert mock_db_cursor.execute.call_args[0][1] == ("failed", "OCR Failed", 123, "fc_ocr")

    @patch("services.tasks.workflow_tasks.wf3_firstcard_invoice")
    def test_dispatch_fc_workflow(self, mock_task, coordinator, mock_db_cursor):
        # Mock the task chain
        mock_task.s.return_value.apply_async = MagicMock()
        
        # Mock DB calls for begin/complete stage
        mock_db_cursor.fetchone.return_value = [999] # for begin stage
        mock_db_cursor.rowcount = 1 # for complete stage

        success = coordinator.dispatch_fc_workflow(123)
        
        assert success is True
        mock_task.s.assert_called_with(123)
        mock_task.s.return_value.apply_async.assert_called_once()
