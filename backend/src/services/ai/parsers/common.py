from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Optional

TWO_DECIMAL_PLACES = Decimal("0.01")


class AccountingProposalValidationError(ValueError):
    """Raised when AI4 accounting proposals fail validation."""


def _quantize_two_decimals(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _deep_clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively clean dictionary, converting empty strings to None."""
    for key, value in d.items():
        if isinstance(value, dict):
            _deep_clean_dict(value)
        elif isinstance(value, str) and not value.strip():
            d[key] = None
    return d


def _ensure_decimal(
    raw_value: Any,
    field: str,
    *,
    allow_zero: bool = True,
    allow_negative: bool = False,
) -> Decimal:
    """Normalize various numeric representations to Decimal with two decimals."""

    if raw_value is None:
        raise AccountingProposalValidationError(f"{field} is missing")

    if isinstance(raw_value, Decimal):
        value = raw_value
    elif isinstance(raw_value, (int, float)):
        value = Decimal(str(raw_value))
    elif isinstance(raw_value, str):
        cleaned = raw_value.strip()
        if not cleaned:
            raise AccountingProposalValidationError(f"{field} is empty")
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.replace(",", ".")
        cleaned = cleaned.replace("%", "")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if cleaned.count(".") > 1:
            parts = cleaned.split(".")
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        try:
            value = Decimal(cleaned)
        except InvalidOperation as exc:
            raise AccountingProposalValidationError(
                f"{field} has invalid numeric value: {raw_value!r}"
            ) from exc
    else:
        raise AccountingProposalValidationError(
            f"{field} has unsupported type: {type(raw_value).__name__}"
        )

    if not allow_negative and value < 0:
        raise AccountingProposalValidationError(f"{field} must be non-negative")
    if not allow_zero and value == 0:
        raise AccountingProposalValidationError(f"{field} must be greater than zero")

    return _quantize_two_decimals(value)
