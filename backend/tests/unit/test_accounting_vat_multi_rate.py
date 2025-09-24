import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

models_receipts = import_module("models.receipts")
services = import_module("services")

Receipt = models_receipts.Receipt
propose_accounting_entries = services.propose_accounting_entries


def test_vat_multi_rate_mapping_and_balanced():
    r = Receipt(
        id="Rmulti",
        submitted_by="u",
        submitted_at=datetime.now(timezone.utc),
        pages=[],
        tags=[],
        location_opt_in=False,
        merchant_name="Store",
        orgnr=None,
        purchase_datetime=None,
        gross_amount=Decimal("118.00"),
        net_amount=Decimal("100.00"),
        vat_breakdown={25: Decimal("18.00")},
        company_card_flag=False,
        confidence_summary=None,
    )
    entries = propose_accounting_entries(r)
    # Expect 3 entries: expense 100, VAT 18 to 2641, credit 118
    assert len(entries) == 3
    vat = next(e for e in entries if e.debit == Decimal("18.00"))
    assert vat.account_code in ("2641", "2642", "2643", "2640")
    assert sum(e.debit for e in entries) == sum(e.credit for e in entries) == Decimal("118.00")
