import json
import importlib
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ai_processing = importlib.import_module("backend.src.api.ai_processing")
from models.ai_processing import (
    AccountingProposal,
    Company,
    DataExtractionResponse,
    ReceiptItem,
    UnifiedFileBase,
)


class FakeCursor:
    def __init__(self, fetch_plan: Optional[Dict[str, List[Any]]] = None):
        self.fetch_plan = fetch_plan or {}
        self.executed: List[tuple[str, tuple[Any, ...] | None]] = []
        self._fetchone_queue: List[Any] = []
        self._fetchall_queue: List[List[Any]] = []
        self.lastrowid: int = 101

    def execute(self, query: str, params: Optional[tuple[Any, ...]] = None):
        self.executed.append((query, params))
        for key, responses in self.fetch_plan.items():
            if key in query:
                if responses:
                    value = responses.pop(0)
                    if isinstance(value, list):
                        self._fetchall_queue.append(value)
                    else:
                        self._fetchone_queue.append(value)
                break

    def fetchone(self):
        if self._fetchone_queue:
            return self._fetchone_queue.pop(0)
        return None

    def fetchall(self):
        if self._fetchall_queue:
            return self._fetchall_queue.pop(0)
        return []

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self.cursor_obj = cursor
        self.started = False
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def start_transaction(self):
        self.started = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.fixture
def capture_connection(monkeypatch):
    holder: Dict[str, Any] = {}

    def _install(cursor: FakeCursor):
        def _factory():
            conn = FakeConnection(cursor)
            holder["conn"] = conn
            return conn

        monkeypatch.setattr(ai_processing, "get_connection", _factory)
        return holder

    return _install


def build_extraction_response(file_id: str) -> DataExtractionResponse:
    unified = UnifiedFileBase(
        file_type="receipt",
        orgnr="556677-8899",
        payment_type="card",
        purchase_datetime=datetime(2024, 1, 5, 10, 15),
        expense_type="corporate",
        gross_amount_original=Decimal("125.50"),
        net_amount_original=Decimal("100.40"),
        exchange_rate=Decimal("1"),
        currency="SEK",
        gross_amount_sek=Decimal("125.50"),
        net_amount_sek=Decimal("100.40"),
        receipt_number="RCPT-001",
        other_data=json.dumps({"source": "unit-test"}),
        ocr_raw="Sample OCR text",
    )
    company = Company(
        name="Demo AB",
        orgnr="556677-8899",
        address=None,
        address2=None,
        zip=None,
        city=None,
        country=None,
        phone=None,
        www=None,
    )
    item = ReceiptItem(
        main_id=file_id,
        article_id="SKU-1",
        name="Coffee",
        number=1,
        item_price_ex_vat=Decimal("80.00"),
        item_price_inc_vat=Decimal("100.00"),
        item_total_price_ex_vat=Decimal("80.00"),
        item_total_price_inc_vat=Decimal("100.00"),
        currency="SEK",
        vat=Decimal("20.00"),
        vat_percentage=Decimal("0.250000"),
    )
    return DataExtractionResponse(
        file_id=file_id,
        unified_file=unified,
        receipt_items=[item],
        company=company,
        confidence=0.83,
    )


def test_persist_document_classification_updates_stage(monkeypatch, capture_connection):
    cursor = FakeCursor()
    holder = capture_connection(cursor)

    ai_processing._persist_document_classification("file-123", "receipt", 0.72)

    conn: FakeConnection = holder["conn"]
    assert conn.started and conn.committed and not conn.rolled_back
    query, params = cursor.executed[0]
    assert "ai_status" in query
    assert params == ("receipt", "ai1_completed", 0.72, "file-123")


def test_persist_expense_classification_updates_status(monkeypatch, capture_connection):
    cursor = FakeCursor()
    holder = capture_connection(cursor)

    ai_processing._persist_expense_classification("file-234", "corporate", 0.91)

    conn: FakeConnection = holder["conn"]
    assert conn.started and conn.committed and not conn.rolled_back
    query, params = cursor.executed[0]
    assert "ai_status" in query
    assert params == ("corporate", "ai2_completed", 0.91, "file-234")


def test_persist_extraction_result_refreshes_tables(monkeypatch, capture_connection):
    cursor = FakeCursor(fetch_plan={"SELECT id FROM companies": [None]})
    cursor.lastrowid = 555
    holder = capture_connection(cursor)

    response = build_extraction_response("file-345")
    ai_processing._persist_extraction_result("file-345", response)

    conn: FakeConnection = holder["conn"]
    assert conn.started and conn.committed and not conn.rolled_back

    statements = list(cursor.executed)
    assert any("INSERT INTO companies" in sql for sql, _ in statements)
    update_sql, update_params = next((sql, params) for sql, params in statements if "UPDATE unified_files" in sql)
    assert "ai3_completed" in update_params
    receipt_inserts = [sql for sql, _ in statements if "INSERT INTO receipt_items" in sql]
    assert receipt_inserts, "Receipt items should be inserted"


def test_persist_accounting_proposals_sets_stage(monkeypatch, capture_connection):
    cursor = FakeCursor()
    holder = capture_connection(cursor)

    proposal = AccountingProposal(
        receipt_id="file-456",
        account_code="2440",
        debit=Decimal("125.50"),
        credit=Decimal("0.00"),
        vat_rate=None,
        notes="Supplier liability",
    )

    ai_processing._persist_accounting_proposals("file-456", [proposal], 0.88)

    conn: FakeConnection = holder["conn"]
    assert conn.started and conn.committed and not conn.rolled_back
    update_sql, update_params = cursor.executed[-1]
    assert "ai4_completed" in update_params


def test_persist_credit_card_match_marks_completion(monkeypatch, capture_connection):
    cursor = FakeCursor()
    holder = capture_connection(cursor)

    ai_processing._persist_credit_card_match("file-567", 99, Decimal("321.00"), 0.93)

    conn: FakeConnection = holder["conn"]
    assert conn.started and conn.committed and not conn.rolled_back
    update_sql, params = cursor.executed[-1]
    assert "ai5_completed" in params
    assert params[0] == "ai5_completed"
    assert params[1] == 0.93
    assert params[2] == "file-567"
