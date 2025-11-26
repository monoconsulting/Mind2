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
