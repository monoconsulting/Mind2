from __future__ import annotations

import re

_SERVICE_RECEIPT_TOKENS = [
    r"\baleris\b",
    r"\bsjukv[aä]rd\b",
    r"\bortopedi\b",
    r"\bregion\b",
    r"\bbes[oö]ksdatum\b",
    r"\bfrikort\b",
    r"\bpatientavgift\b",
]
_SERVICE_RECEIPT_REQUIRED = [
    r"\bbes[oö]ksdatum\b",
    r"\bfrikort\b",
    r"\bpatientavgift\b",
    r"\bregion\b",
]


def is_service_receipt_candidate(text: str) -> bool:
    if not text:
        return False
    hits = sum(1 for token in _SERVICE_RECEIPT_TOKENS if re.search(token, text))
    if hits < 2:
        return False
    if not any(re.search(token, text) for token in _SERVICE_RECEIPT_REQUIRED):
        return False
    return True
