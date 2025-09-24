import sys
from pathlib import Path
from datetime import datetime, timezone

# Ensure backend/src is on path when running tests directly
ROOT = Path(__file__).resolve().parents[2]  # .../backend
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

models_receipts = import_module("models.receipts")
models_catalog = import_module("models.catalog")
services = import_module("services")

Receipt = models_receipts.Receipt
Company = models_catalog.Company

normalize_orgnr = services.normalize_orgnr
DictCompanyProvider = services.DictCompanyProvider
enrich_receipt = services.enrich_receipt


def make_receipt(orgnr: str | None):
    return Receipt(
        id="R2",
        submitted_by="u",
        submitted_at=datetime.now(timezone.utc),
        pages=[],
        tags=[],
        location_opt_in=False,
        merchant_name="Acme",
        orgnr=orgnr,
        purchase_datetime=None,
        gross_amount=None,
        net_amount=None,
        vat_breakdown={},
        company_card_flag=False,
        confidence_summary=None,
    )


def test_normalize_orgnr_accepts_10_digits_with_luhn():
    # A made-up but Luhn-valid 10-digit orgnr (calculate with our helper expectation)
    # We'll use 556677889? where ? is computed so normalize returns it.
    base = "556677889"
    # compute checksum the same way as implementation
    digits = [int(x) for x in base]
    total = 0
    for idx, n in enumerate(digits):
        mul = 2 if idx % 2 == 0 else 1
        v = n * mul
        if v > 9:
            v -= 9
        total += v
    checksum = (10 - (total % 10)) % 10
    valid = base + str(checksum)

    assert normalize_orgnr(valid) == valid


def test_normalize_orgnr_rejects_bad_lengths():
    assert normalize_orgnr("123") is None
    assert normalize_orgnr("") is None


def test_normalize_orgnr_handles_12_digit_form():
    # Build a valid 10-digit first, then ensure 12-digit form normalizes to it
    base = "556677889"
    digits = [int(x) for x in base]
    total = 0
    for idx, n in enumerate(digits):
        mul = 2 if idx % 2 == 0 else 1
        v = n * mul
        if v > 9:
            v -= 9
        total += v
    checksum = (10 - (total % 10)) % 10
    ten = base + str(checksum)

    assert normalize_orgnr(ten) == ten
    twelve = "20" + ten
    assert normalize_orgnr(twelve) == ten


def test_enrich_receipt_with_provider():
    # Use a valid orgnr
    base = "556677889"
    digits = [int(x) for x in base]
    total = 0
    for idx, n in enumerate(digits):
        mul = 2 if idx % 2 == 0 else 1
        v = n * mul
        if v > 9:
            v -= 9
        total += v
    checksum = (10 - (total % 10)) % 10
    ten = base + str(checksum)
    provider = DictCompanyProvider({ten: "ACME AB"})
    r = make_receipt(orgnr=ten)
    company = enrich_receipt(r, provider)
    assert company is not None
    assert isinstance(company, Company)
    assert company.legal_name == "ACME AB"


def test_enrich_receipt_invalid_orgnr_returns_none():
    provider = DictCompanyProvider({})
    r = make_receipt(orgnr="12345")
    assert enrich_receipt(r, provider) is None
