import sys
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime


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
        self._results = None

    @contextmanager
    def cursor(self):
        yield self

    def execute(self, sql, params=None):
        s = " ".join(str(sql).split()).lower()
        p = params or ()
        if s.startswith("select id, merchant_name, purchase_datetime, gross_amount, net_amount, ai_confidence from unified_files"):
            # For /validation
            self._results = [(p[0], "Cafe", datetime(2025, 9, 10, 12, 0, 0), 112.00, 100.00, 0.95)]
        elif s.startswith("select id, merchant_name, purchase_datetime, gross_amount, net_amount from unified_files"):
            # For /accounting/proposal
            self._results = [(p[0], "Cafe", datetime(2025, 9, 10, 12, 0, 0), 112.00, 100.00)]
        else:
            self._results = []

    def fetchone(self):
        return self._results[0] if self._results else None


def test_receipt_validation_and_proposal(monkeypatch):
    app = import_app(monkeypatch)
    client = app.test_client()

    # Patch receipts module db_cursor
    from importlib import import_module
    receipts_mod = import_module("api.receipts")
    fake = FakeDB()
    receipts_mod.db_cursor = lambda: fake.cursor()  # type: ignore

    rid = "RVAL"

    r1 = client.get(f"/receipts/{rid}/validation")
    assert r1.status_code == 200
    data = r1.get_json()
    assert "status" in data and "messages" in data

    r2 = client.get(f"/receipts/{rid}/accounting/proposal")
    assert r2.status_code == 200
    entries = r2.get_json()
    assert isinstance(entries, list)
    assert len(entries) >= 2

