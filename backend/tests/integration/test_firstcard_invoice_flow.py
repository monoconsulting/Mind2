import sys
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager


def import_app(monkeypatch):
    # Disable auto-migrate during tests
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    import sys
    import types

    if "flask_limiter" not in sys.modules:
        limiter_ns = types.SimpleNamespace()

        class DummyLimiter:
            def __init__(self, *args, **kwargs):
                pass

            def init_app(self, _app):  # pragma: no cover - simple stub
                return None

            def limit(self, *args, **kwargs):
                def _decorator(func):
                    return func

                return _decorator

        limiter_ns.Limiter = DummyLimiter
        sys.modules["flask_limiter"] = limiter_ns
        sys.modules.setdefault("flask_limiter.util", types.SimpleNamespace(get_remote_address=lambda *_args, **_kwargs: "0.0.0.0"))
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from importlib import import_module

    return import_module("api.app").app  # type: ignore


class FakeDB:
    def __init__(self):
        self.documents = {}  # id -> {status, period_start, period_end}
        self.lines = []  # list of dicts
        self.history = []
        self._results = None
        self._lastrowid = 0
        self._rowcount = 0

    @contextmanager
    def cursor(self):
        yield self

    # Expose as context manager compatible with code under test
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    # API used by code
    def execute(self, sql, params=None):
        s = " ".join(str(sql).split()).lower()
        p = params or ()
        self._rowcount = 0
        if s.startswith("insert into invoice_documents"):
            doc_id, inv_type, ps, pe = p
            self.documents[doc_id] = {
                "invoice_type": inv_type,
                "period_start": ps,
                "period_end": pe,
                "status": "imported",
                "uploaded_at": "2025-09-20",
                "processing_status": "uploaded",
            }
            self._lastrowid += 1
        elif s.startswith("insert into invoice_lines"):
            invoice_id, tx_date, amount, merchant_name, description, match_status = p
            self._lastrowid += 1
            self.lines.append(
                {
                    "id": self._lastrowid,
                    "invoice_id": invoice_id,
                    "transaction_date": tx_date,
                    "amount": float(amount) if amount is not None else None,
                    "merchant_name": merchant_name,
                    "description": description,
                    "matched_file_id": None,
                    "match_status": match_status,
                }
            )
            self._rowcount = 1
        elif s.startswith("select id, transaction_date, amount from invoice_lines"):
            invoice_id = p[0]
            rows = [
                (ln["id"], ln["transaction_date"], ln["amount"])
                for ln in self.lines
                if ln["invoice_id"] == invoice_id
                and (ln["match_status"] in (None, "pending", "unmatched"))
            ]
            self._results = rows
        elif s.startswith("select count(*) from invoice_lines"):
            invoice_id = p[0]
            count = sum(1 for ln in self.lines if ln["invoice_id"] == invoice_id)
            self._results = [(count,)]
        elif s.startswith("select id from unified_files"):
            # Simulate a matching receipt id for our test
            self._results = [("receipt-1",)]
        elif s.startswith("update invoice_lines set matched_file_id"):
            file_id, score, new_status, line_id, *allowed = p
            for ln in self.lines:
                if ln["id"] == line_id:
                    current = ln["match_status"]
                    allowed_states = {None if a is None else a for a in allowed}
                    if current in allowed_states or current is None:
                        ln["matched_file_id"] = file_id
                        ln["match_status"] = new_status
                        self._rowcount = 1
                    break
        elif s.startswith("insert into invoice_line_history"):
            line_id, new_file_id = p
            self.history.append({"line": line_id, "new": new_file_id})
            self._lastrowid += 1
            self._rowcount = 1
        elif s.startswith("update invoice_documents set status='matched'"):
            doc_id = p[0]
            if doc_id in self.documents:
                self.documents[doc_id]["status"] = "matched"
                self._rowcount = 1
        elif s.startswith("update invoice_documents set status='completed'"):
            doc_id = p[0]
            if doc_id in self.documents:
                self.documents[doc_id]["status"] = "completed"
                self._rowcount = 1
        elif s.startswith("update invoice_documents set status=%s"):
            new_status, doc_id, *allowed = p
            doc = self.documents.get(doc_id)
            if doc and doc["status"] in allowed:
                doc["status"] = new_status
                self._rowcount = 1
        elif s.startswith("update invoice_documents set processing_status=%s"):
            new_status, doc_id, *allowed = p
            doc = self.documents.get(doc_id)
            if doc and doc.get("processing_status") in allowed:
                doc["processing_status"] = new_status
                self._rowcount = 1
        elif s.startswith("select processing_status from invoice_documents"):
            doc_id = p[0]
            doc = self.documents.get(doc_id)
            self._results = [(doc.get("processing_status"),)] if doc else []
        elif s.startswith("select status from invoice_documents"):
            doc_id = p[0]
            doc = self.documents.get(doc_id)
            self._results = [(doc.get("status"),)] if doc else []
        elif s.startswith("select match_status from invoice_lines"):
            line_id = int(p[0])
            for ln in self.lines:
                if ln["id"] == line_id:
                    self._results = [(ln["match_status"],)]
                    break
        elif s.startswith("select count(*), sum(case when match_status"):
            invoice_id = p[0]
            total = 0
            matched = 0
            for ln in self.lines:
                if ln["invoice_id"] != invoice_id:
                    continue
                total += 1
                if ln["match_status"] in ("auto", "manual", "confirmed"):
                    matched += 1
            self._results = [(total, matched)]
        elif s.startswith("select id, uploaded_at, status from invoice_documents"):
            rows = [
                (doc_id, doc["uploaded_at"], doc["status"])
                for doc_id, doc in self.documents.items()
                if doc.get("invoice_type") == "company_card"
            ]
            self._results = rows
        else:
            # Default: no results
            self._results = []

    def fetchone(self):
        if not self._results:
            return None
        return self._results[0]

    def fetchall(self):
        return self._results or []

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._rowcount


def test_firstcard_import_match_confirm(monkeypatch):
    app = import_app(monkeypatch)
    client = app.test_client()

    # Patch module to use FakeDB cursor
    from importlib import import_module

    mod = import_module("api.reconciliation_firstcard")
    fake = FakeDB()

    def fake_db_cursor():
        return fake.cursor()

    # Overwrite the module-level db_cursor used by the blueprint
    mod.db_cursor = fake_db_cursor  # type: ignore
    status_mod = import_module("services.invoice_status")
    status_mod.db_cursor = fake_db_cursor  # type: ignore

    # 1) Import statement with a single line
    body = {
        "period_start": "2025-09-01",
        "period_end": "2025-09-30",
        "lines": [
            {
                "transaction_date": "2025-09-10",
                "amount": 112.00,
                "merchant_name": "Demo Cafe",
                "description": "Card",
            }
        ],
    }
    r1 = client.post("/reconciliation/firstcard/import", json=body)
    assert r1.status_code == 200
    doc_id = r1.get_json()["id"]
    assert fake.documents[doc_id]["status"] == "imported"
    assert fake.documents[doc_id]["processing_status"] == "ready_for_matching"

    # 2) Match
    r2 = client.post("/reconciliation/firstcard/match", json={"document_id": doc_id})
    assert r2.status_code == 200
    assert r2.get_json()["matched"] == 1
    # Confirm line marked matched
    assert fake.lines[0]["matched_file_id"] == "receipt-1"
    assert fake.documents[doc_id]["status"] == "matched"
    assert fake.documents[doc_id]["processing_status"] == "matching_completed"

    # 3) List statements
    r3 = client.get("/reconciliation/firstcard/statements")
    assert r3.status_code == 200
    items = r3.get_json()["items"]
    assert any(it["id"] == doc_id for it in items)

    # 4) Confirm
    r4 = client.post(f"/reconciliation/firstcard/statements/{doc_id}/confirm")
    assert r4.status_code == 200
    assert fake.documents[doc_id]["status"] == "completed"
    assert fake.documents[doc_id]["processing_status"] == "completed"

