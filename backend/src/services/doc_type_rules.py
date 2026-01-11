from __future__ import annotations

import re
from typing import Optional, Tuple


_RECEIPT_EVIDENCE_RE = re.compile(
    r"\b(kvitto|k[öo]pkvitto|moms|vat|org\.?\s*nr|orgnr|summa|totalt|inkl\s*moms)\b",
    re.IGNORECASE,
)
_INVOICE_STRONG_RE = re.compile(
    r"\b(invoice\s*number|fakturanummer|faktura)\b",
    re.IGNORECASE,
)
_INVOICE_SUPPORT_RE = re.compile(
    r"\b(bill\s*to|total\s*excluding\s*tax|subtotal|amount\s*due|vat\s*-\s*sweden)\b",
    re.IGNORECASE,
)
_TERMINAL_SLIP_RE = re.compile(
    r"\b(aid|tvr|tsi|resp|ref|period|kontaktl|contactless|visa|mastercard|debit|"
    r"terminal|term|butiksnr|godk[aä]nt|k[öo]p)\b",
    re.IGNORECASE,
)


def _normalize_text(text: str | None) -> str:
    return (text or "").strip().lower()


def has_receipt_evidence(text: str | None) -> bool:
    return bool(_RECEIPT_EVIDENCE_RE.search(_normalize_text(text)))


def has_terminal_slip_signature(text: str | None) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    matches = _TERMINAL_SLIP_RE.findall(normalized)
    if len(matches) < 3:
        return False
    # Require at least one strong POS token to avoid false positives.
    strong_tokens = {"aid", "tvr", "tsi", "resp", "ref", "period"}
    if not any(token in matches for token in strong_tokens):
        return False
    return True


def has_invoice_signature(text: str | None) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if _INVOICE_STRONG_RE.search(normalized):
        return True
    if _INVOICE_SUPPORT_RE.search(normalized) and "invoice" in normalized:
        return True
    return False


def detect_deterministic_doc_type(text: str | None) -> Tuple[Optional[str], Optional[str]]:
    normalized = _normalize_text(text)
    if not normalized:
        return None, None

    if has_terminal_slip_signature(normalized) and not has_receipt_evidence(normalized):
        return "other", "terminal_slip_signature"

    if has_invoice_signature(normalized):
        return "invoice", "invoice_signature"

    return None, None
