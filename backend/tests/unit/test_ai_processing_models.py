from decimal import Decimal

import pytest

from backend.src.models.ai_processing import (
    CreditCardInvoiceLine,
    DocumentClassificationResponse,
    ReceiptItem,
    UnifiedFileBase,
)


def test_receipt_item_normalization_and_validation():
    item = ReceiptItem(
        main_id="file-1",
        article_id=None,
        name=" Milk ",
        number="2",
        item_price_inc_vat="12,50",
        currency="sek",
    )
    assert item.article_id == ""
    assert item.number == 2
    assert item.item_price_inc_vat == Decimal("12.50")
    assert item.currency == "SEK"


def test_receipt_item_requires_name():
    with pytest.raises(Exception):
        ReceiptItem(main_id="file-1", name="", number=1, currency="SEK")


def test_unified_file_normalizes_currency_and_exchange_rate():
    uf = UnifiedFileBase(
        file_type="receipt",
        currency="usd",
        exchange_rate="11.3333",
        gross_amount_original="10.235",
        net_amount_original="9.1",
    )
    assert uf.currency == "USD"
    assert uf.exchange_rate == Decimal("11.333300")
    assert uf.gross_amount_original == Decimal("10.24")
    assert uf.net_amount_original == Decimal("9.10")


def test_document_classification_response_normalizes_manual_review():
    resp = DocumentClassificationResponse(file_id="f1", document_type="manual review", confidence=0.8)
    assert resp.document_type == "Manual Review"


def test_credit_card_invoice_line_decimal_and_currency():
    line = CreditCardInvoiceLine(
        line_no=1,
        purchase_date=None,
        merchant_name="Store",
        currency_original="eur",
        amount_original="19,995",
        exchange_rate="10.1234567",
        gross_amount="19.995",
    )
    assert line.currency_original == "EUR"
    assert line.amount_original == Decimal("20.00")
    assert line.exchange_rate == Decimal("10.123457")
    assert line.gross_amount == Decimal("20.00")
