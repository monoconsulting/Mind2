import io
import json
import sys
import types
import uuid
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from services.invoice_status import (
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    InvoiceDocumentStatus,
)
from models.ai_processing import (
    CreditCardMatchResponse,
    CreditCardInvoiceExtractionResponse,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
)

import pytest
from flask import Flask

# Stubs for optional dependencies used by the Flask app
if 'mysql' not in sys.modules:
    mysql_pkg = types.ModuleType('mysql')
    mysql_connector = types.ModuleType('mysql.connector')

    def _stub_connect(*args, **kwargs):
        raise RuntimeError('mysql connector stub is not available in tests')

    mysql_connector.connect = _stub_connect
    mysql_pkg.connector = mysql_connector
    sys.modules['mysql'] = mysql_pkg
    sys.modules['mysql.connector'] = mysql_connector

if 'flask_limiter' not in sys.modules:
    class _LimiterStub:
        def __init__(self, *args, **kwargs):
            pass

        def limit(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator

        def init_app(self, *_args, **_kwargs):
            return None

    sys.modules['flask_limiter'] = types.SimpleNamespace(
        Limiter=lambda *args, **kwargs: _LimiterStub()
    )
    sys.modules['flask_limiter.util'] = types.SimpleNamespace(
        get_remote_address=lambda *args, **kwargs: '127.0.0.1'
    )



class FakeDB:
    """In-memory simulation of the limited SQL used by the invoice endpoints."""

    def __init__(self) -> None:
        self.unified_files: Dict[str, Dict[str, Any]] = {}
        self.invoice_documents: Dict[str, Dict[str, Any]] = {}
        self.invoice_lines: List[Dict[str, Any]] = []
        self.creditcard_receipt_matches: List[Dict[str, Any]] = []
        self.companies: Dict[int, Dict[str, Any]] = {}
        self.creditcard_invoices_main: Dict[int, Dict[str, Any]] = {}
        self.creditcard_invoice_items: List[Dict[str, Any]] = []
        self._results: List[Any] = []
        self.rowcount: int = 0
        self.lastrowid: int | None = None
        self._next_creditcard_main_id: int = 1

    def cursor(self):
        return self

    # Context manager protocol -------------------------------------------------
    def __enter__(self):
        self._results = []
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    # SQL handlers -------------------------------------------------------------
    def execute(self, sql: Any, params: Any | None = None) -> None:
        sql_norm = " ".join(str(sql).split())
        statement = sql_norm.lower()
        params = params or ()
        self.rowcount = 0
        self.lastrowid = None

        if statement.startswith("insert into unified_files"):
            (
                file_id,
                file_type,
                ocr_raw,
                other_data,
                content_hash,
                submitted_by,
                original_filename,
                ai_status,
                mime_type,
                file_suffix,
                original_file_id,
                original_file_name,
                original_file_size,
            ) = params
            if any(entry["content_hash"] == content_hash for entry in self.unified_files.values()):
                raise RuntimeError("Duplicate entry 'idx_content_hash'")
            self.unified_files[file_id] = {
                "id": file_id,
                "file_type": file_type,
                "ocr_raw": ocr_raw,
                "other_data": other_data,
                "content_hash": content_hash,
                "submitted_by": submitted_by,
                "original_filename": original_filename,
                "ai_status": ai_status,
                "mime_type": mime_type,
                "file_suffix": file_suffix,
                "original_file_id": original_file_id,
                "original_file_name": original_file_name,
                "original_file_size": original_file_size,
                "credit_card_match": 0,
            }
            self.rowcount = 1
        elif statement.startswith("update unified_files set other_data"):
            other_data, file_id = params
            if file_id in self.unified_files:
                self.unified_files[file_id]["other_data"] = other_data
                self.rowcount = 1
        elif "from unified_files" in statement and "content_hash" in statement:
            content_hash = params[0]
            matches = [
                (fid,)
                for fid, entry in self.unified_files.items()
                if entry["content_hash"] == content_hash
            ]
            self._results = matches[:1]
        elif statement.startswith("select id, file_type, ai_status, other_data, ocr_raw from unified_files"):
            target_id, original_id = params
            rows = []
            for entry in self.unified_files.values():
                if entry["id"] == target_id or entry.get("original_file_id") == original_id:
                    rows.append(
                        (
                            entry["id"],
                            entry["file_type"],
                            entry.get("ai_status"),
                            entry.get("other_data"),
                            entry.get("ocr_raw"),
                    )
                )
            self._results = rows
        elif statement.startswith("insert into creditcard_invoices_main"):
            columns_segment = sql_norm[sql_norm.index("(") + 1 : sql_norm.index(")")]
            columns = [col.strip() for col in columns_segment.split(",")]
            row = {column: value for column, value in zip(columns, params)}
            main_id = self._next_creditcard_main_id
            self._next_creditcard_main_id += 1
            row["id"] = main_id
            self.creditcard_invoices_main[main_id] = row
            self.lastrowid = main_id
            self.rowcount = 1
        elif statement.startswith("update creditcard_invoices_main set"):
            set_clause = sql_norm.split(" set ", 1)[1].rsplit(" where ", 1)[0]
            assignments = [segment.strip() for segment in set_clause.split(",")]
            target_id = params[-1]
            try:
                target_id_int = int(target_id)
            except (TypeError, ValueError):
                target_id_int = target_id
            row = self.creditcard_invoices_main.get(target_id_int)
            if row:
                for assignment, value in zip(assignments, params[:-1]):
                    column = assignment.split("=")[0].strip()
                    row[column] = value
                self.rowcount = 1
        elif statement.startswith("delete from creditcard_invoice_items where main_id="):
            (main_id,) = params
            try:
                main_id_int = int(main_id)
            except (TypeError, ValueError):
                main_id_int = main_id
            self.creditcard_invoice_items = [
                item for item in self.creditcard_invoice_items if item.get("main_id") != main_id_int
            ]
            self.rowcount = 1
        elif statement.startswith("insert into creditcard_invoice_items"):
            columns_segment = sql_norm[sql_norm.index("(") + 1 : sql_norm.index(")")]
            columns = [col.strip() for col in columns_segment.split(",")]
            row = {column: value for column, value in zip(columns, params)}
            self.creditcard_invoice_items.append(row)
            self.rowcount = 1
        elif statement.startswith("select id from creditcard_invoices_main where invoice_number"):
            invoice_number = params[0]
            matches = [
                (main_id,)
                for main_id, row in self.creditcard_invoices_main.items()
                if row.get("invoice_number") == invoice_number
            ]
            self._results = matches[:1]
        elif statement.startswith(
            "select id, transaction_date, amount, coalesce(merchant_name, description) as merchant_hint, match_status from invoice_lines"
        ):
            invoice_id = params[0]
            rows = []
            for ln in self.invoice_lines:
                status = ln.get("match_status")
                if ln["invoice_id"] == invoice_id and (status is None or status in {"pending", "unmatched"}):
                    rows.append(
                        (
                            ln["id"],
                            ln.get("transaction_date"),
                            ln.get("amount"),
                            ln.get("merchant_name") or ln.get("description"),
                            ln.get("match_status"),
                        )
                    )
            self._results = rows
        elif statement.startswith("select invoice_id, transaction_date, amount, match_status, matched_file_id from invoice_lines where id=%s"):
            line_id = params[0]
            for ln in self.invoice_lines:
                if ln["id"] == int(line_id):
                    self._results = [
                        (
                            ln["invoice_id"],
                            ln.get("transaction_date"),
                            ln.get("amount"),
                            ln.get("match_status"),
                            ln.get("matched_file_id"),
                        )
                    ]
                    break
            else:
                self._results = []
        elif statement.startswith("select id, transaction_date, amount from invoice_lines"):
            invoice_id = params[0]
            rows = []
            for ln in self.invoice_lines:
                status = ln.get("match_status")
                if ln["invoice_id"] == invoice_id and (status is None or status in {"pending", "unmatched"}):
                    rows.append(
                        (
                            ln["id"],
                            ln.get("transaction_date"),
                            ln.get("amount"),
                        )
                    )
            self._results = rows
        elif statement.startswith("select uf.id, uf.purchase_datetime, uf.gross_amount, c.name from unified_files as uf"):
            target_date = params[0]
            amount = Decimal(str(params[1]))
            results = []
            for entry in self.unified_files.values():
                purchase_dt = entry.get("purchase_datetime")
                gross_amount = entry.get("gross_amount")
                if purchase_dt is None or gross_amount is None:
                    continue
                if isinstance(purchase_dt, datetime):
                    purchase_date = purchase_dt.date().isoformat()
                else:
                    purchase_date = str(purchase_dt).split(" ")[0]
                if str(purchase_date) != str(target_date):
                    continue
                if abs(Decimal(str(gross_amount)) - amount) > Decimal("5"):
                    continue
                if entry.get("credit_card_match"):
                    continue
                if any(match["receipt_id"] == entry["id"] for match in self.creditcard_receipt_matches):
                    continue
                results.append((entry["id"], purchase_dt, gross_amount, entry.get("company_name")))
            self._results = results[:10]
        elif statement.startswith("update unified_files set ai_status=%s, ai_confidence"):
            ai_status, _confidence, file_id = params
            if file_id in self.unified_files:
                self.unified_files[file_id]["ai_status"] = ai_status
                self.rowcount = 1
        elif statement.startswith("update unified_files set ai_status"):
            ai_status, file_id = params
            if file_id in self.unified_files:
                self.unified_files[file_id]["ai_status"] = ai_status
                self.rowcount = 1
        elif statement.startswith("insert into invoice_documents"):
            doc_id, invoice_type, status, processing_status, metadata_json = params
            self.invoice_documents[doc_id] = {
                "invoice_type": invoice_type,
                "status": status,
                "processing_status": processing_status,
                "metadata_json": metadata_json,
                "uploaded_at": datetime.now(),
                "period_start": None,
                "period_end": None,
            }
            self.rowcount = 1
        elif statement.startswith("update invoice_documents set metadata_json="):
            metadata_json, doc_id = params
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["metadata_json"] = metadata_json
                self.rowcount = 1
                self.rowcount = 1
        elif (
            statement.startswith("update invoice_documents set status=")
            and "metadata_json" in statement
        ):
            status, processing_status, metadata_json, doc_id = params
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["status"] = status
                self.invoice_documents[doc_id]["processing_status"] = processing_status
                self.invoice_documents[doc_id]["metadata_json"] = metadata_json
                self.rowcount = 1
        elif statement.startswith("update invoice_documents set status="):
            target_status = params[0]
            doc_id = params[1]
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["status"] = target_status
                self.rowcount = 1
        elif statement.startswith("select status, metadata_json from invoice_documents"):
            doc_id = params[0]
            doc = self.invoice_documents.get(doc_id)
            self._results = [
                (doc["status"], doc["metadata_json"])
            ] if doc else []
        elif statement.startswith("update invoice_documents set processing_status="):
            target_status = params[0]
            doc_id = params[1]
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["processing_status"] = target_status
                self.rowcount = 1
        elif statement.startswith("update invoice_documents set period_start=%s, period_end=%s"):
            period_start, period_end, doc_id = params
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["period_start"] = period_start
                self.invoice_documents[doc_id]["period_end"] = period_end
                self.rowcount = 1
        elif statement.startswith("update invoice_documents set period_start="):
            period_start, doc_id = params
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["period_start"] = period_start
                self.rowcount = 1
        elif statement.startswith("update invoice_documents set period_end="):
            period_end, doc_id = params
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["period_end"] = period_end
                self.rowcount = 1
        elif statement.startswith("select id, invoice_type, uploaded_at, status, processing_status, metadata_json"):
            rows = []
            for did, doc in self.invoice_documents.items():
                rows.append(
                    (
                        did,
                        doc.get("invoice_type"),
                        doc.get("uploaded_at"),
                        doc.get("status"),
                        doc.get("processing_status"),
                        doc.get("metadata_json"),
                    )
                )
            self._results = rows
        elif statement.startswith("select invoice_type, status, processing_status, period_start, period_end, uploaded_at, metadata_json from invoice_documents"):
            doc_id = params[0]
            doc = self.invoice_documents.get(doc_id)
            if doc:
                self._results = [
                    (
                        doc.get("invoice_type"),
                        doc.get("status"),
                        doc.get("processing_status"),
                        doc.get("period_start"),
                        doc.get("period_end"),
                        doc.get("uploaded_at"),
                        doc.get("metadata_json"),
                    )
                ]
            else:
                self._results = []
        elif statement.startswith("select metadata_json from invoice_documents"):
            doc_id = params[0]
            doc = self.invoice_documents.get(doc_id)
            self._results = [(doc["metadata_json"],)] if doc else []
        elif (
            (
                statement.startswith("select count(1), sum(case when match_status")
                or statement.startswith("select count(*), sum(case when match_status")
            )
            and "from invoice_lines" in statement
        ):
            invoice_id = params[0]
            lines = [ln for ln in self.invoice_lines if ln["invoice_id"] == invoice_id]
            total = len(lines)
            matched = sum(1 for ln in lines if ln.get("match_status") in {"auto", "manual", "confirmed"})
            self._results = [(total, matched)]
        elif statement.startswith("select id, transaction_date, amount, merchant_name, description, match_status, match_score, matched_file_id"):
            invoice_id, limit, offset = params
            lines = [ln for ln in self.invoice_lines if ln["invoice_id"] == invoice_id]
            lines.sort(key=lambda ln: (ln.get("transaction_date") or "", ln["id"]))
            rows = []
            for ln in lines[offset: offset + limit]:
                rows.append(
                    (
                        ln["id"],
                        ln.get("transaction_date"),
                        ln.get("amount"),
                        ln.get("merchant_name"),
                        ln.get("description"),
                        ln.get("match_status"),
                        ln.get("match_score"),
                        ln.get("matched_file_id"),
                    )
                )
            self._results = rows
        elif "from invoice_lines as il" in statement and "left join unified_files" in statement:
            invoice_id = params[0]
            lines = [ln for ln in self.invoice_lines if ln["invoice_id"] == invoice_id]
            lines.sort(key=lambda ln: (ln.get("transaction_date") or "", ln["id"]))
            rows = []
            for ln in lines:
                receipt = self.unified_files.get(ln.get("matched_file_id"))
                purchase_dt = receipt.get("purchase_datetime") if receipt else None
                gross_amount = receipt.get("gross_amount") if receipt else None
                credit_flag = receipt.get("credit_card_match") if receipt else None
                vendor_name = None
                if receipt and receipt.get("company_id") in self.companies:
                    vendor_name = self.companies[receipt["company_id"]]["name"]
                rows.append(
                    (
                        ln["id"],
                        ln.get("transaction_date"),
                        ln.get("amount"),
                        ln.get("description"),
                        ln.get("match_status"),
                        ln.get("match_score"),
                        ln.get("matched_file_id"),
                        purchase_dt,
                        gross_amount,
                        credit_flag,
                        vendor_name,
                    )
                )
            self._results = rows
        elif statement.startswith("update invoice_lines set matched_file_id"):
            matched_file_id, match_score, match_status, line_id, *_allowed = params
            for ln in self.invoice_lines:
                if ln["id"] == int(line_id):
                    ln["matched_file_id"] = matched_file_id
                    ln["match_score"] = match_score
                    ln["match_status"] = match_status
                    self.rowcount = 1
                    break
        elif statement.startswith("update invoice_lines set match_status=%s where id=%s"):
            new_status, line_id, *allowed = params
            allowed_states = {state for state in allowed}
            for ln in self.invoice_lines:
                if ln["id"] == int(line_id):
                    current = ln.get("match_status")
                    if current in allowed_states or current is None:
                        ln["match_status"] = new_status
                        self.rowcount = 1
                    break
        elif statement.startswith("insert into invoice_line_history"):
            invoice_line_id = params[0]
            if len(params) == 3:
                new_matched_file_id = params[1]
                reason = params[2]
                action = "matched"
            elif len(params) == 2:
                new_matched_file_id = None
                reason = params[1]
                action = "no_match"
            else:
                new_matched_file_id = None
                reason = "auto-match"
                action = "matched"
            history = self.unified_files.setdefault("_history", [])
            history.append(
                {
                    "invoice_line_id": invoice_line_id,
                    "action": action,
                    "new_matched_file_id": new_matched_file_id,
                    "reason": reason,
                }
            )
            self.rowcount = 1
        elif statement.startswith("delete from invoice_lines"):
            invoice_id = params[0]
            before = len(self.invoice_lines)
            self.invoice_lines = [
                ln for ln in self.invoice_lines if ln["invoice_id"] != invoice_id
            ]
            self.rowcount = before - len(self.invoice_lines)
        elif statement.startswith("insert into invoice_lines"):
            columns_segment = sql_norm[sql_norm.index("(") + 1 : sql_norm.index(")")]
            columns = [col.strip() for col in columns_segment.split(",")]
            row = {column: value for column, value in zip(columns, params)}
            line_id = len(self.invoice_lines) + 1
            row.setdefault("invoice_id", row.get("invoice_id"))
            row.setdefault("match_status", None)
            row.setdefault("match_score", None)
            row.setdefault("matched_file_id", None)
            row.setdefault("extraction_confidence", row.get("extraction_confidence"))
            row.setdefault("ocr_source_text", row.get("ocr_source_text"))
            row["id"] = line_id
            self.invoice_lines.append(row)
            self.rowcount = 1
        elif statement.startswith(
            "select uf.id, uf.purchase_datetime, uf.gross_amount, uf.credit_card_match, uf.created_at, c.name, existing.id as matched_line_id, crm.invoice_item_id"
        ):
            rows = []
            for receipt in self.unified_files.values():
                company_id = receipt.get("company_id")
                vendor_name = None
                if company_id in self.companies:
                    vendor_name = self.companies[company_id]["name"]
                matched_line_id = None
                for ln in self.invoice_lines:
                    if ln.get("matched_file_id") == receipt["id"]:
                        matched_line_id = ln["id"]
                        break
                matched_invoice_item = None
                for match in self.creditcard_receipt_matches:
                    if match.get("receipt_id") == receipt["id"]:
                        matched_invoice_item = match.get("invoice_item_id")
                        break
                rows.append(
                    (
                        receipt["id"],
                        receipt.get("purchase_datetime"),
                        receipt.get("gross_amount"),
                        receipt.get("credit_card_match"),
                        receipt.get("created_at"),
                        vendor_name,
                        matched_line_id,
                        matched_invoice_item,
                    )
                )
            rows.sort(
                key=lambda r: (
                    r[1] if isinstance(r[1], datetime) else datetime.min,
                ),
                reverse=True,
            )
            self._results = rows[:200]
        elif statement.startswith(
            "select uf.id, uf.purchase_datetime, uf.gross_amount, uf.credit_card_match, uf.created_at, c.name from unified_files as uf"
        ):
            file_id = params[0]
            receipt = self.unified_files.get(file_id)
            if receipt:
                company_id = receipt.get("company_id")
                vendor_name = None
                if company_id in self.companies:
                    vendor_name = self.companies[company_id]["name"]
                self._results = [
                    (
                        receipt["id"],
                        receipt.get("purchase_datetime"),
                        receipt.get("gross_amount"),
                        receipt.get("credit_card_match"),
                        receipt.get("created_at"),
                        vendor_name,
                    )
                ]
            else:
                self._results = []
        else:
            # Unused query in these tests.
            self._results = []

    def fetchone(self):
        if not self._results:
            return None
        return self._results[0]

    def fetchall(self):
        return list(self._results)


@pytest.fixture()
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Flask:
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))

    class _LimiterStub:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def limit(self, *args: Any, **kwargs: Any):
            def decorator(func):
                return func

            return decorator

        def init_app(self, app: Flask) -> None:  # type: ignore[name-defined]
            return None

    monkeypatch.setitem(
        sys.modules,
        "flask_limiter",
        types.SimpleNamespace(Limiter=lambda *args, **kwargs: _LimiterStub()),
    )
    monkeypatch.setitem(
        sys.modules,
        "flask_limiter.util",
        types.SimpleNamespace(get_remote_address=lambda *args, **kwargs: "127.0.0.1"),
    )
    from api.app import app as flask_app
    return flask_app


def _patch_db(monkeypatch: pytest.MonkeyPatch, fake: FakeDB) -> None:
    from api import reconciliation_firstcard as module
    import api.ingest as ingest
    from services import invoice_status
    from services import tasks as tasks_module
    raw_processor = tasks_module.process_invoice_document
    while hasattr(raw_processor, "__wrapped__"):
        raw_processor = getattr(raw_processor, "__wrapped__")  # type: ignore[attr-defined]
    monkeypatch.setattr(tasks_module, "process_invoice_document", raw_processor)

    raw_match = tasks_module.process_matching
    while hasattr(raw_match, "__wrapped__"):
        raw_match = getattr(raw_match, "__wrapped__")  # type: ignore[attr-defined]
    monkeypatch.setattr(tasks_module, "process_matching", raw_match)

    def cursor_factory():
        return fake.cursor()

    monkeypatch.setattr(module, "db_cursor", cursor_factory)
    monkeypatch.setattr(ingest, "db_cursor", cursor_factory)
    monkeypatch.setattr(invoice_status, "db_cursor", cursor_factory)
    monkeypatch.setattr(tasks_module, "db_cursor", cursor_factory)


def _stub_tasks(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from api import reconciliation_firstcard as module
    from services import tasks as tasks_module

    calls: list[str] = []

    class StubTask:
        def delay(self, file_id: str) -> None:
            calls.append(file_id)

    monkeypatch.setattr(module, "process_ocr", StubTask())
    monkeypatch.setattr(tasks_module, "_maybe_advance_invoice_from_file", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks_module, "_set_invoice_metadata_field", lambda *args, **kwargs: None)
    return calls


def test_upload_invoice_pdf_creates_records(app: Flask, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    calls = _stub_tasks(monkeypatch)

    from api import reconciliation_firstcard as module

    page_dir = tmp_path / 'converted-pages'
    page_dir.mkdir(exist_ok=True)
    pages = []
    for idx, content in enumerate([b'page-1', b'page-2']):
        page_path = page_dir / f'page-{idx+1}.png'
        page_path.write_bytes(content)
        page_obj = type("Page", (), {"index": idx, "bytes": content, "path": page_path})()
        pages.append(page_obj)
    monkeypatch.setattr(module, "pdf_to_png_pages", lambda data, out, invoice_id, dpi=300: [type("Page", (), {"index": p.index, "bytes": p.bytes, "path": p.path})() for p in pages])

    client = app.test_client()
    data = {
        "invoice": (io.BytesIO(b"%PDF-1.4"), "sample.pdf"),
    }

    response = client.post(
        "/reconciliation/firstcard/upload-invoice",
        data=data,
        content_type="multipart/form-data",
    )

    assert response.status_code == 201
    payload = response.get_json()
    invoice_id = payload["invoice_id"]
    assert payload["page_count"] == 2
    assert len(payload["page_ids"]) == 2

    # Invoice document persisted with metadata
    assert invoice_id in fake.invoice_documents
    metadata = json.loads(fake.invoice_documents[invoice_id]["metadata_json"])
    assert metadata["page_count"] == 2
    assert metadata["processing_status"] == "ocr_pending"
    assert fake.invoice_documents[invoice_id]["status"] == "imported"
    assert fake.invoice_documents[invoice_id]["processing_status"] == "ocr_pending"

    # Unified files include the parent and pages
    assert invoice_id in fake.unified_files
    page_entries = [uid for uid in fake.unified_files if uid != invoice_id]
    assert len(page_entries) == 2

    # OCR queued for each page
    assert set(calls) == set(payload["page_ids"])


def test_process_invoice_document_parses_credit_card_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)

    from services import tasks as tasks_module

    transitions: list[tuple[str, InvoiceProcessingStatus]] = []
    document_transitions: list[tuple[str, InvoiceDocumentStatus]] = []

    def record_processing(doc_id: str, target: InvoiceProcessingStatus, allowed: tuple[InvoiceProcessingStatus, ...]) -> bool:
        transitions.append((doc_id, target))
        return True

    def record_document(doc_id: str, target: InvoiceDocumentStatus, allowed: tuple[InvoiceDocumentStatus, ...]) -> bool:
        document_transitions.append((doc_id, target))
        return True

    monkeypatch.setattr(tasks_module, "transition_processing_status", record_processing)
    monkeypatch.setattr(tasks_module, "transition_document_status", record_document)

    class StubAIService:
        def __init__(self) -> None:
            self.prompt_provider_names = {"credit_card_invoice_parsing": "openai"}
            self.prompt_model_names = {"credit_card_invoice_parsing": "gpt-test"}

        def parse_credit_card_invoice(self, request):
            header = CreditCardInvoiceHeader(
                invoice_number="FC-2025-09",
                period_start=date(2025, 9, 1),
                period_end=date(2025, 9, 30),
                card_holder="Test User",
                card_number_masked="****1234",
                currency="SEK",
                invoice_total=Decimal("1000.00"),
                amount_to_pay=Decimal("1000.00"),
            )
            line = CreditCardInvoiceLine(
                line_no=1,
                transaction_id="ABC123",
                purchase_date=date(2025, 9, 10),
                merchant_name="Test Merchant",
                currency_original="SEK",
                amount_original=Decimal("1000.00"),
                amount_sek=Decimal("1000.00"),
                gross_amount=Decimal("1000.00"),
                confidence=0.95,
                source_text="2025-09-10 Test Merchant 1000,00",
            )
            return CreditCardInvoiceExtractionResponse(
                invoice_id=request.invoice_id,
                header=header,
                lines=[line],
                overall_confidence=0.95,
            )

    monkeypatch.setattr(tasks_module, "AIService", lambda: StubAIService())

    invoice_id = str(uuid.uuid4())
    page_id = f"{invoice_id}-page-1"
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "ocr_done",
        "processing_status": "ocr_done",
        "metadata_json": json.dumps(
            {
                "source_file_id": invoice_id,
                "page_ids": [page_id],
                "page_count": 1,
                "processing_status": "ocr_done",
            }
        ),
        "uploaded_at": datetime.now(),
    }
    fake.unified_files[invoice_id] = {
        "id": invoice_id,
        "file_type": "invoice",
        "ai_status": "ocr_done",
        "other_data": json.dumps({"page_number": 0}),
        "ocr_raw": "Invoice header text",
        "content_hash": "hash-parent",
        "original_file_id": invoice_id,
    }
    fake.unified_files[page_id] = {
        "id": page_id,
        "file_type": "invoice_page",
        "ai_status": "ocr_done",
        "other_data": json.dumps({"page_number": 1}),
        "ocr_raw": "2025-09-10 Test Merchant 1000,00",
        "content_hash": "hash-page",
        "original_file_id": invoice_id,
    }

    result = tasks_module.process_invoice_document(invoice_id)

    assert result["ok"] is True
    assert result["status"] == InvoiceProcessingStatus.READY_FOR_MATCHING.value
    assert result["lines"] == 1
    assert result["creditcard_main_id"] is not None
    assert result["confidence"] == 0.95

    assert len(fake.creditcard_invoices_main) == 1
    main_id, header_row = next(iter(fake.creditcard_invoices_main.items()))
    assert header_row["invoice_number"] == "FC-2025-09"
    assert header_row.get("card_holder") == "Test User"
    assert header_row.get("currency") == "SEK"

    assert len(fake.creditcard_invoice_items) == 1
    item_row = fake.creditcard_invoice_items[0]
    assert item_row["main_id"] == main_id
    assert item_row["merchant_name"] == "Test Merchant"
    assert Decimal(str(item_row.get("amount_sek"))) == Decimal("1000.00")

    metadata = json.loads(fake.invoice_documents[invoice_id]["metadata_json"])
    assert metadata["creditcard_main_id"] == main_id
    assert metadata["invoice_summary"]["card_holder"] == "Test User"
    assert metadata["overall_confidence"] == 0.95
    assert metadata["line_counts"]["total"] == 1

    assert any(target == InvoiceProcessingStatus.READY_FOR_MATCHING for _, target in transitions)
    assert any(target == InvoiceDocumentStatus.MATCHING for _, target in document_transitions)


def test_invoice_status_and_lines_endpoint(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    _stub_tasks(monkeypatch)

    invoice_id = str(uuid.uuid4())
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "processing",
        "metadata_json": json.dumps(
            {
                "source_file_id": invoice_id,
                "processing_status": "ocr_pending",
                "page_count": 1,
                "page_ids": [invoice_id],
                "detected_kind": "image",
                "overall_confidence": 0.82,
                "invoice_summary": {"invoice_number": "FC-2025-09", "card_holder": "Tester"},
                "creditcard_main_id": 77,
            }
        ),
    }
    fake.unified_files[invoice_id] = {
        "id": invoice_id,
        "file_type": "invoice",
        "ai_status": "ocr_done",
        "other_data": json.dumps({"page_number": 1}),
        "ocr_raw": "Sample OCR text",
        "content_hash": "hash",
        "original_file_id": invoice_id,
    }
    fake.invoice_lines.append(
        {
            "id": 1,
            "invoice_id": invoice_id,
            "transaction_date": "2025-10-04",
            "amount": 123.45,
            "merchant_name": "Cafe",
            "description": "Latte",
            "match_status": "auto",
            "match_score": 0.9,
            "matched_file_id": "receipt-1",
        }
    )
    fake.invoice_lines.append(
        {
            "id": 2,
            "invoice_id": invoice_id,
            "transaction_date": "2025-10-05",
            "amount": 78.0,
            "merchant_name": "Taxi",
            "description": "Airport",
            "match_status": None,
            "match_score": None,
            "matched_file_id": None,
        }
    )

    client = app.test_client()

    status_response = client.get(f"/reconciliation/firstcard/invoices/{invoice_id}/status")
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["ocr_progress"]["completed_pages"] == 1
    assert status_payload["ocr_progress"]["percentage"] == 100.0
    assert status_payload["line_counts"]["total"] == 2
    assert status_payload["line_counts"]["matched"] == 1
    assert status_payload["ai_summary"].startswith("Sample OCR")
    assert status_payload["overall_confidence"] == 0.82
    assert status_payload["invoice_summary"]["invoice_number"] == "FC-2025-09"
    assert status_payload["creditcard_main_id"] == 77

    lines_response = client.get(f"/reconciliation/firstcard/invoices/{invoice_id}/lines?limit=1")
    assert lines_response.status_code == 200
    lines_payload = lines_response.get_json()
    assert lines_payload["total"] == 2
    assert lines_payload["matched"] == 1
    assert len(lines_payload["items"]) == 1
    assert lines_payload["items"][0]["merchant_name"] == "Cafe"
    assert lines_payload["next_offset"] == 1


def test_list_statements_includes_processing_metadata(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    _stub_tasks(monkeypatch)

    invoice_id = str(uuid.uuid4())
    metadata = {
        "processing_status": "ready_for_matching",
        "period_start": "2025-09-01",
        "period_end": "2025-09-30",
        "line_counts": {"total": 3, "matched": 1},
        "submitted_by": "tester",
        "overall_confidence": 0.9,
        "invoice_summary": {"invoice_number": "FC-2025-09", "card_holder": "Tester"},
        "creditcard_main_id": 42,
    }
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "imported",
        "processing_status": "ready_for_matching",
        "metadata_json": json.dumps(metadata),
        "uploaded_at": datetime.now(),
        "period_start": "2025-09-01",
        "period_end": "2025-09-30",
    }

    client = app.test_client()
    response = client.get("/reconciliation/firstcard/statements")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    item = payload["items"][0]
    assert item["invoice_type"] == "credit_card_invoice"
    assert item["processing_status"] == "ready_for_matching"
    assert item["period_start"] == "2025-09-01"
    assert item["line_counts"]["total"] == 3
    assert item["line_counts"]["matched"] == 1
    assert item["line_counts"]["unmatched"] == 2
    assert item["overall_confidence"] == 0.9
    assert item["invoice_summary"]["invoice_number"] == "FC-2025-09"
    assert item["creditcard_main_id"] == 42


def test_invoice_detail_includes_matched_receipt(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    _stub_tasks(monkeypatch)

    invoice_id = str(uuid.uuid4())
    receipt_id = str(uuid.uuid4())
    company_id = 101
    metadata = {
        "processing_status": "ready_for_matching",
        "submitted_by": "tester",
    }
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "imported",
        "processing_status": "ready_for_matching",
        "metadata_json": json.dumps(metadata),
        "uploaded_at": datetime(2025, 9, 21, 9, 0),
        "period_start": "2025-09-01",
        "period_end": "2025-09-30",
    }
    fake.invoice_lines.append(
        {
            "id": 1,
            "invoice_id": invoice_id,
            "transaction_date": "2025-09-05",
            "amount": 150.25,
            "merchant_name": "Coffee Shop",
            "description": "Coffee",
            "match_status": "auto",
            "match_score": 0.92,
            "matched_file_id": receipt_id,
        }
    )
    fake.unified_files[receipt_id] = {
        "id": receipt_id,
        "file_type": "receipt",
        "purchase_datetime": datetime(2025, 9, 5, 12, 0),
        "gross_amount": 150.25,
        "credit_card_match": 1,
        "company_id": company_id,
        "created_at": datetime(2025, 9, 6, 8, 30),
    }
    fake.companies[company_id] = {"id": company_id, "name": "Coffee Shop AB"}

    client = app.test_client()
    response = client.get(f"/reconciliation/firstcard/invoices/{invoice_id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["invoice"]["id"] == invoice_id
    assert payload["invoice"]["line_counts"]["matched"] == 1
    assert payload["invoice"]["line_counts"]["unmatched"] == 0
    assert payload["invoice"]["metadata"]["submitted_by"] == "tester"
    assert len(payload["lines"]) == 1
    line = payload["lines"][0]
    assert line["matched_file_id"] == receipt_id
    assert line["matched_receipt"]["vendor_name"] == "Coffee Shop AB"
    assert line["matched_receipt"]["credit_card_match"] is True


def test_line_candidates_excludes_matched_receipts(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    _stub_tasks(monkeypatch)

    invoice_id = str(uuid.uuid4())
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "imported",
        "processing_status": "ready_for_matching",
        "metadata_json": json.dumps({"processing_status": "ready_for_matching"}),
        "uploaded_at": datetime.now(),
    }
    candidate_receipt_id = str(uuid.uuid4())
    excluded_receipt_id = str(uuid.uuid4())
    creditcard_matched_id = str(uuid.uuid4())
    other_line_receipt = str(uuid.uuid4())

    fake.invoice_lines.append(
        {
            "id": 1,
            "invoice_id": invoice_id,
            "transaction_date": "2025-09-10",
            "amount": 200.00,
            "merchant_name": "Target Cafe",
            "description": "Lunch",
            "match_status": "pending",
            "match_score": None,
            "matched_file_id": None,
        }
    )
    fake.invoice_lines.append(
        {
            "id": 2,
            "invoice_id": invoice_id,
            "transaction_date": "2025-09-09",
            "amount": 75.00,
            "merchant_name": "Other",
            "description": "Other",
            "match_status": "manual",
            "match_score": 0.8,
            "matched_file_id": other_line_receipt,
        }
    )

    fake.unified_files[candidate_receipt_id] = {
        "id": candidate_receipt_id,
        "purchase_datetime": datetime(2025, 9, 10, 14, 0),
        "gross_amount": 200.00,
        "credit_card_match": 0,
        "created_at": datetime(2025, 9, 11, 9, 0),
        "company_id": 201,
    }
    fake.unified_files[excluded_receipt_id] = {
        "id": excluded_receipt_id,
        "purchase_datetime": datetime(2025, 9, 10, 12, 0),
        "gross_amount": 200.00,
        "credit_card_match": 1,
        "created_at": datetime(2025, 9, 10, 13, 0),
        "company_id": 202,
    }
    fake.unified_files[creditcard_matched_id] = {
        "id": creditcard_matched_id,
        "purchase_datetime": datetime(2025, 9, 10, 15, 0),
        "gross_amount": 200.00,
        "credit_card_match": 0,
        "created_at": datetime(2025, 9, 10, 16, 0),
        "company_id": 203,
    }
    fake.unified_files[other_line_receipt] = {
        "id": other_line_receipt,
        "purchase_datetime": datetime(2025, 9, 9, 10, 0),
        "gross_amount": 75.00,
        "credit_card_match": 0,
        "created_at": datetime(2025, 9, 9, 11, 0),
        "company_id": 204,
    }
    fake.companies[201] = {"id": 201, "name": "Candidate Vendor"}
    fake.companies[202] = {"id": 202, "name": "Excluded Vendor"}
    fake.companies[203] = {"id": 203, "name": "CRM Vendor"}
    fake.companies[204] = {"id": 204, "name": "Other Vendor"}

    fake.creditcard_receipt_matches.append(
        {"receipt_id": creditcard_matched_id, "invoice_item_id": 99, "matched_amount": 200.00}
    )

    client = app.test_client()
    response = client.get("/reconciliation/firstcard/lines/1/candidates")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["line"]["id"] == 1
    assert payload["line"]["invoice_id"] == invoice_id
    candidate_ids = [item["file_id"] for item in payload["candidates"]]
    assert candidate_receipt_id in candidate_ids
    assert excluded_receipt_id not in candidate_ids
    assert creditcard_matched_id not in candidate_ids
    assert other_line_receipt not in candidate_ids
    first_candidate = payload["candidates"][0]
    assert first_candidate["file_id"] == candidate_receipt_id
    assert first_candidate["vendor_name"] == "Candidate Vendor"

def test_process_matching_auto_matches_lines(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    _stub_tasks(monkeypatch)

    from services import tasks as tasks_module

    invoice_id = str(uuid.uuid4())
    receipt_id = str(uuid.uuid4())
    metadata = {
        "processing_status": "ready_for_matching",
        "line_counts": {"total": 1, "matched": 0, "unmatched": 1},
        "page_count": 1,
        "page_ids": ["page-1"],
    }
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "imported",
        "processing_status": "ready_for_matching",
        "metadata_json": json.dumps(metadata),
        "uploaded_at": datetime.now(),
    }
    fake.invoice_lines.append(
        {
            "id": 1,
            "invoice_id": invoice_id,
            "transaction_date": "2025-09-05",
            "amount": 150.25,
            "merchant_name": "Coffee Shop",
            "description": "Coffee Shop",
            "match_status": "pending",
            "match_score": None,
            "matched_file_id": None,
        }
    )
    fake.unified_files[receipt_id] = {
        "id": receipt_id,
        "file_type": "receipt",
        "purchase_datetime": datetime(2025, 9, 5, 12, 0),
        "gross_amount": 150.25,
        "content_hash": f"hash-{receipt_id}",
        "company_name": "Coffee Shop AB",
        "credit_card_match": 0,
    }

    def fake_ai_match(request: Any) -> CreditCardMatchResponse:
        line_id = fake.invoice_lines[0]["id"]
        fake.creditcard_receipt_matches.append(
            {
                "receipt_id": request.file_id,
                "invoice_item_id": line_id,
                "matched_amount": float(request.amount),
            }
        )
        if request.file_id in fake.unified_files:
            fake.unified_files[request.file_id]["credit_card_match"] = 1
        return CreditCardMatchResponse(
            file_id=request.file_id,
            matched=True,
            credit_card_invoice_item_id=line_id,
            confidence=0.93,
            match_details={"matched_amount": float(request.amount)},
        )

    monkeypatch.setattr(tasks_module, "match_credit_card_internal", fake_ai_match)

    matched, pending = tasks_module._auto_match_invoice_lines(invoice_id)
    assert matched == 1

    tasks_module.process_matching(invoice_id)

    assert fake.invoice_lines[0]["matched_file_id"] == receipt_id
    assert fake.invoice_lines[0]["match_status"] == "auto"
    doc_metadata = json.loads(fake.invoice_documents[invoice_id]["metadata_json"])
    assert doc_metadata["line_counts"]["matched"] == 1
    assert fake.creditcard_receipt_matches
    assert fake.creditcard_receipt_matches[0]["receipt_id"] == receipt_id
    assert fake.creditcard_receipt_matches[0]["invoice_item_id"] == fake.invoice_lines[0]["id"]
    assert fake.unified_files[receipt_id]["credit_card_match"] == 1


def test_auto_match_marks_unmatched_when_no_receipts(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    _stub_tasks(monkeypatch)

    from services import tasks as tasks_module

    invoice_id = str(uuid.uuid4())
    metadata = {
        "processing_status": "ready_for_matching",
        "line_counts": {"total": 1, "matched": 0, "unmatched": 1},
        "page_count": 1,
        "page_ids": ["page-1"],
    }
    fake.invoice_documents[invoice_id] = {
        "invoice_type": "credit_card_invoice",
        "status": "imported",
        "processing_status": "ready_for_matching",
        "metadata_json": json.dumps(metadata),
        "uploaded_at": datetime.now(),
    }
    fake.invoice_lines.append(
        {
            "id": 1,
            "invoice_id": invoice_id,
            "transaction_date": "2025-09-10",
            "amount": 300.00,
            "merchant_name": "No Match Cafe",
            "description": "No Match Cafe",
            "match_status": "pending",
            "match_score": None,
            "matched_file_id": None,
        }
    )

    matched, pending = tasks_module._auto_match_invoice_lines(invoice_id)
    assert matched == 0
    assert pending == 1

    tasks_module.process_matching(invoice_id)

    assert fake.invoice_lines[0]["match_status"] == InvoiceLineMatchStatus.UNMATCHED.value
    history = fake.unified_files.get("_history", [])
    assert any(entry.get("reason") == "auto-match-ai5-unmatched" for entry in history)
