from decimal import Decimal

import pytest

from services.ai_service import (
    AccountingProposalValidationError,
    parse_accounting_proposals,
)


def test_parse_accounting_proposals_valid_items_structure():
    payload = {
        "receipt_id": "receipt-123",
        "items": [
            {
                "item_id": 1,
                "entries": [
                    {
                        "account_code": "4010",
                        "debit": "125,40",
                        "credit": "0",
                        "vat": "25%",
                        "notes": "Lunch with client",
                    },
                    {
                        "account": "2641",
                        "debit_amount": 31.35,
                        "credit_amount": 0,
                        "vat_rate_percent": 25,
                    },
                ],
            }
        ],
    }

    proposals = parse_accounting_proposals(payload, "receipt-123")

    assert len(proposals) == 2
    assert proposals[0].receipt_id == "receipt-123"
    assert proposals[0].item_id == 1
    assert proposals[0].account_code == "4010"
    assert proposals[0].debit == Decimal("125.40")
    assert proposals[0].credit == Decimal("0.00")
    assert proposals[0].vat_rate == Decimal("25.00")
    assert proposals[0].notes == "Lunch with client"

    assert proposals[1].account_code == "2641"
    assert proposals[1].debit == Decimal("31.35")
    assert proposals[1].credit == Decimal("0.00")


def test_parse_accounting_proposals_accepts_proposals_array():
    payload = {
        "receipt_id": "receipt-xyz",
        "proposals": [
            {
                "item_id": "5",
                "account_code": "2440",
                "debit": 0,
                "credit": "300.99",
                "vat_rate": None,
            }
        ],
    }

    proposals = parse_accounting_proposals(payload, "receipt-xyz")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.item_id == 5
    assert proposal.credit == Decimal("300.99")
    assert proposal.debit == Decimal("0.00")


def test_parse_accounting_proposals_rejects_double_sided_entry():
    payload = {
        "receipt_id": "receipt-err",
        "items": [
            {
                "item_id": 2,
                "entries": [
                    {
                        "account_code": "7790",
                        "debit": "100.00",
                        "credit": "10.00",
                    }
                ],
            }
        ],
    }

    with pytest.raises(AccountingProposalValidationError, match="debit and credit cannot both be greater than zero"):
        parse_accounting_proposals(payload, "receipt-err")


def test_parse_accounting_proposals_truncates_long_notes():
    long_note = "a" * 300
    payload = {
        "receipt_id": "receipt-note",
        "items": [
            {
                "item_id": 3,
                "entries": [
                    {
                        "account_code": "4010",
                        "debit": "50",
                        "credit": "0",
                        "notes": long_note,
                    }
                ],
            }
        ],
    }

    proposals = parse_accounting_proposals(payload, "receipt-note")

    assert len(proposals) == 1
    assert len(proposals[0].notes) == 255
    assert proposals[0].notes == long_note[:255]
