import unittest
from unittest.mock import MagicMock, patch, call
from services.fetch_ftp import fetch_from_ftp, FetchResult
from services.ftp_service import FTPConfig, RemoteFileInfo

class TestFetchFtpRefactored(unittest.TestCase):

    @patch("services.fetch_ftp.FTPConfig")
    @patch("services.fetch_ftp.ftp_connection")
    @patch("services.fetch_ftp.list_files")
    @patch("services.fetch_ftp.download_file")
    @patch("services.fetch_ftp.delete_file")
    @patch("services.fetch_ftp._storage")
    @patch("services.fetch_ftp._insert_unified_file")
    @patch("services.fetch_ftp._history")
    def test_fetch_from_ftp_success(
        self,
        mock_history,
        mock_insert,
        mock_storage,
        mock_delete,
        mock_download,
        mock_list,
        mock_connection,
        mock_config_cls
    ):
        # Setup mocks
        mock_config = MagicMock()
        mock_config.host = "test.host"
        mock_config.delete_after = False
        mock_config_cls.from_env.return_value = mock_config
        
        mock_ftp = MagicMock()
        mock_connection.return_value.__enter__.return_value = mock_ftp
        
        mock_list.return_value = [RemoteFileInfo(filename="test.pdf")]
        
        # Mock download for metadata (fails) and file (succeeds)
        def download_side_effect(ftp, filename):
            if filename.endswith(".json"):
                raise Exception("No metadata")
            return b"file content"
        
        mock_download.side_effect = download_side_effect
        
        mock_fs = MagicMock()
        mock_storage.return_value = mock_fs
        
        mock_insert.return_value = 123

        # Run function
        result = fetch_from_ftp()

        # Verify
        self.assertEqual(len(result.downloaded), 1)
        self.assertEqual(result.downloaded[0][1], "test.pdf")
        self.assertEqual(len(result.errors), 0)
        
        mock_config_cls.from_env.assert_called_once()
        mock_connection.assert_called_once_with(mock_config)
        mock_list.assert_called_once_with(mock_ftp, mock_config)
        mock_download.assert_any_call(mock_ftp, "test.pdf")
        mock_insert.assert_called_once()
        mock_fs.save.assert_called_once()

    @patch("services.fetch_ftp.FTPConfig")
    def test_fetch_from_ftp_no_host(self, mock_config_cls):
        mock_config_cls.from_env.side_effect = ValueError("No host")
        
        with patch("services.fetch_ftp.fetch_from_local_inbox") as mock_local:
            mock_local.return_value = FetchResult([], [], [])
            result = fetch_from_ftp()
            mock_local.assert_called_once()

    @patch("services.fetch_ftp.create_unified_file")
    @patch("services.fetch_ftp._history")
    @patch("services.fetch_ftp._get_file_category")
    @patch("services.fetch_ftp.begin_import_stage")
    @patch("services.fetch_ftp.complete_import_stage")
    @patch("services.fetch_ftp.dispatch_workflow")
    def test_insert_unified_file(self, mock_dispatch, mock_complete, mock_begin, mock_category, mock_history, mock_create):
        from services.fetch_ftp import _insert_unified_file
        
        mock_category.return_value = 1
        mock_create.return_value.workflow_run_id = 999
        mock_dispatch.return_value = True
        
        metadata = {
            'file_id': 'orig_id',
            'original_name': 'orig.pdf',
            'timestamp': '2023-01-01T12:00:00',
            'file_size': 100,
            'file_type': 'application/pdf'
        }
        
        run_id = _insert_unified_file("new_id", "test.pdf", metadata, "hash123", source="ftp")
        
        self.assertEqual(run_id, 999)
        mock_create.assert_called_once()
        args = mock_create.call_args[1]
        self.assertEqual(args['file_id'], "new_id")
        self.assertEqual(args['content_hash'], "hash123")
        self.assertEqual(args['submitted_by'], "ftp")
        self.assertEqual(args['source'], "ftp")
        self.assertEqual(args['file_category'], 1)
        self.assertEqual(args['workflow_type'], "WF1_RECEIPT")
        
        mock_dispatch.assert_called_once_with(999)

if __name__ == "__main__":
    unittest.main()
