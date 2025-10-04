from __future__ import annotations

from contextlib import contextmanager

import pytest

from services import invoice_status
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
)


class MiniCursor:
    def __init__(self, documents: dict[str, dict[str, str]], lines: dict[int, dict[str, str | None]]):
        self.documents = documents
        self.lines = lines
        self._results: list[tuple] = []
        self._rowcount = 0

    def __enter__(self) -> "MiniCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, sql: str, params: tuple | list | None = None) -> None:
        params = tuple(params or ())
        statement = " ".join(sql.split()).lower()
        self._rowcount = 0
        if statement.startswith("update invoice_documents set processing_status=%s"):
            new_status, doc_id, *allowed = params
            doc = self.documents.get(doc_id)
            if doc and doc.get("processing_status") in allowed:
                doc["processing_status"] = new_status
                self._rowcount = 1
        elif statement.startswith("select processing_status from invoice_documents"):
            doc_id = params[0]
            doc = self.documents.get(doc_id)
            self._results = [(doc.get("processing_status"),)] if doc else []
        elif statement.startswith("update invoice_documents set status=%s"):
            new_status, doc_id, *allowed = params
            doc = self.documents.get(doc_id)
            if doc and doc.get("status") in allowed:
                doc["status"] = new_status
                self._rowcount = 1
        elif statement.startswith("select status from invoice_documents"):
            doc_id = params[0]
            doc = self.documents.get(doc_id)
            self._results = [(doc.get("status"),)] if doc else []
        elif statement.startswith("update invoice_lines set matched_file_id=%s"):
            file_id, score, new_status, line_id, *allowed = params
            line = self.lines.get(int(line_id))
            if line and line.get("match_status") in allowed:
                line["matched_file_id"] = file_id
                line["match_status"] = new_status
                self._rowcount = 1
        elif statement.startswith("select match_status from invoice_lines"):
            line_id = int(params[0])
            line = self.lines.get(line_id)
            self._results = [(line.get("match_status"),)] if line else []
        else:
            self._results = []

    def fetchone(self):
        return self._results[0] if self._results else None

    @property
    def rowcount(self) -> int:
        return self._rowcount


class MiniDB:
    def __init__(self) -> None:
        self.documents = {
            "doc-1": {
                "processing_status": InvoiceProcessingStatus.UPLOADED.value,
                "status": InvoiceDocumentStatus.IMPORTED.value,
            }
        }
        self.lines = {
            1: {
                "match_status": InvoiceLineMatchStatus.PENDING.value,
                "matched_file_id": None,
            }
        }

    @contextmanager
    def cursor(self) -> MiniCursor:
        yield MiniCursor(self.documents, self.lines)


@pytest.fixture(autouse=True)
def restore_db_cursor(monkeypatch):
    original = invoice_status.db_cursor
    yield
    invoice_status.db_cursor = original  # type: ignore


def test_transition_processing_status_updates_state(monkeypatch):
    db = MiniDB()
    monkeypatch.setattr(invoice_status, "db_cursor", db.cursor)
    calls: list[tuple] = []
    monkeypatch.setattr(invoice_status, "record_invoice_state_assertion", lambda *args: calls.append(args))

    ok = invoice_status.transition_processing_status(
        "doc-1",
        InvoiceProcessingStatus.OCR_PENDING,
        (InvoiceProcessingStatus.UPLOADED,),
    )

    assert ok is True
    assert db.documents["doc-1"]["processing_status"] == InvoiceProcessingStatus.OCR_PENDING.value
    assert calls == []


def test_transition_processing_status_illegal_emits_metric(monkeypatch):
    db = MiniDB()
    db.documents["doc-1"]["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
    monkeypatch.setattr(invoice_status, "db_cursor", db.cursor)
    calls: list[tuple] = []
    monkeypatch.setattr(invoice_status, "record_invoice_state_assertion", lambda *args: calls.append(args))

    ok = invoice_status.transition_processing_status(
        "doc-1",
        InvoiceProcessingStatus.OCR_PENDING,
        (InvoiceProcessingStatus.UPLOADED,),
    )

    assert ok is False
    assert calls[0][0] == "processing_status"
    assert calls[0][1] == InvoiceProcessingStatus.READY_FOR_MATCHING.value
    assert calls[0][2] == InvoiceProcessingStatus.OCR_PENDING.value


def test_transition_line_status_and_link(monkeypatch):
    db = MiniDB()
    monkeypatch.setattr(invoice_status, "db_cursor", db.cursor)
    calls: list[tuple] = []
    monkeypatch.setattr(invoice_status, "record_invoice_state_assertion", lambda *args: calls.append(args))

    ok = invoice_status.transition_line_status_and_link(
        1,
        "receipt-1",
        0.9,
        InvoiceLineMatchStatus.AUTO,
        (InvoiceLineMatchStatus.PENDING,),
    )

    assert ok is True
    assert db.lines[1]["matched_file_id"] == "receipt-1"
    assert db.lines[1]["match_status"] == InvoiceLineMatchStatus.AUTO.value
    assert calls == []

    # Illegal follow-up transition should emit a metric and keep previous value
    ok = invoice_status.transition_line_status_and_link(
        1,
        "receipt-2",
        0.8,
        InvoiceLineMatchStatus.AUTO,
        (InvoiceLineMatchStatus.PENDING,),
    )

    assert ok is False
    assert db.lines[1]["matched_file_id"] == "receipt-1"
    assert calls[-1][0] == "line_match_status"
    assert calls[-1][2] == InvoiceLineMatchStatus.AUTO.value
