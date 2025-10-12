import sys
from decimal import Decimal
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "backend" / "src"
for candidate in (_REPO_ROOT, _SRC):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import backend.src.api.ai_processing as ai_processing  # type: ignore
from backend.src.models.ai_processing import (  # type: ignore
    AccountingProposal,
    Company,
    DataExtractionResponse,
    ReceiptItem,
    UnifiedFileBase,
)


class FakeCursor:
    def __init__(self, fetchone=None):
        self.fetchone_queue = list(fetchone or [])
        self.calls = []
        self.lastrowid = 99
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))
        if sql.strip().lower().startswith("update unified_files"):
            self.rowcount = 1

    def fetchone(self):
        if self.fetchone_queue:
            return self.fetchone_queue.pop(0)
        return None

    def fetchall(self):  # pragma: no cover - not needed here
        return []

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.started = False
        self.committed = False
        self.closed = False

    def start_transaction(self):
        self.started = True

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):  # pragma: no cover - not triggered in these tests
        self.committed = False

    def close(self):
        self.closed = True


def _build_extraction_response() -> DataExtractionResponse:
    unified = UnifiedFileBase(
        file_type="receipt",
        orgnr="556677-8899",
        payment_type="card",
        purchase_datetime=None,
        expense_type="corporate",
        gross_amount_original=Decimal("123.45"),
        net_amount_original=Decimal("98.76"),
        exchange_rate=Decimal("1"),
        currency="SEK",
        gross_amount_sek=Decimal("123.45"),
        net_amount_sek=Decimal("98.76"),
        other_data="{}",
        ocr_raw="Sample OCR text",
        ai_status=None,
        ai_confidence=None,
        mime_type=None,
        company_id=None,
        receipt_number="ABC-123",
        file_creation_timestamp=None,
        submitted_by=None,
        original_file_id=None,
        original_file_name=None,
        original_file_size=None,
        file_suffix=None,
        file_category=None,
        original_filename=None,
        approved_by=None,
        credit_card_match=False,
    )
    company = Company(
        name="Test Store",
        orgnr="556677-8899",
        address=None,
        address2=None,
        zip=None,
        city=None,
        country=None,
        phone=None,
        www=None,
    )
    items = [
        ReceiptItem(
            main_id="file-1",
            article_id="SKU-1",
            name="Coffee",
            number=1,
            item_price_ex_vat=Decimal("80.00"),
            item_price_inc_vat=Decimal("100.00"),
            item_total_price_ex_vat=Decimal("80.00"),
            item_total_price_inc_vat=Decimal("100.00"),
            currency="SEK",
            vat=Decimal("20.00"),
            vat_percentage=Decimal("25"),
        )
    ]
    return DataExtractionResponse(
        file_id="file-1",
        unified_file=unified,
        receipt_items=items,
        company=company,
        confidence=0.85,
    )


def test_persist_extraction_result_writes_company_and_receipts(monkeypatch):
    # fetchone returns: [company lookup by orgnr, company lookup by name, file exists check]
    fake_cursor = FakeCursor(fetchone=[None, None, ("file-1",)])
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(ai_processing, "get_connection", lambda: fake_conn)

    result = _build_extraction_response()
    ai_processing._persist_extraction_result("file-1", result)

    sql_statements = "\n".join(call[0] for call in fake_cursor.calls)
    assert "INSERT INTO companies" in sql_statements
    assert "DELETE FROM receipt_items" in sql_statements
    assert "INSERT INTO receipt_items" in sql_statements
    assert "UPDATE unified_files SET" in sql_statements
    assert fake_conn.committed is True


def test_persist_credit_card_match_updates_status(monkeypatch):
    fake_cursor = FakeCursor()
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(ai_processing, "get_connection", lambda: fake_conn)

    ai_processing._persist_credit_card_match(
        file_id="file-99",
        invoice_item_id=123,
        matched_amount=Decimal("199.00"),
        confidence=0.92,
        matched=True,
    )

    sql_statements = "\n".join(call[0] for call in fake_cursor.calls)
    assert "INSERT INTO creditcard_receipt_matches" in sql_statements
    assert sql_statements.count("UPDATE unified_files SET") >= 2  # stage + credit flag
    assert fake_conn.committed is True


def test_persist_accounting_proposals_replaces_rows(monkeypatch):
    fake_cursor = FakeCursor()
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(ai_processing, "get_connection", lambda: fake_conn)

    proposals = [
        AccountingProposal(
            receipt_id="file-77",
            account_code="2440",
            debit=Decimal("100"),
            credit=Decimal("0"),
            vat_rate=None,
            notes="Test",
        )
    ]

    ai_processing._persist_accounting_proposals(
        file_id="file-77",
        proposals=proposals,
        confidence=0.75,
    )

    sql_statements = "\n".join(call[0] for call in fake_cursor.calls)
    assert "DELETE FROM ai_accounting_proposals" in sql_statements
    assert "INSERT INTO ai_accounting_proposals" in sql_statements
    assert "UPDATE unified_files SET ai_status" in sql_statements
    assert fake_conn.committed is True
