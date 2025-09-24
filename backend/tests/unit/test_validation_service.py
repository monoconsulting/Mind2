import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend/src is on path when running tests directly
ROOT = Path(__file__).resolve().parents[2]  # .../backend
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

models_receipts = import_module("models.receipts")
services_validation = import_module("services.validation")

Receipt = models_receipts.Receipt
ReceiptStatus = models_receipts.ReceiptStatus
validate_receipt = services_validation.validate_receipt
DEFAULT_CONFIDENCE_THRESHOLD = services_validation.DEFAULT_CONFIDENCE_THRESHOLD


def make_base_receipt(**overrides):
    now = datetime.now(timezone.utc)
    base = Receipt(
        id="R1",
        submitted_by="u1",
        submitted_at=now,
        pages=["p1"],
        tags=[],
        location_opt_in=False,
        merchant_name="Cafe",
        orgnr=None,
        purchase_datetime=now - timedelta(days=1),
        gross_amount=Decimal("112.00"),
        net_amount=Decimal("100.00"),
        vat_breakdown={12: Decimal("12.00")},
        company_card_flag=False,
        confidence_summary=0.9,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_validate_receipt_happy_path_passed():
    r = make_base_receipt()
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.PASSED
    assert report.messages == []


def test_validate_receipt_rounding_info():
    # Introduce a tiny rounding diff within tolerance -> INFO
    r = make_base_receipt(gross_amount=Decimal("112.01"))
    report = validate_receipt(r)
    assert report.status in (ReceiptStatus.PASSED, ReceiptStatus.MANUAL_REVIEW)
    assert any("rounding" in m.message for m in report.messages)


def test_low_confidence_triggers_manual_review():
    r = make_base_receipt(confidence_summary=DEFAULT_CONFIDENCE_THRESHOLD - 0.1)
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.MANUAL_REVIEW
    assert any(m.field_ref == "confidence_summary" for m in report.messages)


def test_missing_fields_generate_warnings():
    r = make_base_receipt(merchant_name="", net_amount=None)
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.MANUAL_REVIEW
    fields = {m.field_ref for m in report.messages}
    assert {"merchant_name", "net_amount"}.issubset(fields)


def test_future_date_fails():
    r = make_base_receipt(purchase_datetime=datetime.now(timezone.utc) + timedelta(days=2))
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.FAILED
    assert any(
        m.field_ref == "purchase_datetime" and "future" in m.message
        for m in report.messages
    )


def test_invalid_vat_amount_and_rate():
    r = make_base_receipt(vat_breakdown={99: "abc", 12: Decimal("-1.00")})
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.FAILED
    msgs = "\n".join(m.message for m in report.messages)
    assert "Unknown VAT rate 99%" in msgs or "Invalid VAT rate key" in msgs
    assert "Non-numeric VAT amount" in msgs or "Negative VAT amount" in msgs


def test_gross_less_than_net_fails():
    r = make_base_receipt(gross_amount=Decimal("90.00"), net_amount=Decimal("100.00"))
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.FAILED
    assert any("less than net" in m.message for m in report.messages)


def test_net_plus_vat_not_equal_gross_error():
    r = make_base_receipt(gross_amount=Decimal("115.00"), net_amount=Decimal("100.00"), vat_breakdown={12: Decimal("12.00")})
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.FAILED
    assert any("Gross != Net + VAT" in m.message for m in report.messages)


def test_very_old_date_warning_manual_review():
    r = make_base_receipt(purchase_datetime=datetime.now(timezone.utc) - timedelta(days=365 * 11))
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.MANUAL_REVIEW
    assert any("unusually old" in m.message for m in report.messages)


def test_naive_datetime_is_treated_as_utc():
    now = datetime.now()
    r = make_base_receipt(purchase_datetime=now - timedelta(days=1))
    report = validate_receipt(r)
    # Should still pass given valid amounts and fields
    assert report.status == ReceiptStatus.PASSED


def test_missing_gross_warning():
    r = make_base_receipt(gross_amount=None)
    report = validate_receipt(r)
    assert report.status == ReceiptStatus.MANUAL_REVIEW
    assert any(m.field_ref == "gross_amount" and m.severity.name.lower() == "warning" for m in report.messages)


def test_confidence_none_does_not_warn():
    r = make_base_receipt(confidence_summary=None)
    report = validate_receipt(r)
    # Happy path otherwise; should remain PASSED and no confidence warning
    assert report.status == ReceiptStatus.PASSED
    assert all(m.field_ref != "confidence_summary" for m in report.messages)
