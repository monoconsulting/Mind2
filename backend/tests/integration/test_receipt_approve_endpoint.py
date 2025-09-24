import sys
from pathlib import Path
from contextlib import contextmanager


def import_app(monkeypatch):
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from importlib import import_module
    return import_module("api.app").app  # type: ignore


class FakeDB:
    def __init__(self):
        self.rowcount = 0

    @contextmanager
    def cursor(self):
        yield self

    def execute(self, sql, params=None):
        s = " ".join(str(sql).split()).lower()
        if s.startswith("update unified_files set ai_status='completed'"):
            self.rowcount = 1


def test_approve_endpoint(monkeypatch):
    app = import_app(monkeypatch)
    client = app.test_client()

    from importlib import import_module
    receipts_mod = import_module("api.receipts")
    fake = FakeDB()
    receipts_mod.db_cursor = lambda: fake.cursor()  # type: ignore

    r = client.post("/receipts/R123/approve")
    assert r.status_code == 200
    assert r.get_json().get("approved") is True

