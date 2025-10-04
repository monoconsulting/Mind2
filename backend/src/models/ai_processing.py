"""Pydantic models for AI processing of receipts and documents."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Literal

from pydantic import BaseModel, Field


class UnifiedFileBase(BaseModel):
    """Base model mirroring the unified_files table."""

    file_type: Literal["receipt", "invoice", "other", "Manual Review"]
    orgnr: Optional[str] = Field(None, max_length=32, description="Company Organization Number")
    payment_type: Optional[Literal["cash", "card"]] = Field(
        None, description='Cash vs corporate card purchase classification'
    )
    purchase_datetime: Optional[datetime] = None
    expense_type: Optional[Literal["personal", "corporate"]] = None
    gross_amount_original: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    net_amount_original: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    exchange_rate: Optional[Decimal] = Field(None, max_digits=18, decimal_places=6)
    currency: Optional[str] = Field(None, max_length=222)
    gross_amount_sek: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    net_amount_sek: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
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


class UnifiedFileAIStatus(BaseModel):
    """AI processing status for unified files."""
    id: str
    ai_status: Optional[Literal["pending", "processing", "completed", "failed", "manual_review"]] = None
    ai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class ReceiptItem(BaseModel):
    """Model for individual receipt items."""
    id: Optional[int] = Field(None, description="Database ID (auto-generated)")
    main_id: str = Field(description="Reference to unified_files.id")
    article_id: str = Field(max_length=222)
    name: str = Field(max_length=222)
    number: int = Field(gt=0, description="Quantity of items")
    item_price_ex_vat: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    item_price_inc_vat: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    item_total_price_ex_vat: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    item_total_price_inc_vat: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    currency: str = Field(default="SEK", max_length=11)
    vat: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    vat_percentage: Optional[Decimal] = Field(None, max_digits=18, decimal_places=6)


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
    total_amount_sek: Decimal = Field(max_digits=18, decimal_places=2)
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
    amount_original: Decimal = Field(max_digits=18, decimal_places=2)
    exchange_rate: Optional[Decimal] = Field(None, max_digits=18, decimal_places=6)
    amount_sek: Decimal = Field(max_digits=18, decimal_places=2)
    vat_rate: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    vat_amount: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    net_amount: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    gross_amount: Decimal = Field(max_digits=18, decimal_places=2)
    cost_center_override: Optional[str] = Field(None, max_length=100)
    project_code: Optional[str] = Field(None, max_length=100)


# AI Processing Request/Response Models

class DocumentClassificationRequest(BaseModel):
    """Request for AI1 - Document Type Classification."""
    file_id: str
    ocr_text: Optional[str] = None
    image_path: Optional[str] = None


class DocumentClassificationResponse(BaseModel):
    """Response for AI1 - Document Type Classification."""
    file_id: str
    document_type: Literal["receipt", "invoice", "other", "Manual Review"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None


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
    debit: Decimal = Field(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    credit: Decimal = Field(max_digits=18, decimal_places=2, default=Decimal("0.00"))
    vat_rate: Optional[Decimal] = Field(None, max_digits=18, decimal_places=2)
    notes: Optional[str] = Field(None, max_length=255)
    item_id: Optional[int] = Field(None, description="Reference to receipt_items.id")


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
    processing_steps: List[Literal["AI1", "AI2", "AI3", "AI4", "AI5"]]
    stop_on_error: bool = False


class BatchProcessingResponse(BaseModel):
    """Response for batch AI processing."""

    total_files: int
    processed: int
    failed: int
    results: List[dict]