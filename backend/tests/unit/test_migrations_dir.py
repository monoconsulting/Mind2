from __future__ import annotations

from pathlib import Path
import re
import sys

import pytest

_here = Path(__file__).resolve()
_backend_root = _here.parents[2]
_src = _backend_root / "src"
sys.path.insert(0, str(_src))

from services.db import migrations  # noqa: E402


def test_migrations_dir_points_to_database_folder():
    expected = _backend_root.parent / "database" / "migrations"
    assert migrations.MIGRATIONS_DIR.resolve() == expected.resolve()
    assert "database" in migrations.MIGRATIONS_DIR.parts
    assert "migrations" in migrations.MIGRATIONS_DIR.parts


def test_actual_migrations_have_unique_prefixes():
    """Scan actual database/migrations/*.sql files and assert unique prefixes.

    Skips any file whose first non-empty line starts with '-- Deprecated migration'.
    Fails if any 4-digit prefix is used by more than one non-deprecated file.
    """
    migrations_dir = migrations.MIGRATIONS_DIR
    assert migrations_dir.exists(), f"Migrations directory not found: {migrations_dir}"

    prefix_to_files: dict[str, list[str]] = {}

    for sql_file in sorted(migrations_dir.glob("*.sql")):
        # Check if file is deprecated
        is_deprecated = False
        try:
            with sql_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped:
                        if stripped.startswith("-- Deprecated migration"):
                            is_deprecated = True
                        break
        except OSError:
            pass

        if is_deprecated:
            continue

        # Extract 4-digit prefix
        match = re.match(r"^(\d{4})_.+\.sql$", sql_file.name)
        if not match:
            continue  # Skip files without proper naming (will be caught by other tests)

        prefix = match.group(1)
        if prefix not in prefix_to_files:
            prefix_to_files[prefix] = []
        prefix_to_files[prefix].append(sql_file.name)

    # Check for duplicates
    duplicates = {prefix: files for prefix, files in prefix_to_files.items() if len(files) > 1}

    assert not duplicates, (
        f"Duplicate migration prefixes found among non-deprecated files:\n"
        + "\n".join(f"  {prefix}: {files}" for prefix, files in duplicates.items())
    )
