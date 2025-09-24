from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Optional

from models.accounting import AccountingRule
from models.receipts import AccountingEntry, Receipt


# Simple Swedish BAS defaults
DEFAULT_EXPENSE_ACCOUNT = "5790"  # Övriga förbrukningsmaterial
DEFAULT_CREDIT_ACCOUNT = "2440"   # Leverantörsskulder
DEFAULT_CREDIT_ACCOUNT_CARD = "1930"  # Företagskonto (bank) for company card

VAT_ACCOUNT_BY_RATE: dict[int, str] = {
    25: "2641",  # Debiterad ingående moms, 25%
    12: "2642",  # Debiterad ingående moms, 12%
    6: "2643",   # Debiterad ingående moms, 6%
    0: "2640",   # Fallback
}


def _first_matching_rule(receipt: Receipt, rules: Iterable[AccountingRule]) -> Optional[AccountingRule]:
    merchant = (receipt.merchant_name or "").lower()
    tags = set((receipt.tags or []))
    for r in rules or []:
        ct = (r.condition_type or "").lower()
        cv = (r.condition_value or "").lower()
        if ct == "merchant_contains" and cv and cv in merchant:
            return r
        if ct == "tag" and cv and cv in {t.lower() for t in tags}:
            return r
    return None


def _decimal(val: Optional[Decimal]) -> Optional[Decimal]:
    if isinstance(val, Decimal):
        return val
    if val is None:
        return None
    return Decimal(str(val))


def _make_expense_entry(receipt: Receipt, account: str, amount: Optional[Decimal]) -> Optional[AccountingEntry]:
    if not amount or amount <= 0:
        return None
    return AccountingEntry(
        id=None,
        receipt_id=receipt.id or "",
        account_code=account,
        debit=amount,
        credit=Decimal("0"),
        vat_rate=None,
        notes=None,
    )


def _make_vat_entries(receipt: Receipt, breakdown: dict[int, Decimal]) -> List[AccountingEntry]:
    out: List[AccountingEntry] = []
    for rate, amount in (breakdown or {}).items():
        if not amount or amount <= 0:
            continue
        vat_acc = VAT_ACCOUNT_BY_RATE.get(int(rate), VAT_ACCOUNT_BY_RATE[0])
        out.append(
            AccountingEntry(
                id=None,
                receipt_id=receipt.id or "",
                account_code=vat_acc,
                debit=amount,
                credit=Decimal("0"),
                vat_rate=Decimal(str(rate)),
                notes=None,
            )
        )
    return out


def _make_credit_entry(receipt: Receipt, account: str, amount: Optional[Decimal]) -> Optional[AccountingEntry]:
    if not amount or amount <= 0:
        return None
    return AccountingEntry(
        id=None,
        receipt_id=receipt.id or "",
        account_code=account,
        debit=Decimal("0"),
        credit=amount,
        vat_rate=None,
        notes=None,
    )


def propose_accounting_entries(
    receipt: Receipt,
    rules: Optional[List[AccountingRule]] = None,
) -> List[AccountingEntry]:
    """Create a simple, balanced accounting proposal for a receipt.

    Strategy:
    - Determine expense account from first matching rule; else fallback to DEFAULT_EXPENSE_ACCOUNT.
    - Compute net, gross, and VAT breakdown (from receipt fields); if missing, infer net = gross - sum(VAT).
    - Create entries:
        • Debit expense account with net
        • Debit VAT account(s) per rate with VAT amount
        • Credit credit account with gross (1930 if company_card_flag else 2440)
    - Ensure amounts are non-negative and present before creating entries.
    """
    entries: List[AccountingEntry] = []

    gross = _decimal(receipt.gross_amount)
    net = _decimal(receipt.net_amount)
    vat_breakdown = receipt.vat_breakdown or {}
    vat_sum = sum(vat_breakdown.values(), Decimal("0")) if vat_breakdown else Decimal("0")

    if net is None and gross is not None:
        net = gross - vat_sum

    # Choose accounts
    rule = _first_matching_rule(receipt, rules or [])
    expense_account = rule.account_code if rule else DEFAULT_EXPENSE_ACCOUNT
    credit_account = DEFAULT_CREDIT_ACCOUNT_CARD if receipt.company_card_flag else DEFAULT_CREDIT_ACCOUNT

    # Expense debit
    exp = _make_expense_entry(receipt, expense_account, net)
    if exp:
        entries.append(exp)

    # VAT debits per rate
    entries.extend(_make_vat_entries(receipt, vat_breakdown or {}))

    # Credit side with gross
    cred = _make_credit_entry(receipt, credit_account, gross)
    if cred:
        entries.append(cred)

    return entries
