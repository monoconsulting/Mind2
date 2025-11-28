"""Pydantic models for AI processing of receipts and documents."""
from datetime import datetime, date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, List, Literal

from pydantic import BaseModel, Field, condecimal, validator


Decimal18_2 = condecimal(max_digits=18, decimal_places=2)
Decimal12_6 = condecimal(max_digits=12, decimal_places=6)

_DECIMAL_TWO_PLACES = Decimal("0.01")
_DECIMAL_SIX_PLACES = Decimal("0.000001")


def _empty_to_none(value: Optional[str]) -> Optional[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _normalize_decimal(value, *, quantum: Decimal) -> Optional[Decimal]:
    if value in (None, "", "null"):
        return None
    try:
        dec_value = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid decimal value: {value!r}") from exc
    try:
        return dec_value.quantize(quantum, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError(f"Decimal quantization failed for value {value!r}") from exc


class UnifiedFileBase(BaseModel):
    """Base model mirroring the unified_files table."""

    file_type: Literal["receipt", "invoice", "other", "Manual Review"]
    orgnr: Optional[str] = Field(None, max_length=32, description="Company Organization Number")
    payment_type: Optional[Literal["cash", "card", "swish"]] = Field(
        None, description='Cash vs corporate card purchase classification'
    )
    purchase_datetime: Optional[datetime] = None
    expense_type: Optional[Literal["personal", "corporate"]] = None
    gross_amount_original: Optional[Decimal18_2] = None
    net_amount_original: Optional[Decimal18_2] = None
    exchange_rate: Optional[Decimal12_6] = None
    currency: Optional[str] = Field(None, max_length=222)
    gross_amount_sek: Optional[Decimal18_2] = None
    net_amount_sek: Optional[Decimal18_2] = None
    ai_status: Optional[str] = Field(None, max_length=32)
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    mime_type: Optional[str] = Field(None, max_length=222)
    ocr_raw: Optional[str] = None
    company_id: Optional[int] = Field(None, description="Reference to companies.id")
    receipt_number: Optional[str] = Field(None, max_length=255)
    file_creation_timestamp: Optional[datetime] = None
    submitted_by: Optional[str] = Field(None, max_length=64)
    original_file_id: Optional[str] = Field(None, max_length=36)
    original_file_name: Optional[str] = Field(None, max_length=222)
    original_file_size: Optional[int] = None
    file_suffix: Optional[str] = Field(None, max_length=32)
    file_category: Optional[int] = None
    original_filename: Optional[str] = Field(None, max_length=255)
    approved_by: Optional[int] = None
    other_data: Optional[str] = Field(None, description="Additional data from receipt")
    credit_card_match: bool = False
    credit_card_number: Optional[str] = Field(None, max_length=44)
    credit_card_last_4_digits: Optional[int] = None
    credit_card_brand_full: Optional[str] = Field(None, max_length=32)
    credit_card_brand_short: Optional[str] = Field(None, max_length=16)
    credit_card_payment_variant: Optional[str] = Field(None, max_length=64)
    credit_card_type: Optional[str] = Field(None, max_length=64)
    credit_card_token: Optional[str] = Field(None, max_length=64)
    credit_card_entering_mode: Optional[str] = Field(None, max_length=32)

    @validator(
        "orgnr",
        "payment_type",
        "receipt_number",
        "mime_type",
        "other_data",
        "credit_card_number",
        "credit_card_brand_full",
        "credit_card_brand_short",
        "credit_card_payment_variant",
        "credit_card_type",
        "credit_card_token",
        "credit_card_entering_mode",
        pre=True,
    )
    def _strip_optional(cls, value):
        return _empty_to_none(value)

    @validator("currency", pre=True)
    def _normalize_currency(cls, value):
        value = _empty_to_none(value)
        return value.upper() if isinstance(value, str) else value

    @validator(
        "gross_amount_original",
        "net_amount_original",
        "gross_amount_sek",
        "net_amount_sek",
        pre=True,
    )
    def _normalize_amounts(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_TWO_PLACES)

    @validator("exchange_rate", pre=True)
    def _normalize_exchange_rate(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_SIX_PLACES)

    @validator("credit_card_last_4_digits", pre=True)
    def _normalize_last4(cls, value):
        if value in (None, "", False):
            return None
        try:
            digits = int(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError("credit_card_last_4_digits must be numeric") from exc
        if digits < 0:
            raise ValueError("credit_card_last_4_digits must be non-negative")
        return digits


class UnifiedFileAIStatus(BaseModel):
    """AI processing status for unified files."""
    id: str
    ai_status: Optional[Literal["pending", "processing", "completed", "failed", "manual_review"]] = None
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class ReceiptItem(BaseModel):
    """Model for individual receipt items."""
    id: Optional[int] = Field(None, description="Database ID (auto-generated)")
    main_id: str = Field(description="Reference to unified_files.id")
    article_id: str = Field(default="", max_length=222, description="Article/SKU ID (optional)")
    name: str = Field(description="Item name/description")
    number: int = Field(default=1, gt=0, description="Quantity of items")
    item_price_ex_vat: Optional[Decimal18_2] = None
    item_price_inc_vat: Optional[Decimal18_2] = None
    item_total_price_ex_vat: Optional[Decimal18_2] = None
    item_total_price_inc_vat: Optional[Decimal18_2] = None
    currency: str = Field(default="SEK", max_length=11)
    vat: Optional[Decimal18_2] = None
    vat_percentage: Optional[Decimal12_6] = None

    @validator("name")
    def _require_name(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("name is required for receipt item")
        return str(value).strip()

    @validator("main_id")
    def _require_main_id(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("main_id is required for receipt item")
        return str(value)

    @validator("article_id", pre=True)
    def _default_article(cls, value: Optional[str]) -> str:
        if value is None:
            return ""
        return str(value)

    @validator("number", pre=True)
    def _normalize_number(cls, value) -> int:
        if value in (None, "", False):
            return 1
        try:
            number = int(round(float(value)))
        except (TypeError, ValueError) as exc:
            raise ValueError("number must be numeric") from exc
        if number <= 0:
            raise ValueError("number must be greater than zero")
        return number

    @validator(
        "item_price_ex_vat",
        "item_price_inc_vat",
        "item_total_price_ex_vat",
        "item_total_price_inc_vat",
        "vat",
        pre=True,
    )
    def _normalize_two_decimal_fields(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_TWO_PLACES)

    @validator("vat_percentage", pre=True)
    def _normalize_vat_percentage(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_SIX_PLACES)

    @validator("currency", pre=True)
    def _normalize_currency(cls, value):
        value = _empty_to_none(value)
        return (value.upper() if isinstance(value, str) else value) or "SEK"


class Company(BaseModel):
    """Model for company information."""

    name: str = Field(max_length=234)
    orgnr: str = Field(max_length=22, description="Organization number")
    address: Optional[str] = Field(None, max_length=222)
    address2: Optional[str] = Field(None, max_length=222)
    zip: Optional[str] = Field(None, max_length=123)
    city: Optional[str] = Field(None, max_length=234)
    country: Optional[str] = Field(None, max_length=234)
    phone: Optional[str] = Field(None, max_length=234)
    www: Optional[str] = Field(None, max_length=234)


class CreditCardInvoiceMain(BaseModel):
    """Model for credit card invoice main records."""
    invoice_date: datetime
    invoice_number: str = Field(max_length=64)
    card_number_masked: str = Field(max_length=20)
    cardholder_name: str = Field(max_length=200)
    total_amount_sek: Decimal18_2
    payment_due_date: datetime
    invoice_period_start: datetime
    invoice_period_end: datetime


class CreditCardInvoiceItem(BaseModel):
    """Model for credit card invoice line items."""
    main_id: int = Field(description="FK to credit_card_invoices_main.id")
    line_no: int = Field(gt=0)
    transaction_id: Optional[str] = Field(None, max_length=64)
    purchase_date: datetime
    posting_date: Optional[datetime] = None
    merchant_name: str = Field(max_length=200)
    merchant_city: Optional[str] = Field(None, max_length=100)
    merchant_country: Optional[str] = Field(None, max_length=2, description="ISO country code")
    mcc: Optional[str] = Field(None, max_length=4, description="Merchant Category Code")
    description: Optional[str] = None
    currency_original: str = Field(max_length=3, description="ISO currency code")
    amount_original: Decimal18_2
    exchange_rate: Optional[Decimal12_6] = None
    amount_sek: Decimal18_2
    vat_rate: Optional[Decimal18_2] = None
    vat_amount: Optional[Decimal18_2] = None
    net_amount: Optional[Decimal18_2] = None
    gross_amount: Decimal18_2
    cost_center_override: Optional[str] = Field(None, max_length=100)
    project_code: Optional[str] = Field(None, max_length=100)


class CreditCardInvoiceHeader(BaseModel):
    """Structured header information extracted from a credit card invoice."""

    invoice_number: Optional[str] = Field(None, max_length=100)
    invoice_number_long: Optional[str] = Field(None, max_length=150)
    invoice_print_time: Optional[datetime] = None
    invoice_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    due_date: Optional[date] = None
    payment_due: Optional[date] = None
    card_type: Optional[str] = Field(None, max_length=50)
    card_name: Optional[str] = Field(None, max_length=100)
    card_number_masked: Optional[str] = Field(None, max_length=32)
    card_holder: Optional[str] = Field(None, max_length=100)
    customer_name: Optional[str] = Field(None, max_length=150)
    customer_number: Optional[str] = Field(None, max_length=50)
    cost_center: Optional[str] = Field(None, max_length=100)
    co: Optional[str] = Field(None, max_length=150)
    billing_address: Optional[List[str]] = None
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_org_no: Optional[str] = Field(None, max_length=50)
    bank_vat_no: Optional[str] = Field(None, max_length=50)
    bank_fi_no: Optional[str] = Field(None, max_length=50)
    plusgiro: Optional[str] = Field(None, max_length=30)
    bankgiro: Optional[str] = Field(None, max_length=30)
    iban: Optional[str] = Field(None, max_length=34)
    bic: Optional[str] = Field(None, max_length=11)
    ocr: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=3)
    invoice_total: Optional[Decimal18_2] = None
    card_total: Optional[Decimal18_2] = None
    amount_to_pay: Optional[Decimal18_2] = None
    reported_vat: Optional[Decimal18_2] = None
    vat_25: Optional[Decimal18_2] = None
    vat_12: Optional[Decimal18_2] = None
    vat_6: Optional[Decimal18_2] = None
    vat_0: Optional[Decimal18_2] = None
    next_invoice: Optional[date] = None
    notes: Optional[List[str]] = None

    @validator("currency", pre=True)
    def _normalize_currency(cls, value):
        value = _empty_to_none(value)
        return value.upper() if isinstance(value, str) else value

    @validator("billing_address", pre=True)
    def _clean_billing_address(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            cleaned = [str(v).strip() for v in value if str(v).strip()]
            return cleaned or None
        cleaned = str(value).strip()
        return [cleaned] if cleaned else None

    @validator(
        "invoice_total",
        "card_total",
        "amount_to_pay",
        "reported_vat",
        "vat_25",
        "vat_12",
        "vat_6",
        "vat_0",
        pre=True,
    )
    def _normalize_header_amounts(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_TWO_PLACES)


class CreditCardInvoiceLine(BaseModel):
    """Structured line item extracted from a credit card invoice."""

    line_no: int = Field(gt=0)
    transaction_id: Optional[str] = Field(None, max_length=64)
    purchase_date: Optional[date] = None
    posting_date: Optional[date] = None
    merchant_name: Optional[str] = Field(None, max_length=200)
    merchant_city: Optional[str] = Field(None, max_length=100)
    merchant_country: Optional[str] = Field(None, max_length=2)
    mcc: Optional[str] = Field(None, max_length=4)
    description: Optional[str] = None
    currency_original: Optional[str] = Field(None, max_length=3)
    amount_original: Optional[Decimal18_2] = None
    exchange_rate: Optional[Decimal12_6] = None
    amount_sek: Optional[Decimal18_2] = None
    vat_rate: Optional[Decimal18_2] = None
    vat_amount: Optional[Decimal18_2] = None
    net_amount: Optional[Decimal18_2] = None
    gross_amount: Optional[Decimal18_2] = None
    cost_center_override: Optional[str] = Field(None, max_length=100)
    project_code: Optional[str] = Field(None, max_length=100)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_text: Optional[str] = None

    @validator(
        "merchant_name",
        "merchant_city",
        "merchant_country",
        "description",
        "source_text",
        pre=True,
    )
    def _strip_text_fields(cls, value):
        return _empty_to_none(value)

    @validator("currency_original", pre=True)
    def _normalize_currency(cls, value):
        value = _empty_to_none(value)
        return value.upper() if isinstance(value, str) else value

    @validator(
        "amount_original",
        "amount_sek",
        "vat_rate",
        "vat_amount",
        "net_amount",
        "gross_amount",
        pre=True,
    )
    def _normalize_line_amounts(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_TWO_PLACES)

    @validator("exchange_rate", pre=True)
    def _normalize_line_exchange_rate(cls, value):
        return _normalize_decimal(value, quantum=_DECIMAL_SIX_PLACES)


class CreditCardInvoiceExtractionRequest(BaseModel):
    """Request payload for AI6 credit card invoice parsing."""

    invoice_id: str
    ocr_text: str
    page_ids: List[str] = Field(default_factory=list)


class CreditCardInvoiceExtractionResponse(BaseModel):
    """Response payload for AI6 credit card invoice parsing."""

    invoice_id: str
    header: CreditCardInvoiceHeader
    lines: List[CreditCardInvoiceLine]
    overall_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


# AI Processing Request/Response Models

class DocumentClassificationRequest(BaseModel):
    """Request for AI1 - Document Type Classification."""
    file_id: str
    ocr_text: Optional[str] = None
    image_path: Optional[str] = None


class DocumentClassificationResponse(BaseModel):
    """Response for AI1 - Document Type Classification."""
    file_id: str
    document_type: Literal["receipt", "invoice", "fc_invoice", "other", "Manual Review"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None

    @validator("document_type", pre=True)
    def _normalize_document_type(cls, value: str) -> str:
        if value is None:
            raise ValueError("document_type is required")
        text = str(value).strip()
        lowered = text.lower()
        if lowered in {"manual review", "manual_review"}:
            return "Manual Review"
        if lowered in {"receipt", "invoice", "fc_invoice", "other"}:
            return "fc_invoice" if lowered == "fc_invoice" else lowered
        raise ValueError(f"Unsupported document_type '{value}'")


class ExpenseClassificationRequest(BaseModel):
    """Request for AI2 - Expense Type Classification."""
    file_id: str
    ocr_text: Optional[str] = None
    document_type: str


class ExpenseClassificationResponse(BaseModel):
    """Response for AI2 - Expense Type Classification."""
    file_id: str
    expense_type: Literal["personal", "corporate"]
    confidence: float = Field(ge=0.0, le=1.0)
    card_identifier: Optional[str] = None
    reasoning: Optional[str] = None

    @validator("expense_type", pre=True)
    def _normalize_expense_type(cls, value: str) -> str:
        if value is None:
            raise ValueError("expense_type is required")
        lowered = str(value).strip().lower()
        if lowered in {"personal", "corporate"}:
            return lowered
        raise ValueError(f"Unsupported expense_type '{value}'")


class DataExtractionRequest(BaseModel):
    """Request for AI3 - Data Extraction."""
    file_id: str
    ocr_text: str
    document_type: str
    expense_type: str


class DataExtractionResponse(BaseModel):
    """Response for AI3 - Data Extraction."""
    file_id: str
    unified_file: UnifiedFileBase
    receipt_items: List[ReceiptItem]
    company: Company
    confidence: float = Field(ge=0.0, le=1.0)


class AccountingProposal(BaseModel):
    """Model for AI generated accounting proposals."""

    receipt_id: str
    account_code: str = Field(max_length=32, description="Account from chart_of_accounts")
    debit: Decimal18_2 = Field(default=Decimal("0.00"))
    credit: Decimal18_2 = Field(default=Decimal("0.00"))
    vat_rate: Optional[Decimal18_2] = None
    notes: Optional[str] = Field(None, max_length=255)
    item_id: Optional[int] = Field(None, description="Reference to receipt_items.id")

    @validator("account_code")
    def _strip_account_code(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("account_code is required")
        return str(value).strip()


class AccountingClassificationRequest(BaseModel):
    """Request for AI4 - Accounting Classification."""
    file_id: str
    document_type: str
    expense_type: str
    gross_amount: Decimal
    net_amount: Decimal
    vat_amount: Decimal
    vendor_name: str
    receipt_items: List[ReceiptItem]


class AccountingClassificationResponse(BaseModel):
    """Response for AI4 - Accounting Classification."""
    file_id: str
    proposals: List[AccountingProposal]
    confidence: float = Field(ge=0.0, le=1.0)
    based_on_bas2025: bool = True


class CreditCardMatchRequest(BaseModel):
    """Request for AI5 - Credit Card Matching."""
    file_id: str
    purchase_date: datetime
    amount: Decimal
    invoice_id: Optional[str] = None
    merchant_name: Optional[str] = None


class CreditCardMatchResponse(BaseModel):
    """Response for AI5 - Credit Card Matching."""
    file_id: str
    matched: bool
    credit_card_invoice_item_id: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)
    match_details: Optional[dict] = None


# Batch processing models

class BatchProcessingRequest(BaseModel):
    """Request for batch AI processing of multiple files."""
    file_ids: List[str]
    processing_steps: List[Literal["AI1", "AI2", "AI3", "AI4", "AI5", "AI7"]]
    stop_on_error: bool = False


class BatchProcessingResponse(BaseModel):
    """Response for batch AI processing."""

    total_files: int
    processed: int
    failed: int
    results: List[dict]

