import unittest
from unittest.mock import MagicMock, patch, call
from services.ftp_service import FTPConfig, create_ftp_client, list_files, download_file, delete_file, ftp_connection

class TestFTPService(unittest.TestCase):

    def setUp(self):
        self.config = FTPConfig(
            host="ftp.example.com",
            port=21,
            user="user",
            password="password",
            passive=True,
            remote_directory="/upload",
            use_tls=False,
            allowed_extensions=["pdf", "jpg"]
        )

    @patch("services.ftp_service.FTP")
    def test_create_ftp_client_basic(self, mock_ftp_cls):
        mock_ftp = MagicMock()
        mock_ftp_cls.return_value = mock_ftp
        
        client = create_ftp_client(self.config)
        
        mock_ftp_cls.assert_called_once()
        mock_ftp.connect.assert_called_with(host="ftp.example.com", port=21, timeout=20)
        mock_ftp.login.assert_called_with(user="user", passwd="password")
        mock_ftp.set_pasv.assert_called_with(True)
        mock_ftp.cwd.assert_called_with("/upload")
        self.assertEqual(client, mock_ftp)

    @patch("services.ftp_service.FTP_TLS")
    def test_create_ftp_client_tls(self, mock_ftp_tls_cls):
        self.config.use_tls = True
        mock_ftp = MagicMock()
        mock_ftp_tls_cls.return_value = mock_ftp
        
        client = create_ftp_client(self.config)
        
        mock_ftp_tls_cls.assert_called_once()
        mock_ftp.connect.assert_called_with(host="ftp.example.com", port=21, timeout=20)
        mock_ftp.prot_p.assert_called_once()
        self.assertEqual(client, mock_ftp)

    def test_list_files(self):
        mock_ftp = MagicMock()
        # Mock nlst to return a mix of allowed, disallowed, and json files
        mock_ftp.nlst.return_value = ["file1.pdf", "file2.jpg", "file3.txt", "metadata.json", "file1.pdf.json"]
        
        files = list_files(mock_ftp, self.config)
        
        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].filename, "file1.pdf")
        self.assertEqual(files[1].filename, "file2.jpg")

    def test_download_file(self):
        mock_ftp = MagicMock()
        content = b"file content"
        
        # Mock retrbinary to write content to the callback
        def side_effect(cmd, callback):
            callback(content)
            
        mock_ftp.retrbinary.side_effect = side_effect
        
        result = download_file(mock_ftp, "file1.pdf")
        
        self.assertEqual(result, content)
        mock_ftp.retrbinary.assert_called_with("RETR file1.pdf", unittest.mock.ANY)

    def test_delete_file(self):
        mock_ftp = MagicMock()
        
        success = delete_file(mock_ftp, "file1.pdf")
        
        self.assertTrue(success)
        mock_ftp.delete.assert_called_with("file1.pdf")

    def test_delete_file_error(self):
        mock_ftp = MagicMock()
        mock_ftp.delete.side_effect = Exception("Delete failed")
        
        success = delete_file(mock_ftp, "file1.pdf")
        
        self.assertFalse(success)

    @patch("services.ftp_service.create_ftp_client")
    def test_ftp_connection_context_manager(self, mock_create):
        mock_ftp = MagicMock()
        mock_create.return_value = mock_ftp
        
        with ftp_connection(self.config) as ftp:
            self.assertEqual(ftp, mock_ftp)
            
        mock_ftp.quit.assert_called_once()

if __name__ == "__main__":
    unittest.main()
