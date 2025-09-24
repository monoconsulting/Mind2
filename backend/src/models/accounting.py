from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class AccountingRule:
    id: Optional[str]
    name: str
    condition_type: str  # merchant_contains|lineitem_contains|tag
    condition_value: str
    account_code: str
    vat_account_code: Optional[str] = None
