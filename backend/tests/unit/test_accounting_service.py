import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

# Ensure backend/src is on path when running tests directly
ROOT = Path(__file__).resolve().parents[2]  # .../backend
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

models_receipts = import_module("models.receipts")
models_accounting = import_module("models.accounting")
services = import_module("services")

Receipt = models_receipts.Receipt
AccountingRule = models_accounting.AccountingRule
propose_accounting_entries = services.propose_accounting_entries


def make_receipt(**overrides):
    base = Receipt(
        id="R100",
        submitted_by="u",
        submitted_at=datetime.now(timezone.utc),
        pages=[],
        tags=[],
        location_opt_in=False,
        merchant_name="Cafe Central",
        orgnr=None,
        purchase_datetime=None,
        gross_amount=Decimal("112.00"),
        net_amount=Decimal("100.00"),
        vat_breakdown={12: Decimal("12.00")},
        company_card_flag=False,
        confidence_summary=None,
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_proposal_basic_entries_and_balanced():
    r = make_receipt()
    entries = propose_accounting_entries(r, rules=[])

    # Expect 3 entries: expense debit (100), VAT debit (12), credit (112)
    assert len(entries) == 3
    total_debit = sum(e.debit for e in entries)
    total_credit = sum(e.credit for e in entries)
    assert total_debit == total_credit == Decimal("112.00")


def test_rules_override_expense_account():
    r = make_receipt()
    rules = [
        AccountingRule(
            id=None,
            name="Cafe rule",
            condition_type="merchant_contains",
            condition_value="cafe",
            account_code="4010",
        )
    ]
    entries = propose_accounting_entries(r, rules=rules)
    expense = next(e for e in entries if e.debit == Decimal("100.00"))
    assert expense.account_code == "4010"


def test_company_card_uses_bank_credit_account():
    r = make_receipt(company_card_flag=True)
    entries = propose_accounting_entries(r)
    credit = next(e for e in entries if e.credit == Decimal("112.00"))
    assert credit.account_code == "1930"


def test_missing_net_infers_from_gross_and_vat():
    r = make_receipt(net_amount=None)
    entries = propose_accounting_entries(r)
    expense = next(e for e in entries if e.debit == Decimal("100.00"))
    assert expense is not None
