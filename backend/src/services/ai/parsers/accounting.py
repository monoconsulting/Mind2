from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from models.ai_processing import AccountingProposal
from services.ai.parsers.common import (
    AccountingProposalValidationError,
    _ensure_decimal,
    _quantize_two_decimals,
)

logger = logging.getLogger(__name__)

ACCOUNT_CODE_KEYS = ("account_code", "account", "accountCode", "account_number")
DEBIT_KEYS = ("debit", "debit_amount")
CREDIT_KEYS = ("credit", "credit_amount")
VAT_KEYS = ("vat_rate", "vat", "vat_rate_percent", "vatPercent")
NOTES_KEYS = ("notes", "note", "memo", "description")
ITEM_ID_KEYS = ("item_id", "line_id", "line_item_id", "entry_id")
ZERO_DECIMAL = Decimal("0.00")


def _first_present(data: Dict[str, Any], keys: Iterable[str], field: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    raise AccountingProposalValidationError(f"{field} is missing")


def _extract_account_code(entry: Dict[str, Any]) -> str:
    for key in ACCOUNT_CODE_KEYS:
        value = entry.get(key)
        if value is None:
            continue
        code = str(value).strip()
        if not code:
            continue
        if len(code) > 32:
            raise AccountingProposalValidationError("account_code exceeds 32 characters")
        return code
    raise AccountingProposalValidationError("account_code is missing")


def _coerce_item_id(raw_value: Any, context: str) -> int:
    if raw_value is None:
        raise AccountingProposalValidationError(f"{context} is missing")
    try:
        item_id = int(str(raw_value))
    except (TypeError, ValueError) as exc:
        raise AccountingProposalValidationError(f"{context} must be an integer") from exc
    if item_id <= 0:
        raise AccountingProposalValidationError(f"{context} must be a positive integer")
    return item_id


def _extract_vat_rate(entry: Dict[str, Any]) -> Optional[Decimal]:
    for key in VAT_KEYS:
        if key in entry and entry[key] not in (None, ""):
            rate = _ensure_decimal(entry[key], "vat_rate")
            if rate < 0 or rate > 100:
                raise AccountingProposalValidationError("vat_rate must be between 0 and 100")
            return rate
    return None


def _extract_notes(entry: Dict[str, Any]) -> Optional[str]:
    for key in NOTES_KEYS:
        if key in entry and entry[key] is not None:
            text = str(entry[key]).strip()
            if not text:
                return None
            if len(text) > 255:
                logger.warning("AI4 note truncated to 255 characters: %s...", text[:32])
                return text[:255]
            return text
    return None


def _build_accounting_proposal(
    entry: Dict[str, Any],
    expected_receipt_id: str,
    *,
    context: str,
) -> AccountingProposal:
    receipt_id = str(entry.get("receipt_id") or "").strip()
    if not receipt_id:
        receipt_id = expected_receipt_id
    if receipt_id != expected_receipt_id:
        raise AccountingProposalValidationError(
            f"receipt_id mismatch (expected {expected_receipt_id}, got {receipt_id})"
        )

    raw_item_id = entry.get("item_id")
    if raw_item_id is None:
        raise AccountingProposalValidationError(f"{context}.item_id is missing")
    item_id = _coerce_item_id(raw_item_id, f"{context}.item_id")

    account_code = _extract_account_code(entry)
    debit_raw = _first_present(entry, DEBIT_KEYS, "debit")
    credit_raw = _first_present(entry, CREDIT_KEYS, "credit")
    debit = _ensure_decimal(debit_raw, "debit")
    credit = _ensure_decimal(credit_raw, "credit")

    if debit > 0 and credit > 0:
        raise AccountingProposalValidationError("debit and credit cannot both be greater than zero")
    if debit == 0 and credit == 0:
        raise AccountingProposalValidationError("debit and credit cannot both be zero")

    vat_rate = _extract_vat_rate(entry)
    notes = _extract_notes(entry)

    return AccountingProposal(
        receipt_id=expected_receipt_id,
        item_id=item_id,
        account_code=account_code,
        debit=_quantize_two_decimals(debit if debit > 0 else ZERO_DECIMAL),
        credit=_quantize_two_decimals(credit if credit > 0 else ZERO_DECIMAL),
        vat_rate=_quantize_two_decimals(vat_rate) if vat_rate is not None else None,
        notes=notes,
    )


def parse_accounting_proposals(payload: Dict[str, Any], fallback_receipt_id: str) -> List[AccountingProposal]:
    """Parse and validate AI4 payload into accounting proposals."""

    if not isinstance(payload, dict):
        raise AccountingProposalValidationError("LLM response must be a JSON object")

    receipt_id = str(payload.get("receipt_id") or fallback_receipt_id or "").strip()
    if not receipt_id:
        raise AccountingProposalValidationError("receipt_id is missing from payload")

    raw_entries: List[Tuple[Dict[str, Any], str]] = []

    if payload.get("items") is not None:
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise AccountingProposalValidationError("items must be a non-empty array")
        for item_index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise AccountingProposalValidationError(
                    f"items[{item_index}] must be an object"
                )
            raw_item_id = None
            for key in ITEM_ID_KEYS:
                if key in item and item[key] not in (None, ""):
                    raw_item_id = item[key]
                    break
            if raw_item_id is None:
                raise AccountingProposalValidationError(
                    f"items[{item_index}] is missing item_id"
                )
            entries = item.get("entries")
            if not isinstance(entries, list) or not entries:
                raise AccountingProposalValidationError(
                    f"items[{item_index}].entries must be a non-empty array"
                )
            for entry_index, entry in enumerate(entries, start=1):
                if not isinstance(entry, dict):
                    raise AccountingProposalValidationError(
                        f"items[{item_index}].entries[{entry_index}] must be an object"
                    )
                normalized = dict(entry)
                normalized.setdefault("item_id", raw_item_id)
                normalized.setdefault("receipt_id", receipt_id)
                raw_entries.append((normalized, f"items[{item_index}].entries[{entry_index}]"))
    elif payload.get("proposals") is not None:
        proposals = payload.get("proposals")
        if not isinstance(proposals, list) or not proposals:
            raise AccountingProposalValidationError("proposals must be a non-empty array")
        for idx, entry in enumerate(proposals, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"proposals[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"proposals[{idx}]"))
    elif payload.get("entries") is not None:
        # Accept 'entries' as an alias for 'proposals' (common LLM output format)
        entries = payload.get("entries")
        if not isinstance(entries, list) or not entries:
            raise AccountingProposalValidationError("entries must be a non-empty array")
        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"entries[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"entries[{idx}]"))
    elif payload.get("accounting_entries") is not None:
        # Accept 'accounting_entries' as an alias for 'proposals' (common LLM output format)
        accounting_entries = payload.get("accounting_entries")
        if not isinstance(accounting_entries, list) or not accounting_entries:
            raise AccountingProposalValidationError("accounting_entries must be a non-empty array")
        for idx, entry in enumerate(accounting_entries, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"accounting_entries[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"accounting_entries[{idx}]"))
    else:
        raise AccountingProposalValidationError(
            "Payload must include either 'items', 'proposals', 'entries', or 'accounting_entries'"
        )

    parsed: List[AccountingProposal] = []
    for entry, context in raw_entries:
        parsed.append(_build_accounting_proposal(entry, receipt_id, context=context))

    if not parsed:
        raise AccountingProposalValidationError("No accounting proposals generated from payload")

    return parsed
