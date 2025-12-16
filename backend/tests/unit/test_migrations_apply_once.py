from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys

import pytest

_here = Path(__file__).resolve()
_backend_root = _here.parents[2]
_src = _backend_root / "src"
sys.path.insert(0, str(_src))

from services.db import migrations  # noqa: E402


class _FakeCursor:
    def __init__(self, *, ledger: dict[str, str]):
        self._ledger = ledger
        self._fetchone: tuple[int] | None = None
        self._fetchall: list[tuple[str, str]] | None = None
        self.executed: list[tuple[str, tuple | None]] = []

    def execute(self, sql: str, params=None):
        compact = " ".join((sql or "").split())
        self.executed.append((compact, tuple(params) if params is not None else None))

        lower = compact.lower()
        if lower.startswith("select count(*) from schema_migrations"):
            # Supports both:
            # - SELECT COUNT(*) FROM schema_migrations
            # - SELECT COUNT(*) FROM schema_migrations WHERE filename = %s
            if "where filename" in lower and params:
                filename = str(params[0])
                self._fetchone = (1 if filename in self._ledger else 0,)
            else:
                self._fetchone = (len(self._ledger),)
            self._fetchall = None
            return
        if lower.startswith("select filename, checksum from schema_migrations"):
            self._fetchall = [(k, v) for k, v in self._ledger.items()]
            self._fetchone = None
            return
        if lower.startswith("insert into schema_migrations"):
            filename = params[0]
            checksum = params[1] if len(params) > 1 else None
            self._ledger[str(filename)] = str(checksum) if checksum is not None else ""
            self._fetchone = None
            self._fetchall = None
            return

        self._fetchone = None
        self._fetchall = None

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return self._fetchall or []

    def close(self):  # pragma: no cover
        pass


def _fake_db_cursor(ledger: dict[str, str]):
    @contextmanager
    def _ctx(**_kwargs):
        yield _FakeCursor(ledger=ledger)

    return _ctx


def test_apply_migrations_idempotent_applies_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "0001_first.sql").write_text("CREATE TABLE t1 (id INT);", encoding="utf-8")
    (tmp_path / "0002_second.sql").write_text("CREATE TABLE t2 (id INT);", encoding="utf-8")

    ledger: dict[str, str] = {}
    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)
    monkeypatch.setattr(migrations, "db_cursor", _fake_db_cursor(ledger))
    monkeypatch.setattr(migrations, "_db_is_provisioned", lambda _cur: (False, ["missing"]))
    monkeypatch.setattr(migrations, "_table_exists", lambda _cur, _name: False)
    monkeypatch.delenv("DB_MIGRATIONS_BASELINE", raising=False)
    monkeypatch.delenv("DB_MIGRATIONS_ALLOW_DESTRUCTIVE", raising=False)

    first = migrations.apply_migrations(seed_demo=False)
    assert first["mode"] == "apply"
    assert first["applied"] == ["0001_first.sql", "0002_second.sql"]
    assert set(ledger.keys()) == {"0001_first.sql", "0002_second.sql", "__baseline__"}

    second = migrations.apply_migrations(seed_demo=False)
    assert second["mode"] == "apply"
    assert second["applied"] == []


def test_apply_migrations_baseline_marks_without_executing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "0001_first.sql").write_text("CREATE TABLE t1 (id INT);", encoding="utf-8")
    (tmp_path / "0002_second.sql").write_text("CREATE TABLE t2 (id INT);", encoding="utf-8")

    ledger: dict[str, str] = {}
    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)
    monkeypatch.setattr(migrations, "db_cursor", _fake_db_cursor(ledger))
    monkeypatch.setattr(migrations, "_db_is_provisioned", lambda _cur: (True, []))
    monkeypatch.setattr(migrations, "_table_exists", lambda _cur, _name: True)
    monkeypatch.setenv("DB_MIGRATIONS_BASELINE", "1")
    monkeypatch.delenv("DB_MIGRATIONS_ALLOW_DESTRUCTIVE", raising=False)

    result = migrations.apply_migrations(seed_demo=False)
    assert result["mode"] == "baseline"
    assert result["applied"] == []
    assert result["baseline_marked"] == ["0001_first.sql", "0002_second.sql"]
    assert set(ledger.keys()) == {"0001_first.sql", "0002_second.sql", "__baseline__"}


def test_prompt_safe_mode_skips_prompt_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "0001_prompts.sql").write_text(
        """
        DELETE FROM ai_system_prompts WHERE prompt_key = 'data_extraction';
        UPDATE ai_system_prompts SET prompt_content = 'x' WHERE prompt_key = 'data_extraction';
        INSERT INTO ai_system_prompts (prompt_key, title, description, prompt_content) VALUES ('data_extraction', 't', 'd', 'p');
        """,
        encoding="utf-8",
    )

    ledger: dict[str, str] = {}
    cursor = _FakeCursor(ledger=ledger)

    @contextmanager
    def _ctx(**_kwargs):
        yield cursor

    monkeypatch.setattr(migrations, "MIGRATIONS_DIR", tmp_path)
    monkeypatch.setattr(migrations, "db_cursor", _ctx)
    monkeypatch.setattr(migrations, "_db_is_provisioned", lambda _cur: (False, ["missing"]))
    monkeypatch.setattr(migrations, "_table_exists", lambda _cur, name: name == "ai_system_prompts")
    monkeypatch.setattr(migrations, "_has_rows", lambda _cur, name: name == "ai_system_prompts")
    monkeypatch.delenv("DB_MIGRATIONS_BASELINE", raising=False)

    result = migrations.apply_migrations(seed_demo=False)
    assert result["applied"] == ["0001_prompts.sql"]

    executed_sql = "\n".join(sql for sql, _params in cursor.executed)
    assert "DELETE FROM ai_system_prompts" not in executed_sql
    assert "UPDATE ai_system_prompts" not in executed_sql
    assert "INSERT IGNORE INTO ai_system_prompts" in executed_sql
