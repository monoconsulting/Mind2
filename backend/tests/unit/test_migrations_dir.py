from __future__ import annotations

from pathlib import Path
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
