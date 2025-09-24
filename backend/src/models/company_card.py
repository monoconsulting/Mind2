from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CompanyCardInvoice:
    id: Optional[str]
    period_start: datetime
    period_end: datetime
    uploaded_at: datetime
    status: str


@dataclass
class CompanyCardLine:
    id: Optional[str]
    invoice_id: str
    date: datetime
    amount: float
    merchant_name: str
    matched_receipt_id: Optional[str] = None
    match_score: Optional[float] = None
