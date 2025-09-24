from __future__ import annotations

import os
import ssl
import uuid
from dataclasses import dataclass
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from services.storage import FileStorage
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
    if not host:
        # Fallback to local inbox mode
        return fetch_from_local_inbox()
    port = int(os.getenv("FTP_PORT", "21"))
    user = os.getenv("FTP_USER", "anonymous")
    password = os.getenv("FTP_PASS", "anonymous@")
    passive = os.getenv("FTP_PASSIVE", "true").lower() not in {"false", "0", "no"}
    remote_dir = os.getenv("FTP_REMOTE_DIR", "/")
    use_tls = os.getenv("FTP_TLS", "false").lower() in {"1", "true", "yes"}
    allowed_exts = [e.strip() for e in (os.getenv("FTP_ALLOWED_EXT", "pdf,jpg,jpeg,png").split(",")) if e.strip()]
    delete_after = os.getenv("FTP_DELETE_AFTER", "false").lower() in {"1", "true", "yes"}

    downloaded: List[Tuple[str, str]] = []
    skipped: List[str] = []
    errors: List[str] = []

    fs = _storage()
    ftp = None
    try:
        if use_tls:
            ftp = FTP_TLS()
            ftp.context = ssl.create_default_context()
        else:
            ftp = FTP()
        ftp.connect(host=host, port=port, timeout=20)
        ftp.login(user=user, passwd=password)
        if use_tls and isinstance(ftp, FTP_TLS):
            ftp.prot_p()
        ftp.set_pasv(passive)
        if remote_dir:
            ftp.cwd(remote_dir)
        names = ftp.nlst()
        for name in names:
            # Attempt to filter by extension
            if not _allowed(name, allowed_exts):
                skipped.append(name)
                continue
            try:
                file_id = str(uuid.uuid4())
                buf = bytearray()
                ftp.retrbinary(f"RETR {name}", buf.extend)
                fs.save(file_id, name, bytes(buf))
                _insert_unified_file(file_id)
                set_ai_status(file_id, "new")
                downloaded.append((file_id, name))
                if delete_after:
                    try:
                        ftp.delete(name)
                    except error_perm:
                        # ignore delete permission errors
                        pass
            except Exception as e:
                errors.append(f"{name}: {e}")
    except Exception as e:
        errors.append(str(e))
    finally:
        try:
            if ftp is not None:
                ftp.quit()
        except Exception:
            pass

    return FetchResult(downloaded=downloaded, skipped=skipped, errors=errors)
