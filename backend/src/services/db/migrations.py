from __future__ import annotations

import hashlib
import logging
import os
import re

from pathlib import Path
from typing import Any, Iterable, Iterator

from .connection import db_cursor

# Resolve migrations directory in both dev (repo) and container (/app) contexts
def _resolve_migrations_dir() -> Path:
    """Return the canonical migrations directory (`database/migrations`)."""
    here = Path(__file__).resolve()
    # Try repo layout: backend/src/services/db/ -> repo/database/migrations
    try:
        repo_root = here.parents[4]
        candidate = repo_root / "database" / "migrations"
        if candidate.exists():
            return candidate
    except Exception:
        pass
    # Try container layout: /app/database/migrations
    container_candidate = Path("/app/database/migrations")
    if container_candidate.exists():
        return container_candidate
    # Fallback to sibling database/migrations relative to source tree
    # Note: backend/migrations is deprecated and not used by the migration runner.
    return here.parents[2] / "database" / "migrations"


# database/migrations is the single source of truth for schema migrations.
# backend/migrations is deprecated and intentionally ignored by the migration runner.
MIGRATIONS_DIR = _resolve_migrations_dir()


def _validate_and_list_sql_files() -> list[Path]:
    """Return validated .sql migrations sorted by name.

    Rules:
    - only .sql files are considered
    - file name must start with four digits + underscore (NNNN_description.sql)
    - prefixes must be unique
    """
    sql_files: list[Path] = []
    prefixes: set[str] = set()
    for path in MIGRATIONS_DIR.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() != ".sql":
            # Non-SQL files (README/SUMMARY/etc.) are ignored safely.
            continue
        # Skip deprecated stubs kept for history only
        try:
            with path.open("r", encoding="utf-8") as fh:
                first_nonempty = ""
                for line in fh:
                    stripped = line.strip()
                    if stripped:
                        first_nonempty = stripped
                        break
                if first_nonempty.startswith("-- Deprecated migration"):
                    continue
        except OSError:
            # If unreadable, fall through to naming validation which will raise
            pass
        name = path.name
        match = re.match(r"^(\d{4})_.+\.sql$", name)
        if not match:
            raise ValueError(f"Invalid migration filename: {name}")
        prefix = match.group(1)
        if prefix in prefixes:
            raise ValueError(f"Duplicate migration prefix detected: {prefix}")
        prefixes.add(prefix)
        sql_files.append(path)
    return sorted(sql_files)


def list_migration_files() -> Iterable[Path]:
    return _validate_and_list_sql_files()


def _split_sql(sql: str) -> list[str]:
    # Remove BOM
    if sql and sql[0] == "\ufeff":
        sql = sql[1:]
    # Strip line comments starting with -- and block comments /* */
    lines = []
    in_block = False
    for raw in sql.splitlines():
        line = raw
        if not in_block:
            if "/*" in line:
                in_block = True
                line = line.split("/*", 1)[0]
        if in_block:
            if "*/" in raw:
                in_block = False
                tail = raw.split("*/", 1)[1]
                # Keep anything after */ on the same line
                if tail.strip():
                    lines.append(tail)
            continue
        # Remove -- comments
        if "--" in line:
            line = line.split("--", 1)[0]
        if line.strip():
            lines.append(line)
    cleaned = "\n".join(lines)
    parts = [s.strip() for s in cleaned.split(";")]
    return [p for p in parts if p]


import logging

logger = logging.getLogger(__name__)

_BASELINE_MARKER_FILENAME = "__baseline__"

_LEDGER_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  filename VARCHAR(255) NOT NULL,
  checksum CHAR(64) NULL,
  applied_at DATETIME NOT NULL,
  PRIMARY KEY (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_sv_0900_ai_ci
"""


def _compute_checksum(sql_bytes: bytes) -> str:
    return hashlib.sha256(sql_bytes).hexdigest()


def _truthy_env(name: str) -> bool:
    return str(os.getenv(name, "") or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _table_exists(cur: Any, table_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        """,
        (table_name,),
    )
    row = cur.fetchone() or (0,)
    return int(row[0] or 0) > 0


def _column_exists(cur: Any, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    row = cur.fetchone() or (0,)
    return int(row[0] or 0) > 0


def _column_type(cur: Any, table_name: str, column_name: str) -> str | None:
    cur.execute(
        """
        SELECT DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table_name, column_name),
    )
    row = cur.fetchone()
    if not row:
        return None
    return str(row[0] or "").lower() if row[0] is not None else None


def _ensure_schema_migrations(cur: Any) -> None:
    cur.execute(_LEDGER_CREATE_SQL)


def _get_applied(cur: Any) -> dict[str, str | None]:
    _ensure_schema_migrations(cur)
    cur.execute("SELECT filename, checksum FROM schema_migrations")
    rows = cur.fetchall() or []
    applied: dict[str, str | None] = {}
    for filename, checksum in rows:
        if filename:
            applied[str(filename)] = str(checksum) if checksum is not None else None
    return applied


def _schema_migrations_is_empty(cur: Any) -> bool:
    _ensure_schema_migrations(cur)
    cur.execute("SELECT COUNT(*) FROM schema_migrations")
    row = cur.fetchone() or (0,)
    return int(row[0] or 0) == 0


def _schema_migrations_has_baseline_marker(cur: Any) -> bool:
    _ensure_schema_migrations(cur)
    cur.execute("SELECT COUNT(*) FROM schema_migrations WHERE filename = %s", (_BASELINE_MARKER_FILENAME,))
    row = cur.fetchone() or (0,)
    return int(row[0] or 0) > 0


def _ensure_baseline_marker(cur: Any) -> None:
    _ensure_schema_migrations(cur)
    cur.execute(
        """
        INSERT INTO schema_migrations (filename, checksum, applied_at)
        VALUES (%s, NULL, NOW())
        ON DUPLICATE KEY UPDATE filename=filename
        """,
        (_BASELINE_MARKER_FILENAME,),
    )


def _db_is_provisioned(cur: Any) -> tuple[bool, list[str]]:
    """Heuristic sanity-check used to decide if baseline is safe.

    Baseline is only safe when the DB already contains the schema changes represented
    by the migrations directory (i.e., an existing/provisioned environment).
    """
    missing: list[str] = []

    required_tables = [
        "unified_files",
        "invoice_documents",
        "ai_system_prompts",
        # Newer “latest” signature tables
        "ai_llm",
        "workflow_runs",
        "workflow_stage_runs",
    ]
    for table in required_tables:
        if not _table_exists(cur, table):
            missing.append(f"table:{table}")

    # Recent-signature columns
    if not _column_exists(cur, "invoice_documents", "updated_at"):
        missing.append("column:invoice_documents.updated_at")

    prompt_type = _column_type(cur, "ai_system_prompts", "prompt_content")
    if prompt_type != "mediumtext":
        missing.append("column:ai_system_prompts.prompt_content (expected mediumtext)")

    return (len(missing) == 0, missing)


def _baseline_mark(cur: Any, files: list[Path]) -> list[str]:
    applied_files: list[str] = []
    for sql_file in files:
        try:
            sql_bytes = sql_file.read_bytes()
        except Exception:
            # If unreadable, store NULL checksum and continue.
            sql_bytes = b""
        checksum = _compute_checksum(sql_bytes) if sql_bytes else None
        cur.execute(
            """
            INSERT INTO schema_migrations (filename, checksum, applied_at)
            VALUES (%s, %s, NOW())
            ON DUPLICATE KEY UPDATE filename=filename
            """,
            (sql_file.name, checksum),
        )
        applied_files.append(sql_file.name)
    return applied_files


def _iter_sql_statements(sql: str) -> Iterator[str]:
    """Split SQL script into statements, respecting quotes and comments.

    This is required because many migrations embed large prompt strings where semicolons
    may appear inside quoted text.
    """
    if sql and sql[0] == "\ufeff":
        sql = sql[1:]

    buf: list[str] = []
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    escape = False

    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                buf.append(ch)
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if not in_single and not in_double and not in_backtick:
            if ch == "-" and nxt == "-":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue

        if ch == "\\" and (in_single or in_double):
            buf.append(ch)
            escape = not escape
            i += 1
            continue

        if ch == "'" and not in_double and not in_backtick and not escape:
            in_single = not in_single
        elif ch == '"' and not in_single and not in_backtick and not escape:
            in_double = not in_double
        elif ch == "`" and not in_single and not in_double:
            in_backtick = not in_backtick

        escape = False

        if ch == ";" and not in_single and not in_double and not in_backtick:
            statement = "".join(buf).strip()
            buf.clear()
            if statement:
                yield statement
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        yield tail


def _has_rows(cur: Any, table_name: str) -> bool:
    if not _table_exists(cur, table_name):
        return False
    cur.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    row = cur.fetchone() or (0,)
    return int(row[0] or 0) > 0


def _transform_prompt_statement(statement: str) -> str | None:
    """Return a safe statement for ai_system_prompts, or None to skip."""
    stripped = statement.lstrip()
    lower = stripped.lower()
    if "ai_system_prompts" not in lower:
        return statement

    mojibake_sig = re.compile(r"(?:\u00c3|\u00c2|\u00e2\u20ac|\u251c|\u0393\u00c7)")

    def _is_repair_update(sql: str) -> bool:
        sql_lower = sql.lower()
        if " set " not in sql_lower or " where " not in sql_lower:
            return False
        where_idx = sql_lower.find(" where ")
        head = sql[:where_idx]
        tail = sql[where_idx:]

        # Never allow updates that themselves contain mojibake in the SET clause.
        if mojibake_sig.search(head):
            return False

        # Require prompt_key scoping.
        if not re.search(r"(?is)\bprompt_key\s*=\s*'[^']+'\b", tail):
            return False

        # Allow only repair-style predicates that are unlikely to overwrite user-edited prompts:
        # - match known bad values (mojibake signatures) in WHERE, or
        # - match exact bytes via HEX(title|description|prompt_content)=...
        if not (mojibake_sig.search(tail) or re.search(r"(?is)\bhex\s*\(\s*`?(title|description|prompt_content)`?\s*\)", tail)):
            return False

        # Restrict the columns being updated to prompt metadata/content only.
        set_part = head.split(" set ", 1)[1]
        updated_cols = re.findall(r"(?is)(`?)([a-z_]+)\\1\\s*=", set_part)
        allowed = {"title", "description", "prompt_content", "updated_at"}
        return all(col in allowed for _tick, col in updated_cols)

    if lower.startswith("delete"):
        return None
    if lower.startswith("update"):
        # Never overwrite prompt rows via migrations; prompts are user data.
        # Exception: allow narrowly-scoped mojibake repair updates that only run
        # when the existing row matches known-bad encodings (see WORKFLOW_REPAIR_PART_2).
        return stripped if _is_repair_update(stripped) else None
    if lower.startswith("insert"):
        # Allow seeding only-if-missing.
        return re.sub(r"(?is)^\s*insert\s+into\s+`?ai_system_prompts`?\b", "INSERT IGNORE INTO ai_system_prompts", stripped)
    return statement


def apply_migrations(seed_demo: bool = True) -> dict[str, Any]:
    """Apply database/migrations/*.sql safely with ledger + baseline support."""
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    files = list(list_migration_files())

    baseline_requested = _truthy_env("DB_MIGRATIONS_BASELINE")
    allow_destructive = _truthy_env("DB_MIGRATIONS_ALLOW_DESTRUCTIVE")
    applied_now: list[str] = []
    skipped_changed: list[str] = []
    skipped_destructive: list[str] = []
    baseline_marked: list[str] = []

    with db_cursor() as cur:
        _ensure_schema_migrations(cur)
        marker_present = _schema_migrations_has_baseline_marker(cur)
        applied = _get_applied(cur)

        schema_empty = _schema_migrations_is_empty(cur)
        provisioned, missing_signatures = _db_is_provisioned(cur)
        schema_uninitialized = schema_empty or not marker_present
        auto_baseline = schema_uninitialized and provisioned

        if schema_uninitialized and (baseline_requested or auto_baseline):
            if not provisioned:
                raise RuntimeError(
                    "Baseline requested but DB does not appear fully provisioned; "
                    f"missing signatures: {', '.join(missing_signatures) or 'unknown'}"
                )
            logger.warning(
                "schema_migrations not initialized; baselining %d migrations (baseline_requested=%s, auto_baseline=%s)",
                len(files),
                baseline_requested,
                auto_baseline,
            )
            baseline_marked = _baseline_mark(cur, files)
            _ensure_baseline_marker(cur)
            return {
                "ok": True,
                "mode": "baseline",
                "baseline_marked": baseline_marked,
                "applied": [],
                "skipped_changed": [],
            }

        if schema_uninitialized and not provisioned and _table_exists(cur, "unified_files"):
            # Existing DB without a migration ledger: we must not replay old migrations.
            # Operator must run missing catch-up migrations manually, then baseline/auto-baseline.
            hints: list[str] = []
            if "column:invoice_documents.updated_at" in missing_signatures:
                hints.append("Run migration file: 0040_add_updated_at_to_invoice_documents.sql")
            raise RuntimeError(
                "schema_migrations is not initialized and DB appears partially migrated; refusing to replay migrations. "
                f"Missing signatures: {', '.join(missing_signatures) or 'unknown'}. "
                + ("Hints: " + "; ".join(hints) + ". " if hints else "")
                + "After catch-up, run baseline (DB_MIGRATIONS_BASELINE=1) or re-run apply-migrations to allow auto-baseline."
            )

        for sql_file in files:
            sql_bytes = sql_file.read_bytes()
            checksum = _compute_checksum(sql_bytes)
            already = applied.get(sql_file.name)
            if already is not None:
                if already and already != checksum:
                    logger.warning(
                        "Migration file changed after being applied: %s (stored=%s, current=%s). "
                        "Do NOT modify migrations in-place; create a new migration instead.",
                        sql_file.name,
                        already,
                        checksum,
                    )
                    skipped_changed.append(sql_file.name)
                continue

            sql_text = sql_bytes.decode("utf-8-sig")
            if not sql_text.strip():
                cur.execute(
                    """
                    INSERT INTO schema_migrations (filename, checksum, applied_at)
                    VALUES (%s, %s, NOW())
                    """,
                    (sql_file.name, checksum),
                )
                applied_now.append(sql_file.name)
                continue

            if not allow_destructive and sql_file.name in {
                "0035_cleanup_fc_receipt_items.sql",
                "0036_reset_fc_processing.sql",
            }:
                logger.warning(
                    "Skipping destructive one-off migration %s (set DB_MIGRATIONS_ALLOW_DESTRUCTIVE=1 to run manually).",
                    sql_file.name,
                )
                skipped_destructive.append(sql_file.name)
                cur.execute(
                    """
                    INSERT INTO schema_migrations (filename, checksum, applied_at)
                    VALUES (%s, %s, NOW())
                    """,
                    (sql_file.name, checksum),
                )
                applied_now.append(sql_file.name)
                continue

            prompt_safe_mode = (
                ("ai_system_prompts" in sql_text.lower())
                and _table_exists(cur, "ai_system_prompts")
                and _has_rows(cur, "ai_system_prompts")
            )

            logger.info("Applying migration: %s (prompt_safe=%s)", sql_file.name, prompt_safe_mode)
            try:
                for statement in _iter_sql_statements(sql_text):
                    safe_stmt = _transform_prompt_statement(statement) if prompt_safe_mode else statement
                    if safe_stmt is None:
                        continue
                    cur.execute(safe_stmt)
                    try:
                        cur.fetchall()
                    except Exception:
                        pass
            except Exception as exc:  # pragma: no cover
                msg = str(exc)
                logger.error("Error applying migration %s: %s", sql_file.name, msg)
                raise

            cur.execute(
                """
                INSERT INTO schema_migrations (filename, checksum, applied_at)
                VALUES (%s, %s, NOW())
                """,
                (sql_file.name, checksum),
            )
            applied_now.append(sql_file.name)

        if not marker_present:
            _ensure_baseline_marker(cur)

    # Optional seed of a few demo rows for instant UI sanity
    # NOTE: Seed data disabled - mock data is forbidden per CLAUDE.md
    # If re-enabled in future, must:
    # 1. Create companies first in companies table
    # 2. Link via company_id, not merchant_name column (which doesn't exist)
    if False and seed_demo:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT COUNT(1) FROM unified_files")
                (cnt,) = cur.fetchone() or (0,)
                if int(cnt) == 0:
                    # First create companies
                    cur.execute(
                        """
                        INSERT INTO companies (id, name, orgnr)
                        VALUES
                          ('demo-company-001', 'Demo Cafe', '556677-8899'),
                          ('demo-company-002', 'Grocer AB', '112233-4455'),
                          ('demo-company-003', 'Tools & Co', '998877-6655')
                        ON DUPLICATE KEY UPDATE id=id
                        """
                    )
                    # Then create receipts linked to companies
                    cur.execute(
                        """
                        INSERT INTO unified_files
                          (id, file_type, created_at, company_id, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence)
                        VALUES
                          ('demo-0001','receipt', NOW(), 'demo-company-001', NOW(), 89.00, 71.20, 'new', 0.42),
                          ('demo-0002','receipt', NOW(), 'demo-company-002', NOW(), 245.50, 196.40, 'processed', 0.93),
                          ('demo-0003','receipt', NOW(), 'demo-company-003', NOW(), 1299.00, 1039.20, 'error', 0.12)
                        """
                    )
        except Exception:
            # best-effort; ignore seeding errors
            pass

    return {
        "ok": True,
        "mode": "apply",
        "baseline_marked": baseline_marked,
        "applied": applied_now,
        "skipped_changed": skipped_changed,
        "skipped_destructive": skipped_destructive,
    }
