from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


_LINE_PATTERN = re.compile(
    r"(20\d{2}-\d{2}-\d{2})\s+(.+?)\s+(-?\d+[.,]\d{2})"
)
_PERIOD_PATTERN = re.compile(
    r"Period\s*:?\s*(20\d{2}-\d{2}-\d{2})\s*(?:to|-)\s*(20\d{2}-\d{2}-\d{2})",
    re.IGNORECASE,
)


@dataclass(slots=True)
class ParsedInvoiceLine:
    transaction_date: str
    merchant_name: str
    description: str
    amount: float
    confidence: float
    raw_text: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "transaction_date": self.transaction_date,
            "merchant_name": self.merchant_name,
            "description": self.description,
            "amount": self.amount,
            "confidence": self.confidence,
            "raw_text": self.raw_text,
        }


def _normalise_amount(value: str) -> float:
    cleaned = value.replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_credit_card_statement(text: str) -> Dict[str, Any]:
    """
    Parse OCR text from a credit card invoice into structured data.

    The parser is intentionally conservative: it only extracts rows that match
    the canonical `YYYY-MM-DD  Merchant  123,45` pattern while preserving the
    original OCR snippet for auditability.
    """
    result: Dict[str, Any] = {
        "period_start": None,
        "period_end": None,
        "lines": [],
        "raw_text": text or "",
    }
    if not text:
        return result

    lines: List[ParsedInvoiceLine] = []
    for match in _LINE_PATTERN.finditer(text):
        transaction_date, merchant, amount = match.groups()
        merchant_clean = merchant.strip()
        raw_snippet = match.group(0).strip()
        parsed_line = ParsedInvoiceLine(
            transaction_date=transaction_date,
            merchant_name=merchant_clean,
            description=merchant_clean,
            amount=_normalise_amount(amount),
            confidence=0.85,
            raw_text=raw_snippet,
        )
        lines.append(parsed_line)

    period_match = _PERIOD_PATTERN.search(text)
    if period_match:
        result["period_start"], result["period_end"] = period_match.groups()

    result["lines"] = [line.as_dict() for line in lines]
    return result

