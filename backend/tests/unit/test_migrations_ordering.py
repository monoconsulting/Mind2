from __future__ import annotations

from pathlib import Path
import sys

import pytest

_here = Path(__file__).resolve()
_backend_root = _here.parents[2]
_src = _backend_root / "src"
sys.path.insert(0, str(_src))

from services.db import migrations  # noqa: E402


def test_list_migration_files_valid_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "0001_alpha.sql").write_text("select 1;")
    (tmp_path / "0002_beta.sql").write_text("select 1;")
    (tmp_path / "notes.md").write_text("# ignored")

    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)

    files = list(migrations.list_migration_files())
    assert [p.name for p in files] == ["0001_alpha.sql", "0002_beta.sql"]


def test_list_migration_files_duplicate_prefix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "0001_alpha.sql").write_text("select 1;")
    (tmp_path / "0001_beta.sql").write_text("select 1;")

    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)

    with pytest.raises(ValueError) as exc:
        list(migrations.list_migration_files())
    assert "Duplicate migration prefix" in str(exc.value)


def test_list_migration_files_invalid_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "1_bad.sql").write_text("select 1;")

    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)

    with pytest.raises(ValueError) as exc:
        list(migrations.list_migration_files())
    assert "Invalid migration filename" in str(exc.value)


def test_list_migration_files_skips_deprecated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deprecated migrations (first line starts with '-- Deprecated migration') are skipped.

    This allows duplicate prefixes where one file is deprecated and another is active.
    Example: 0031_old.sql (deprecated) and 0031_active.sql should not conflict.
    """
    # Active migration with prefix 0031
    (tmp_path / "0031_active.sql").write_text("SELECT 1;")

    # Deprecated migration with same prefix - should be skipped
    deprecated_content = """-- Deprecated migration (2025-11-26)
-- This migration has been replaced by 0042_new.sql
-- Kept for historical reference only.

-- ORIGINAL SQL (commented):
-- CREATE TABLE old_table (id INT);
"""
    (tmp_path / "0031_old_deprecated.sql").write_text(deprecated_content)

    # Another active migration
    (tmp_path / "0042_new.sql").write_text("SELECT 2;")

    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)

    files = list(migrations.list_migration_files())
    names = [p.name for p in files]

    # Should include both active migrations but NOT the deprecated one
    assert "0031_active.sql" in names
    assert "0042_new.sql" in names
    assert "0031_old_deprecated.sql" not in names
    assert len(names) == 2


def test_list_migration_files_deprecated_does_not_conflict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A deprecated file with same prefix as active file should not raise duplicate error."""
    # This is the exact scenario from MIND_FULL_UPDATE_2025-11-25_FIXES_2.md:
    # - 0031_add_ocr_raw_to_creditcard_invoices.sql (active)
    # - 0031_create_workflow_tracking.sql (deprecated, replaced by 0042)
    # - 0042_create_workflow_tracking.sql (active canonical)

    (tmp_path / "0031_add_ocr_raw_to_creditcard_invoices.sql").write_text(
        "ALTER TABLE creditcard_invoices_main ADD COLUMN ocr_raw LONGTEXT;"
    )

    (tmp_path / "0031_create_workflow_tracking.sql").write_text(
        "-- Deprecated migration (2025-11-26)\n-- Replaced by 0042_create_workflow_tracking.sql\n"
    )

    (tmp_path / "0042_create_workflow_tracking.sql").write_text(
        "CREATE TABLE IF NOT EXISTS workflow_runs (id BIGINT PRIMARY KEY);"
    )

    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)

    # Should NOT raise ValueError - deprecated file is skipped
    files = list(migrations.list_migration_files())
    names = [p.name for p in files]

    assert "0031_add_ocr_raw_to_creditcard_invoices.sql" in names
    assert "0042_create_workflow_tracking.sql" in names
    assert "0031_create_workflow_tracking.sql" not in names
