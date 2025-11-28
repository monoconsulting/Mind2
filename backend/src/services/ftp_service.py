from __future__ import annotations

import logging
import os
import ssl
from dataclasses import dataclass, field
from ftplib import FTP, FTP_TLS
from typing import List, Optional, Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

@dataclass
class FTPConfig:
    """Configuration for FTP connection and operations."""
    host: str
    port: int = 21
    user: str = "anonymous"
    password: str = "anonymous@"
    passive: bool = True
    remote_directory: str = "/"
    use_tls: bool = False
    allowed_extensions: List[str] = field(default_factory=lambda: ["pdf", "jpg", "jpeg", "png"])
    delete_after: bool = False

    @classmethod
    def from_env(cls) -> FTPConfig:
        """Create configuration from environment variables."""
        host = os.getenv("FTP_HOST")
        if not host:
            raise ValueError("FTP_HOST environment variable is not set")

        return cls(
            host=host,
            port=int(os.getenv("FTP_PORT", "21")),
            user=os.getenv("FTP_USER", "anonymous"),
            password=os.getenv("FTP_PASS", "anonymous@"),
            passive=os.getenv("FTP_PASSIVE", "true").lower() not in {"false", "0", "no"},
            remote_directory=os.getenv("FTP_REMOTE_DIR", "/"),
            use_tls=os.getenv("FTP_TLS", "false").lower() in {"1", "true", "yes"},
            allowed_extensions=[e.strip() for e in (os.getenv("FTP_ALLOWED_EXT", "pdf,jpg,jpeg,png").split(",")) if e.strip()],
            delete_after=os.getenv("FTP_DELETE_AFTER", "false").lower() in {"1", "true", "yes"},
        )

@dataclass
class RemoteFileInfo:
    """Information about a file on the remote FTP server."""
    filename: str
    size: Optional[int] = None

def create_ftp_client(config: FTPConfig) -> FTP:
    """
    Create and connect an FTP client based on configuration.
    
    Args:
        config: FTPConfig object with connection details.
        
    Returns:
        Connected FTP or FTP_TLS instance.
    """
    logger.info(f"Connecting to FTP: {config.host}:{config.port} (TLS={config.use_tls})")
    
    if config.use_tls:
        ftp = FTP_TLS()
        ftp.context = ssl.create_default_context()
    else:
        ftp = FTP()

    ftp.connect(host=config.host, port=config.port, timeout=20)
    ftp.login(user=config.user, passwd=config.password)
    
    if config.use_tls and isinstance(ftp, FTP_TLS):
        ftp.prot_p()
        
    ftp.set_pasv(config.passive)
    
    if config.remote_directory and config.remote_directory != "/":
        ftp.cwd(config.remote_directory)
        
    return ftp

@contextmanager
def ftp_connection(config: FTPConfig) -> Generator[FTP, None, None]:
    """
    Context manager for FTP connection.
    
    Yields:
        Connected FTP client.
    """
    ftp = None
    try:
        ftp = create_ftp_client(config)
        yield ftp
    finally:
        if ftp:
            try:
                ftp.quit()
            except Exception:
                pass

def list_files(ftp: FTP, config: FTPConfig) -> List[RemoteFileInfo]:
    """
    List files in the current directory of the FTP connection.
    
    Args:
        ftp: Connected FTP client.
        config: FTPConfig for filtering rules.
        
    Returns:
        List of RemoteFileInfo objects.
    """
    files: List[RemoteFileInfo] = []
    try:
        names = ftp.nlst()
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return []

    for name in names:
        # Skip JSON metadata files in the main list, they are fetched separately if needed
        if name.lower().endswith('.json'):
            continue
            
        # Check extension
        if not any(name.lower().endswith("." + ext.lower()) for ext in config.allowed_extensions):
            continue
            
        files.append(RemoteFileInfo(filename=name))
        
    return files

def download_file(ftp: FTP, remote_filename: str) -> bytes:
    """
    Download a file from the FTP server.
    
    Args:
        ftp: Connected FTP client.
        remote_filename: Name of the file to download.
        
    Returns:
        File content as bytes.
    """
    buf = bytearray()
    ftp.retrbinary(f"RETR {remote_filename}", buf.extend)
    return bytes(buf)

def delete_file(ftp: FTP, remote_filename: str) -> bool:
    """
    Delete a file from the FTP server.
    
    Args:
        ftp: Connected FTP client.
        remote_filename: Name of the file to delete.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        ftp.delete(remote_filename)
        return True
    except Exception as e:
        logger.error(f"Error deleting file {remote_filename}: {e}")
        return False
