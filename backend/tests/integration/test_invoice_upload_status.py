import io
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pytest
from flask import Flask


class FakeDB:
    """In-memory simulation of the limited SQL used by the invoice endpoints."""

    def __init__(self) -> None:
        self.unified_files: Dict[str, Dict[str, Any]] = {}
        self.invoice_documents: Dict[str, Dict[str, Any]] = {}
        self.invoice_lines: List[Dict[str, Any]] = []
        self._results: List[Any] = []

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
        statement = " ".join(str(sql).split()).lower()
        params = params or ()

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
            }
        elif statement.startswith("update unified_files set other_data"):
            other_data, file_id = params
            if file_id in self.unified_files:
                self.unified_files[file_id]["other_data"] = other_data
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
        elif statement.startswith("update unified_files set ai_status=%s, ai_confidence"):
            ai_status, _confidence, file_id = params
            if file_id in self.unified_files:
                self.unified_files[file_id]["ai_status"] = ai_status
        elif statement.startswith("update unified_files set ai_status"):
            ai_status, file_id = params
            if file_id in self.unified_files:
                self.unified_files[file_id]["ai_status"] = ai_status
        elif statement.startswith("insert into invoice_documents"):
            doc_id, invoice_type, status, metadata_json = params
            self.invoice_documents[doc_id] = {
                "invoice_type": invoice_type,
                "status": status,
                "metadata_json": metadata_json,
            }
        elif statement.startswith("update invoice_documents set status="):
            status, metadata_json, doc_id = params
            if doc_id in self.invoice_documents:
                self.invoice_documents[doc_id]["status"] = status
                self.invoice_documents[doc_id]["metadata_json"] = metadata_json
        elif statement.startswith("select status, metadata_json from invoice_documents"):
            doc_id = params[0]
            doc = self.invoice_documents.get(doc_id)
            self._results = [
                (doc["status"], doc["metadata_json"])
            ] if doc else []
        elif statement.startswith("select count(1), sum(case when match_status") and "from invoice_lines" in statement:
            invoice_id = params[0]
            lines = [ln for ln in self.invoice_lines if ln["invoice_id"] == invoice_id]
            total = len(lines)
            matched = sum(1 for ln in lines if ln.get("match_status") in {"auto", "manual"})
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
        elif statement.startswith("insert into invoice_lines"):
            invoice_id, transaction_date, amount, merchant_name, description = params
            line_id = len(self.invoice_lines) + 1
            self.invoice_lines.append(
                {
                    "id": line_id,
                    "invoice_id": invoice_id,
                    "transaction_date": transaction_date,
                    "amount": amount,
                    "merchant_name": merchant_name,
                    "description": description,
                    "match_status": None,
                    "match_score": None,
                    "matched_file_id": None,
                }
            )
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
    from api.app import app as flask_app
    return flask_app


def _patch_db(monkeypatch: pytest.MonkeyPatch, fake: FakeDB) -> None:
    from api import reconciliation_firstcard as module
    import api.ingest as ingest

    def cursor_factory():
        return fake.cursor()

    monkeypatch.setattr(module, "db_cursor", cursor_factory)
    monkeypatch.setattr(ingest, "db_cursor", cursor_factory)


def _stub_tasks(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from api import reconciliation_firstcard as module

    calls: list[str] = []

    class StubTask:
        def delay(self, file_id: str) -> None:
            calls.append(file_id)

    monkeypatch.setattr(module, "process_ocr", StubTask())
    return calls


def test_upload_invoice_pdf_creates_records(app: Flask, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = FakeDB()
    _patch_db(monkeypatch, fake)
    calls = _stub_tasks(monkeypatch)

    from api import reconciliation_firstcard as module

    pages = [
        type("Page", (), {"index": 0, "bytes": b"page-1"})(),
        type("Page", (), {"index": 1, "bytes": b"page-2"})(),
    ]
    monkeypatch.setattr(module, "pdf_to_png_pages", lambda data, out, invoice_id, dpi=300: pages)

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

    # Unified files include the parent and pages
    assert invoice_id in fake.unified_files
    page_entries = [uid for uid in fake.unified_files if uid != invoice_id]
    assert len(page_entries) == 2

    # OCR queued for each page
    assert set(calls) == set(payload["page_ids"])


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

    lines_response = client.get(f"/reconciliation/firstcard/invoices/{invoice_id}/lines?limit=1")
    assert lines_response.status_code == 200
    lines_payload = lines_response.get_json()
    assert lines_payload["total"] == 2
    assert lines_payload["matched"] == 1
    assert len(lines_payload["items"]) == 1
    assert lines_payload["items"][0]["merchant_name"] == "Cafe"
    assert lines_payload["next_offset"] == 1
