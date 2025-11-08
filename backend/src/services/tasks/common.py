from __future__ import annotations

import logging

from celery import chain, chord, group

try:
    from services.db.connection import db_cursor
except Exception:  # pragma: no cover
    db_cursor = None  # type: ignore

try:
    from services.db.files import (
        DuplicateFileError,
        insert_unified_file,
        set_ai_status,
        update_other_data,
    )
except ImportError:  # pragma: no cover
    insert_unified_file = lambda **kwargs: None  # type: ignore
    update_other_data = lambda **kwargs: None  # type: ignore

    class DuplicateFileError(Exception):
        """Fallback exception when database layer is unavailable."""

    def set_ai_status(file_id: str, status: str) -> bool:  # type: ignore
        _ = (file_id, status)
        return False

from services.queue_manager import get_celery
from services.storage import FileStorage
from services.pdf_conversion import pdf_to_png_pages
from observability.events import log_event
from observability.metrics import record_invoice_decision, track_task
from services.ocr import run_ocr
from services.enrichment import enrich_receipt, provider_from_env
from services.validation import validate_receipt
from services.accounting import propose_accounting_entries
from services.box_enrichment import run_box_enrichment
from services.invoice_status import (
    InvoiceDocumentStatus,
    InvoiceLineMatchStatus,
    InvoiceProcessingStatus,
    invoice_documents_supports_updated_at,
    transition_document_status,
    transition_line_status,
    transition_line_status_and_link,
    transition_processing_status,
)
from services.invoice_parser import parse_credit_card_statement
from models.accounting import AccountingRule
from models.ai_processing import (
    AccountingClassificationRequest,
    CreditCardInvoiceExtractionRequest,
    CreditCardInvoiceExtractionResponse,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
    DataExtractionRequest,
    DocumentClassificationRequest,
    ExpenseClassificationRequest,
    ReceiptItem,
)
from models.receipts import AccountingEntry, Receipt, ReceiptStatus
from api.ai_processing import (
    _persist_credit_card_match,
    classify_accounting_internal,
    classify_document_internal,
    classify_expense_internal,
    extract_data_internal,
)

logger = logging.getLogger(__name__)
celery_app = get_celery()

__all__ = [
    "db_cursor",
    "DuplicateFileError",
    "FileStorage",
    "InvoiceDocumentStatus",
    "InvoiceLineMatchStatus",
    "InvoiceProcessingStatus",
    "AccountingRule",
    "AccountingEntry",
    "AccountingClassificationRequest",
    "CreditCardInvoiceExtractionRequest",
    "CreditCardInvoiceExtractionResponse",
    "CreditCardInvoiceHeader",
    "CreditCardInvoiceLine",
    "DataExtractionRequest",
    "DocumentClassificationRequest",
    "ExpenseClassificationRequest",
    "Receipt",
    "ReceiptItem",
    "ReceiptStatus",
    "_persist_credit_card_match",
    "celery_app",
    "chain",
    "chord",
    "enrich_receipt",
    "extract_data_internal",
    "insert_unified_file",
    "log_event",
    "parse_credit_card_statement",
    "pdf_to_png_pages",
    "propose_accounting_entries",
    "provider_from_env",
    "record_invoice_decision",
    "run_box_enrichment",
    "run_ocr",
    "set_ai_status",
    "track_task",
    "transition_document_status",
    "transition_line_status",
    "transition_line_status_and_link",
    "transition_processing_status",
    "update_other_data",
    "validate_receipt",
    "group",
    "invoice_documents_supports_updated_at",
]
