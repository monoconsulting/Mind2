from __future__ import annotations

import logging
import os
import ssl
import uuid
from dataclasses import dataclass
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from services.storage import FileStorage

logger = logging.getLogger(__name__)
try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore
try:
    from services.db.files import set_ai_status
except Exception:  # pragma: no cover
    def set_ai_status(file_id: str, status: str) -> bool:  # type: ignore
        _ = (file_id, status)
        return False


@dataclass
class FetchResult:
    downloaded: List[Tuple[str, str]]  # (id, filename)
    skipped: List[str]
    errors: List[str]


def _allowed(name: str, exts: List[str]) -> bool:
    name_l = name.lower()
    return any(name_l.endswith("." + ext.lower()) for ext in exts)


def _insert_unified_file(file_id: str) -> None:
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "INSERT INTO unified_files (id, file_type, created_at) "
                    "VALUES (%s, %s, NOW())"
                ),
                (file_id, "receipt"),
            )
    except Exception:
        # best-effort
        pass


def _storage() -> FileStorage:
    base = os.getenv("STORAGE_DIR", "/data/storage")
    return FileStorage(base)


def fetch_from_local_inbox() -> FetchResult:
    inbox = os.getenv("FTP_LOCAL_DIR")
    move_dir = os.getenv("FTP_LOCAL_MOVE_DIR")
    allowed_exts = [e.strip() for e in (os.getenv("FTP_ALLOWED_EXT", "pdf,jpg,jpeg,png,txt").split(",")) if e.strip()]
    if not inbox:
        return FetchResult(downloaded=[], skipped=[], errors=["FTP_LOCAL_DIR not set"])
    inbox_path = Path(inbox)
    if not inbox_path.exists():
        return FetchResult(downloaded=[], skipped=[], errors=[f"Local inbox not found: {inbox}"])

    downloaded: List[Tuple[str, str]] = []
    skipped: List[str] = []
    errors: List[str] = []
    fs = _storage()
    for p in sorted(inbox_path.iterdir()):
        if not p.is_file():
            continue
        if not _allowed(p.name, allowed_exts):
            skipped.append(p.name)
            continue
        try:
            file_id = str(uuid.uuid4())
            data = p.read_bytes()
            fs.save(file_id, p.name, data)
            _insert_unified_file(file_id)
            set_ai_status(file_id, "new")
            downloaded.append((file_id, p.name))
            if move_dir:
                dst_dir = Path(move_dir)
                dst_dir.mkdir(parents=True, exist_ok=True)
                p.rename(dst_dir / p.name)
        except Exception as e:
            errors.append(f"{p.name}: {e}")
    return FetchResult(downloaded=downloaded, skipped=skipped, errors=errors)


def fetch_from_ftp() -> FetchResult:
    host = os.getenv("FTP_HOST")
    logger.info(f"FTP DEBUG: Starting fetch_from_ftp, host={host}")

    if not host:
        logger.info("FTP DEBUG: No host configured, falling back to local inbox mode")
        return fetch_from_local_inbox()

    port = int(os.getenv("FTP_PORT", "21"))
    user = os.getenv("FTP_USER", "anonymous")
    password = os.getenv("FTP_PASS", "anonymous@")
    passive = os.getenv("FTP_PASSIVE", "true").lower() not in {"false", "0", "no"}
    remote_dir = os.getenv("FTP_REMOTE_DIR", "/")
    use_tls = os.getenv("FTP_TLS", "false").lower() in {"1", "true", "yes"}
    allowed_exts = [e.strip() for e in (os.getenv("FTP_ALLOWED_EXT", "pdf,jpg,jpeg,png").split(",")) if e.strip()]
    delete_after = os.getenv("FTP_DELETE_AFTER", "false").lower() in {"1", "true", "yes"}

    logger.info(f"FTP DEBUG: Config - host={host}, port={port}, user={user}, remote_dir={remote_dir}")
    logger.info(f"FTP DEBUG: Config - use_tls={use_tls}, passive={passive}, allowed_exts={allowed_exts}")

    downloaded: List[Tuple[str, str]] = []
    skipped: List[str] = []
    errors: List[str] = []

    fs = _storage()
    ftp = None
    try:
        logger.info("FTP DEBUG: Creating FTP connection...")
        if use_tls:
            ftp = FTP_TLS()
            ftp.context = ssl.create_default_context()
            logger.info("FTP DEBUG: Using FTP_TLS")
        else:
            ftp = FTP()
            logger.info("FTP DEBUG: Using regular FTP")

        logger.info(f"FTP DEBUG: Connecting to {host}:{port}")
        ftp.connect(host=host, port=port, timeout=20)
        logger.info("FTP DEBUG: Connection established, attempting login...")

        ftp.login(user=user, passwd=password)
        logger.info("FTP DEBUG: Login successful")

        if use_tls and isinstance(ftp, FTP_TLS):
            logger.info("FTP DEBUG: Setting TLS protection mode")
            ftp.prot_p()

        ftp.set_pasv(passive)
        logger.info(f"FTP DEBUG: Set passive mode to {passive}")

        if remote_dir:
            logger.info(f"FTP DEBUG: Changing to directory: {remote_dir}")
            ftp.cwd(remote_dir)
            logger.info(f"FTP DEBUG: Successfully changed to directory: {remote_dir}")

        logger.info("FTP DEBUG: Getting file list...")
        names = ftp.nlst()
        logger.info(f"FTP DEBUG: Found {len(names)} files: {names[:10]}...")  # Show first 10
        logger.info(f"FTP DEBUG: Allowed extensions: {allowed_exts}")

        for name in names:
            logger.info(f"FTP DEBUG: Checking file: {name}")
            if not _allowed(name, allowed_exts):
                logger.info(f"FTP DEBUG: SKIPPED (extension): {name}")
                skipped.append(name)
                continue
            logger.info(f"FTP DEBUG: ALLOWED: {name}")
            try:
                file_id = str(uuid.uuid4())
                logger.info(f"FTP DEBUG: Downloading {name} with file_id {file_id}")
                buf = bytearray()
                ftp.retrbinary(f"RETR {name}", buf.extend)
                logger.info(f"FTP DEBUG: Downloaded {len(buf)} bytes for {name}")

                fs.save(file_id, name, bytes(buf))
                _insert_unified_file(file_id)
                set_ai_status(file_id, "new")
                downloaded.append((file_id, name))
                logger.info(f"FTP DEBUG: Successfully saved {name}")

                if delete_after:
                    try:
                        ftp.delete(name)
                        logger.info(f"FTP DEBUG: Deleted {name} from FTP server")
                    except error_perm:
                        logger.info(f"FTP DEBUG: Could not delete {name} - permission denied")
            except Exception as e:
                logger.error(f"FTP DEBUG: Error processing {name}: {e}")
                errors.append(f"{name}: {e}")
    except Exception as e:
        logger.error(f"FTP DEBUG: Connection error: {e}")
        errors.append(str(e))
    finally:
        try:
            if ftp is not None:
                logger.info("FTP DEBUG: Closing FTP connection")
                ftp.quit()
        except Exception:
            pass

    logger.info(f"FTP DEBUG: Fetch complete - downloaded: {len(downloaded)}, skipped: {len(skipped)}, errors: {len(errors)}")
    return FetchResult(downloaded=downloaded, skipped=skipped, errors=errors)
