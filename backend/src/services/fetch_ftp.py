from __future__ import annotations

import hashlib
import json
import logging
import os
import ssl
import uuid
import re
from dataclasses import dataclass
from datetime import datetime
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from services.storage import FileStorage
from services.tasks import dispatch_workflow
from services.workflow_runs import create_workflow_run

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


INSERT_HISTORY_SQL = """
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def _history(
    file_id: str,
    job: str,
    status: str,
    ai_stage_name: str | None = None,
    log_text: str | None = None,
    error_message: str | None = None,
    confidence: float | None = None,
    processing_time_ms: int | None = None,
    provider: str | None = None,
    model_name: str | None = None,
) -> None:
    """Log processing history with detailed information."""
    if db_cursor is None:
        return
    try:
        with db_cursor() as cur:
            cur.execute(
                INSERT_HISTORY_SQL,
                (
                    file_id,
                    job,
                    status,
                    ai_stage_name,
                    log_text,
                    error_message,
                    confidence,
                    processing_time_ms,
                    provider,
                    model_name,
                ),
            )
    except Exception:
        # best-effort history
        pass


@dataclass
class FetchResult:
    downloaded: List[Tuple[str, str]]  # (id, filename)
    skipped: List[str]
    errors: List[str]


def _allowed(name: str, exts: List[str]) -> bool:
    """Check if file extension is allowed"""
    name_l = name.lower()
    # Skip JSON metadata files
    if name_l.endswith('.json'):
        return False
    return any(name_l.endswith("." + ext.lower()) for ext in exts)


def _get_file_suffix(filename: str) -> str:
    """Extract file extension without dot"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def _get_file_category(file_suffix: str) -> Optional[int]:
    """Get file category ID based on file suffix"""
    if db_cursor is None or not file_suffix:
        return None

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT fs.file_type
                FROM file_suffix fs
                WHERE LOWER(fs.file_ending) = LOWER(%s)
                """,
                (file_suffix,)
            )
            result = cur.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting file category: {e}")
        return None


def _load_metadata(file_path: Path) -> Dict[str, Any]:
    """Load metadata from JSON file if it exists"""
    json_path = Path(str(file_path) + '.json')
    if json_path.exists():
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata from {json_path}: {e}")
    return {}


def _insert_unified_file(
    file_id: str,
    filename: str,
    metadata: Dict[str, Any],
    content_hash: str
) -> None:
    """Insert file record with metadata from FTP. AI will populate business data later."""
    if db_cursor is None:
        return

    try:
        file_suffix = _get_file_suffix(filename)
        file_category = _get_file_category(file_suffix)

        # Extract ONLY metadata fields (file system data, NOT business data)
        original_file_id = metadata.get('file_id')
        original_file_name = metadata.get('original_name')
        file_creation_timestamp = metadata.get('timestamp')
        original_file_size = metadata.get('file_size')
        mime_type = metadata.get('file_type')

        # Convert datetime strings to datetime objects if needed
        if file_creation_timestamp and isinstance(file_creation_timestamp, str):
            try:
                # Handle ISO format with timezone: 2025-09-07T19:33:00+02:00
                # Remove timezone info for MySQL compatibility
                timestamp_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', file_creation_timestamp)
                file_creation_timestamp = datetime.fromisoformat(timestamp_clean.replace('T', ' '))
            except:
                file_creation_timestamp = None

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO unified_files (
                    id, file_type, created_at, content_hash,
                    file_category, file_suffix, original_filename,
                    original_file_id, original_file_name, file_creation_timestamp,
                    original_file_size, mime_type, submitted_by, ai_status, ocr_raw, other_data
                ) VALUES (
                    %s, %s, NOW(), %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    file_id, "receipt", content_hash,
                    file_category, file_suffix, filename,
                    original_file_id, original_file_name, file_creation_timestamp,
                    original_file_size, mime_type, 'ftp', 'ftp_fetched', '', '{}'
                )
            )
            logger.info(f"Inserted unified_file {file_id} with metadata and hash {content_hash[:16]}...")

            # Log successful FTP fetch
            file_size = metadata.get('file_size', 'unknown')
            _history(
                file_id=file_id,
                job="ftp_fetch",
                status="success",
                ai_stage_name="FTP-FileFetched",
                log_text=f"File fetched from FTP: filename={filename}, size={file_size} bytes, hash={content_hash[:16]}..., metadata_fields={list(metadata.keys())}",
                provider="ftp",
            )
    except Exception as e:
        # Check for duplicate hash
        if 'Duplicate entry' in str(e) and 'idx_content_hash' in str(e):
            logger.warning(f"Skipping duplicate file {filename} (hash: {content_hash[:16]}...)")
            raise ValueError("Duplicate file")
        logger.error(f"Error inserting unified file: {e}")
        raise


def _dispatch_receipt_workflow(file_id: str, content_hash: str, source_channel: str) -> None:
    """Create and dispatch a WF1 workflow for the fetched file."""
    workflow_run_id = create_workflow_run(
        workflow_key="WF1_RECEIPT",
        source_channel=source_channel,
        file_id=file_id,
        content_hash=content_hash,
    )
    if not workflow_run_id:
        logger.error("Failed to create workflow run for FTP file %s", file_id)
        return

    if not dispatch_workflow(workflow_run_id):
        logger.error(
            "Dispatch of workflow_run %s failed for file %s",
            workflow_run_id,
            file_id,
        )
        return

    set_ai_status(file_id, "processing")
    logger.info(
        "Dispatched WF1 workflow (run_id=%s) for FTP file %s",
        workflow_run_id,
        file_id,
    )


def _insert_file_location(file_id: str, location: Dict[str, Any]) -> None:
    """Insert file location data"""
    if db_cursor is None or not location:
        return

    try:
        # Try new JSON format first (latitude/longitude)
        lat = location.get('latitude') or location.get('lat')
        lon = location.get('longitude') or location.get('lon')
        acc = location.get('acc')

        # Convert string coordinates to float if needed
        if isinstance(lat, str):
            lat = float(lat)
        if isinstance(lon, str):
            lon = float(lon)

        if lat is not None and lon is not None:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO file_locations (file_id, lat, lon, acc, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (file_id, lat, lon, acc)
                )
            logger.info(f"Inserted location for file {file_id}: lat={lat}, lon={lon}")
    except Exception as e:
        logger.error(f"Error inserting file location: {e}")


def _insert_file_tags(file_id: str, tags: List[Any]) -> None:
    """Insert file tags"""
    if db_cursor is None or not tags:
        return

    try:
        with db_cursor() as cur:
            for tag in tags:
                try:
                    # Convert tag ID to string if it's numeric
                    tag_str = str(tag)
                    cur.execute(
                        """
                        INSERT INTO file_tags (file_id, tag, created_at)
                        VALUES (%s, %s, NOW())
                        """,
                        (file_id, tag_str)
                    )
                except Exception as e:
                    logger.warning(f"Could not insert tag {tag} for file {file_id}: {e}")
        logger.info(f"Inserted {len(tags)} tags for file {file_id}")
    except Exception as e:
        logger.error(f"Error inserting file tags: {e}")


def _storage() -> FileStorage:
    base = os.getenv("STORAGE_DIR", "/data/storage")
    return FileStorage(base)


def fetch_from_local_inbox() -> FetchResult:
    """Fetch files from local inbox directory with metadata support"""
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

    # Process files (skip JSON metadata files)
    for p in sorted(inbox_path.iterdir()):
        if not p.is_file():
            continue

        # Skip JSON metadata files
        if p.suffix.lower() == '.json':
            continue

        if not _allowed(p.name, allowed_exts):
            skipped.append(p.name)
            continue

        try:
            file_id = str(uuid.uuid4())
            data = p.read_bytes()

            # Calculate content hash for duplicate detection
            content_hash = hashlib.sha256(data).hexdigest()
            logger.info(f"Local: Processing {p.name} - hash {content_hash[:16]}...")

            # Load metadata from JSON file if it exists
            metadata = _load_metadata(p)
            # Add file size to metadata for logging
            metadata['file_size'] = len(data)

            # Insert file record with metadata and hash (handles duplicates)
            try:
                _insert_unified_file(file_id, p.name, metadata, content_hash)
            except ValueError as ve:
                if "Duplicate file" in str(ve):
                    skipped.append(p.name)
                    logger.info(f"Local: Skipped duplicate file {p.name}")
                    continue
                raise

            # Save file to storage
            fs.save(file_id, p.name, data)

            # Insert location data if available
            if 'location' in metadata:
                _insert_file_location(file_id, metadata['location'])

            # Insert tags if available
            if 'tags' in metadata:
                _insert_file_tags(file_id, metadata['tags'])

            # Create workflow run for receipts uploaded via local inbox
            _dispatch_receipt_workflow(file_id, content_hash, "ftp_local")

            downloaded.append((file_id, p.name))
            logger.info(f"Local: Successfully processed {p.name} as {file_id}")

            # Move files if configured
            if move_dir:
                dst_dir = Path(move_dir)
                dst_dir.mkdir(parents=True, exist_ok=True)

                # Move the file
                p.rename(dst_dir / p.name)

                # Move the JSON metadata file if it exists
                json_path = Path(str(p) + '.json')
                if json_path.exists():
                    json_path.rename(dst_dir / json_path.name)

        except Exception as e:
            logger.error(f"Local: Error processing {p.name}: {e}")
            errors.append(f"{p.name}: {e}")
            # Log error if we have a file_id
            if 'file_id' in locals():
                _history(
                    file_id=file_id,
                    job="ftp_fetch",
                    status="error",
                    ai_stage_name="FTP-FileFetched",
                    log_text=f"Failed to process file from local inbox: {p.name}",
                    error_message=f"{type(e).__name__}: {str(e)}",
                    provider="ftp",
                )

    return FetchResult(downloaded=downloaded, skipped=skipped, errors=errors)


def fetch_from_ftp() -> FetchResult:
    """Fetch files from FTP server with metadata support"""
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
    metadata_cache: Dict[str, Dict[str, Any]] = {}

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
        logger.info(f"FTP DEBUG: Found {len(names)} files: {names[:10]}...")

        # First, download all JSON metadata files
        for name in names:
            if name.lower().endswith('.json'):
                try:
                    buf = bytearray()
                    ftp.retrbinary(f"RETR {name}", buf.extend)
                    metadata = json.loads(buf.decode('utf-8'))
                    base_name = name[:-5]  # Remove .json extension
                    metadata_cache[base_name] = metadata
                    logger.info(f"FTP DEBUG: Loaded metadata for {base_name}")
                except Exception as e:
                    logger.error(f"FTP DEBUG: Error loading metadata {name}: {e}")

        # Process actual files
        for name in names:
            logger.info(f"FTP DEBUG: Checking file: {name}")

            # Skip JSON metadata files
            if name.lower().endswith('.json'):
                continue

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

                # Calculate content hash for duplicate detection
                data = bytes(buf)
                content_hash = hashlib.sha256(data).hexdigest()
                logger.info(f"FTP DEBUG: Calculated hash {content_hash[:16]}... for {name}")

                # Get metadata if available
                metadata = metadata_cache.get(name, {})
                # Add file size to metadata for logging
                metadata['file_size'] = len(data)

                # Insert file record with metadata and hash (handles duplicates)
                try:
                    _insert_unified_file(file_id, name, metadata, content_hash)
                except ValueError as ve:
                    if "Duplicate file" in str(ve):
                        skipped.append(name)
                        logger.info(f"FTP DEBUG: SKIPPED duplicate file {name}")
                        # Delete from FTP if configured
                        if delete_after:
                            try:
                                ftp.delete(name)
                                if name in metadata_cache:
                                    try:
                                        ftp.delete(name + '.json')
                                    except:
                                        pass
                                logger.info(f"FTP DEBUG: Deleted duplicate {name} from FTP server")
                            except error_perm:
                                logger.info(f"FTP DEBUG: Could not delete {name} - permission denied")
                        continue
                    raise

                # Save file to storage
                fs.save(file_id, name, data)

                # Insert location data if available
                if 'location' in metadata:
                    _insert_file_location(file_id, metadata['location'])

                # Insert tags if available
                if 'tags' in metadata:
                    _insert_file_tags(file_id, metadata['tags'])

                # Create workflow run for receipts delivered via FTP
                _dispatch_receipt_workflow(file_id, content_hash, "ftp")

                downloaded.append((file_id, name))
                logger.info(f"FTP DEBUG: Successfully saved {name} as {file_id}")

                if delete_after:
                    try:
                        ftp.delete(name)
                        # Also delete metadata file if it exists
                        if name in metadata_cache:
                            try:
                                ftp.delete(name + '.json')
                            except:
                                pass
                        logger.info(f"FTP DEBUG: Deleted {name} from FTP server")
                    except error_perm:
                        logger.info(f"FTP DEBUG: Could not delete {name} - permission denied")
            except Exception as e:
                logger.error(f"FTP DEBUG: Error processing {name}: {e}")
                errors.append(f"{name}: {e}")
                # Log error if we have a file_id
                if 'file_id' in locals():
                    _history(
                        file_id=file_id,
                        job="ftp_fetch",
                        status="error",
                        ai_stage_name="FTP-FileFetched",
                        log_text=f"Failed to process file from FTP: {name}",
                        error_message=f"{type(e).__name__}: {str(e)}",
                        provider="ftp",
                    )
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
