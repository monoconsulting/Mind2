from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .connection import db_cursor
import re

# Resolve migrations directory in both dev (repo) and container (/app) contexts
def _resolve_migrations_dir() -> Path:
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
    return here.parents[2] / "database" / "migrations"


MIGRATIONS_DIR = _resolve_migrations_dir()


def list_migration_files() -> Iterable[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


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


def apply_migrations(seed_demo: bool = True) -> None:
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    for sql_file in list_migration_files():
        with open(sql_file, "r", encoding="utf-8") as f:
            sql = f.read()
        if not sql.strip():
            continue
        with db_cursor() as cur:
            for statement in _split_sql(sql):
                try:
                    cur.execute(statement)
                except Exception as e:  # pragma: no cover
                    msg = str(e)
                    # Ignore idempotency errors
                    if (
                        "Duplicate column name" in msg
                        or "already exists" in msg
                        or "exists" in msg and "constraint" in msg.lower()
                    ):
                        continue
                    raise

    # Optional seed of a few demo rows for instant UI sanity
    if seed_demo:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT COUNT(1) FROM unified_files")
                (cnt,) = cur.fetchone() or (0,)
                if int(cnt) == 0:
                    cur.execute(
                        """
                        INSERT INTO unified_files
                          (id, file_type, created_at, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence)
                        VALUES
                          ('demo-0001','receipt', NOW(), 'Demo Cafe', '556677-8899', NOW(), 89.00, 71.20, 'new', 0.42),
                          ('demo-0002','receipt', NOW(), 'Grocer AB', '112233-4455', NOW(), 245.50, 196.40, 'processed', 0.93),
                          ('demo-0003','receipt', NOW(), 'Tools & Co', '998877-6655', NOW(), 1299.00, 1039.20, 'error', 0.12)
                        """
                    )
        except Exception:
            # best-effort; ignore seeding errors
            pass
