import unittest
from unittest.mock import MagicMock, patch
from services.db.files import create_unified_file, DuplicateFileError, UnifiedFile

class TestDbFilesUnifiedFiles(unittest.TestCase):
    
    @patch("services.db.files.db_cursor")
    @patch("services.db.files.create_workflow_run")
    def test_create_unified_file_success(self, mock_create_workflow, mock_db_cursor):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_create_workflow.return_value = 101
        
        result = create_unified_file(
            file_type="receipt",
            original_filename="test.pdf",
            content_hash="hash123",
            submitted_by="user1",
            source="web",
            initial_ai_status="new",
            workflow_type="WF1_RECEIPT"
        )
        
        self.assertIsInstance(result, UnifiedFile)
        self.assertEqual(result.file_type, "receipt")
        self.assertEqual(result.original_filename, "test.pdf")
        self.assertEqual(result.content_hash, "hash123")
        self.assertEqual(result.workflow_run_id, 101)
        
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        self.assertIn("INSERT INTO unified_files", args[0])
        self.assertIn("hash123", args[1])
        
        mock_create_workflow.assert_called_once()

    @patch("services.db.files.db_cursor")
    def test_create_unified_file_duplicate(self, mock_db_cursor):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_cursor.return_value.__enter__.return_value = mock_cursor
        
        mock_cursor.execute.side_effect = Exception("Duplicate entry 'hash123' for key 'idx_content_hash'")
        
        with self.assertRaises(DuplicateFileError):
            create_unified_file(
                file_type="receipt",
                original_filename="test.pdf",
                content_hash="hash123",
                submitted_by="user1",
                source="web",
                initial_ai_status="new"
            )

if __name__ == "__main__":
    unittest.main()
