from __future__ import annotations

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


def _find_or_create_company(merchant_name: Optional[str], orgnr: Optional[str]) -> Optional[int]:
    """
    Find or create a company in the companies table.
    Returns company_id if found/created, None if not possible.

    Strategy:
    1. If orgnr provided: lookup by orgnr, create if not found
    2. If only name provided: lookup by name, create if not found
    3. If neither provided: return None
    """
    if db_cursor is None:
        return None

    # Need at least one identifier
    if not merchant_name and not orgnr:
        return None

    try:
        with db_cursor() as cur:
            # Try to find existing company
            if orgnr:
                # Lookup by orgnr (most reliable)
                cur.execute(
                    "SELECT id FROM companies WHERE orgnr = %s LIMIT 1",
                    (orgnr,)
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Found existing company by orgnr: {orgnr} -> id={result[0]}")
                    return result[0]

            if merchant_name:
                # Lookup by name (less reliable, but better than nothing)
                cur.execute(
                    "SELECT id FROM companies WHERE name = %s LIMIT 1",
                    (merchant_name,)
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Found existing company by name: {merchant_name} -> id={result[0]}")
                    return result[0]

            # Company not found, create new one
            company_name = merchant_name or f"Unknown ({orgnr})" if orgnr else "Unknown"
            cur.execute(
                """
                INSERT INTO companies (name, orgnr, created_at)
                VALUES (%s, %s, NOW())
                """,
                (company_name, orgnr)
            )

            # Get the newly created company ID
            cur.execute("SELECT LAST_INSERT_ID()")
            result = cur.fetchone()
            if result:
                new_company_id = result[0]
                logger.info(f"Created new company: {company_name} (orgnr={orgnr}) -> id={new_company_id}")
                return new_company_id

            return None

    except Exception as e:
        logger.error(f"Error finding/creating company (name={merchant_name}, orgnr={orgnr}): {e}")
        return None


def _insert_unified_file(
    file_id: str,
    filename: str,
    metadata: Dict[str, Any]
) -> None:
    """Insert file record with complete metadata"""
    if db_cursor is None:
        return

    try:
        file_suffix = _get_file_suffix(filename)
        file_category = _get_file_category(file_suffix)

        # Extract metadata fields (old format)
        merchant_name = metadata.get('merchant_name')
        orgnr = metadata.get('orgnr')
        purchase_datetime = metadata.get('purchase_datetime')
        gross_amount = metadata.get('gross_amount')
        net_amount = metadata.get('net_amount')

        # Extract new JSON format fields
        original_file_id = metadata.get('file_id')
        original_file_name = metadata.get('original_name')
        file_creation_timestamp = metadata.get('timestamp')
        original_file_size = metadata.get('file_size')
        mime_type = metadata.get('file_type')

        # Convert datetime strings to datetime objects if needed
        if purchase_datetime and isinstance(purchase_datetime, str):
            try:
                purchase_datetime = datetime.strptime(purchase_datetime, '%Y-%m-%d %H:%M:%S')
            except:
                purchase_datetime = None

        if file_creation_timestamp and isinstance(file_creation_timestamp, str):
            try:
                # Handle ISO format with timezone: 2025-09-07T19:33:00+02:00
                # Remove timezone info for MySQL compatibility
                timestamp_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', file_creation_timestamp)
                file_creation_timestamp = datetime.fromisoformat(timestamp_clean.replace('T', ' '))
            except:
                file_creation_timestamp = None

        # Find or create company if merchant info provided
        # This replaces direct merchant_name storage which doesn't exist in schema
        company_id = None
        if merchant_name or orgnr:
            company_id = _find_or_create_company(merchant_name, orgnr)
            if company_id:
                logger.info(f"Linked file {file_id} to company_id={company_id}")

        with db_cursor() as cur:
            cur.execute(
                """
                INSERT INTO unified_files (
                    id, file_type, created_at,
                    file_category, file_suffix,
                    company_id, vat, purchase_datetime,
                    gross_amount, net_amount, original_filename,
                    original_file_id, original_file_name, file_creation_timestamp,
                    original_file_size, mime_type
                ) VALUES (
                    %s, %s, NOW(),
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
                """,
                (
                    file_id, "receipt",
                    file_category, file_suffix,
                    company_id, orgnr, purchase_datetime,
                    gross_amount, net_amount, filename,
                    original_file_id, original_file_name, file_creation_timestamp,
                    original_file_size, mime_type
                )
            )
            logger.info(f"Inserted unified_file {file_id} with metadata (company_id={company_id})")
    except Exception as e:
        logger.error(f"Error inserting unified file: {e}")


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

            # Load metadata from JSON file if it exists
            metadata = _load_metadata(p)

            # Save file to storage
            fs.save(file_id, p.name, data)

            # Insert file record with metadata
            _insert_unified_file(file_id, p.name, metadata)

            # Insert location data if available
            if 'location' in metadata:
                _insert_file_location(file_id, metadata['location'])

            # Insert tags if available
            if 'tags' in metadata:
                _insert_file_tags(file_id, metadata['tags'])

            # Set AI status
            set_ai_status(file_id, "new")

            downloaded.append((file_id, p.name))

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
            errors.append(f"{p.name}: {e}")

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

                # Get metadata if available
                metadata = metadata_cache.get(name, {})

                # Save file to storage
                fs.save(file_id, name, bytes(buf))

                # Insert file record with metadata
                _insert_unified_file(file_id, name, metadata)

                # Insert location data if available
                if 'location' in metadata:
                    _insert_file_location(file_id, metadata['location'])

                # Insert tags if available
                if 'tags' in metadata:
                    _insert_file_tags(file_id, metadata['tags'])

                # Set AI status
                set_ai_status(file_id, "new")

                downloaded.append((file_id, name))
                logger.info(f"FTP DEBUG: Successfully saved {name}")

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