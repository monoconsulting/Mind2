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

from services.ftp_service import (
    FTPConfig,
    ftp_connection,
    list_files,
    download_file,
    delete_file,
)

from services.storage import FileStorage
from services.tasks import (
    begin_import_stage,
    complete_import_stage,
    dispatch_workflow,
)
from services.workflow_runs import create_workflow_run
from services.ai_logging import log_ai_call

logger = logging.getLogger(__name__)
try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore
try:
    from services.db.files import (
        set_ai_status,
        create_unified_file,
        DuplicateFileError,
    )
except Exception:  # pragma: no cover
    def set_ai_status(file_id: str, status: str) -> bool:  # type: ignore
        _ = (file_id, status)
        return False
    class DuplicateFileError(Exception): pass
    def create_unified_file(*args, **kwargs): pass


_history = log_ai_call


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
    content_hash: str,
    source: str = "ftp"
) -> Optional[str]:
    """Insert file record with metadata from FTP using create_unified_file. Returns workflow_run_id."""
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

    unified_file = create_unified_file(
        file_id=file_id,
        file_type="receipt",
        content_hash=content_hash,
        submitted_by=source,
        original_filename=filename,
        initial_ai_status="ftp_fetched",
        mime_type=mime_type,
        file_suffix=file_suffix,
        original_file_id=original_file_id,
        original_file_name=original_file_name,
        original_file_size=original_file_size,
        extra_metadata={},
        source=source,
        file_category=file_category,
        workflow_type="WF1_RECEIPT"
    )
    logger.info(f"Inserted unified_file {file_id} with metadata and hash {content_hash[:16]}...")

    # Log successful FTP fetch
    file_size = metadata.get('file_size', 'unknown')
    _history(
        file_id=file_id,
        job="ftp_fetch",
        status="success",
        ai_stage_name="FTP-FileFetched",
        log_text=f"File fetched from FTP: filename={filename}, size={file_size} bytes, hash={content_hash[:16]}..., metadata_fields={list(metadata.keys())}. Metadata från FTP registrerad",
        provider="ftp",
    )
    
    workflow_run_id = unified_file.workflow_run_id
    if not workflow_run_id:
        logger.warning(f"No workflow run created for file {file_id}")
        return None

    begin_import_stage(
        workflow_run_id,
        "ingest_wf1",
        message="Skapar WF1 workflow_run",
    )
    
    return workflow_run_id


def _dispatch_and_complete(workflow_run_id: str, file_id: str) -> bool:
    """Helper to dispatch workflow and update stage"""
    if not dispatch_workflow(workflow_run_id):
        logger.error(
            "Dispatch of workflow_run %s failed for file %s",
            workflow_run_id,
            file_id,
        )
        complete_import_stage(
            workflow_run_id,
            "ingest_wf1",
            success=False,
            message="WF1 kunde inte dispatchas",
        )
        return False

    complete_import_stage(
        workflow_run_id,
        "ingest_wf1",
        success=True,
        message="WF1 dispatchad",
    )
    set_ai_status(file_id, "processing")
    logger.info(
        "Dispatched WF1 workflow (run_id=%s) for FTP file %s",
        workflow_run_id,
        file_id,
    )
    return True


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

            workflow_run_id = None
            # Insert file record with metadata and hash (handles duplicates)
            try:
                workflow_run_id = _insert_unified_file(file_id, p.name, metadata, content_hash)
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

            # Dispatch workflow if created
            if workflow_run_id:
                _dispatch_and_complete(workflow_run_id, file_id)

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
    """Fetch files from FTP server with metadata support using ftp_service"""
    try:
        config = FTPConfig.from_env()
    except ValueError as e:
        logger.info(f"FTP DEBUG: {e}, falling back to local inbox mode")
        return fetch_from_local_inbox()

    logger.info(f"FTP DEBUG: Starting fetch_from_ftp, host={config.host}")
    logger.info(f"FTP DEBUG: Config - host={config.host}, port={config.port}, user={config.user}, remote_dir={config.remote_directory}")
    logger.info(f"FTP DEBUG: Config - use_tls={config.use_tls}, passive={config.passive}, allowed_exts={config.allowed_extensions}")

    downloaded: List[Tuple[str, str]] = []
    skipped: List[str] = []
    errors: List[str] = []
    
    fs = _storage()

    try:
        with ftp_connection(config) as ftp:
            logger.info("FTP DEBUG: Getting file list...")
            files = list_files(ftp, config)
            logger.info(f"FTP DEBUG: Found {len(files)} allowed files")

            for remote_file in files:
                name = remote_file.filename
                logger.info(f"FTP DEBUG: Processing file: {name}")

                try:
                    # Try to download metadata file
                    metadata = {}
                    metadata_filename = name + ".json"
                    try:
                        json_data = download_file(ftp, metadata_filename)
                        metadata = json.loads(json_data.decode('utf-8'))
                        logger.info(f"FTP DEBUG: Loaded metadata for {name}")
                    except Exception:
                        # Metadata file might not exist, which is fine
                        pass

                    file_id = str(uuid.uuid4())
                    logger.info(f"FTP DEBUG: Downloading {name} with file_id {file_id}")
                    
                    file_data = download_file(ftp, name)
                    logger.info(f"FTP DEBUG: Downloaded {len(file_data)} bytes for {name}")

                    # Calculate content hash for duplicate detection
                    content_hash = hashlib.sha256(file_data).hexdigest()
                    logger.info(f"FTP DEBUG: Calculated hash {content_hash[:16]}... for {name}")

                    workflow_run_id = None
                    # Insert file record with metadata and hash (handles duplicates)
                    try:
                        workflow_run_id = _insert_unified_file(file_id, name, metadata, content_hash, source="ftp")
                    except ValueError as ve:
                        if "Duplicate file" in str(ve):
                            skipped.append(name)
                            logger.info(f"FTP DEBUG: Skipped duplicate file {name}")
                            continue
                        raise

                    # Save file to storage (CRITICAL FIX: was missing in original code)
                    fs.save(file_id, name, file_data)

                    # Insert location data if available
                    if 'location' in metadata:
                        _insert_file_location(file_id, metadata['location'])

                    # Insert tags if available
                    if 'tags' in metadata:
                        _insert_file_tags(file_id, metadata['tags'])

                    # Dispatch workflow if created
                    if workflow_run_id:
                        _dispatch_and_complete(workflow_run_id, file_id)

                    downloaded.append((file_id, name))
                    logger.info(f"FTP DEBUG: Successfully saved {name} as {file_id}")

                    if config.delete_after:
                        delete_file(ftp, name)
                        delete_file(ftp, metadata_filename)
                        logger.info(f"FTP DEBUG: Deleted {name} from FTP server")

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

    logger.info(f"FTP DEBUG: Fetch complete - downloaded: {len(downloaded)}, skipped: {len(skipped)}, errors: {len(errors)}")
    return FetchResult(downloaded=downloaded, skipped=skipped, errors=errors)
