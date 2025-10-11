from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


class ReceiptStatus(str, Enum):
    PROCESSING = "Processing"
    PASSED = "Passed"
    FAILED = "Failed"
    MANUAL_REVIEW = "Manual Review"
    COMPLETED = "Completed"


@dataclass
class LineItem:
    id: Optional[str]
    receipt_id: Optional[str]
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal
    total: Decimal


@dataclass
class Receipt:
    id: Optional[str]
    submitted_by: Optional[str]
    submitted_at: datetime
    pages: List[str] = field(default_factory=list)  # file references
    tags: List[str] = field(default_factory=list)
    location_opt_in: bool = False

    merchant_name: Optional[str] = None
    orgnr: Optional[str] = None
    purchase_datetime: Optional[datetime] = None

    gross_amount: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    vat_breakdown: Dict[int, Decimal] = field(default_factory=dict)  # {25: amt, 12: amt, ...}

    company_card_flag: bool = False
    status: ReceiptStatus = ReceiptStatus.PROCESSING
    confidence_summary: Optional[float] = None


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationMessage:
    message: str
    severity: Severity
    field_ref: Optional[str] = None


@dataclass
class ValidationReport:
    id: Optional[str]
    receipt_id: str
    status: ReceiptStatus
    messages: List[ValidationMessage] = field(default_factory=list)


@dataclass
class AccountingEntry:
    id: Optional[str]
    receipt_id: str
    item_id: Optional[int] = None  # FK to receipt_items.id
    account_code: str = ""
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    vat_rate: Optional[Decimal] = None
    notes: Optional[str] = None
