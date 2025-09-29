"""AI Service for processing receipts and documents."""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
import json

from ..models.ai_processing import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    ExpenseClassificationRequest,
    ExpenseClassificationResponse,
    DataExtractionRequest,
    DataExtractionResponse,
    AccountingClassificationRequest,
    AccountingClassificationResponse,
    CreditCardMatchRequest,
    CreditCardMatchResponse,
    UnifiedFileBase,
    ReceiptItem,
    Company,
    AccountingProposal
)

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-based document processing."""

    def __init__(self):
        """Initialize AI Service with configured model."""
        # TODO: Initialize with actual AI model from config
        self.model_name = "gpt-4"  # Placeholder
        self.temperature = 0.3  # Low temperature for consistency

    def classify_document(self, request: DocumentClassificationRequest) -> DocumentClassificationResponse:
        """
        AI1 - Classify document type (receipt, invoice, or other).

        Args:
            request: Document classification request with OCR text or image

        Returns:
            Classification response with document type and confidence
        """
        try:
            # TODO: Implement actual AI classification
            # This is a placeholder implementation
            logger.info(f"Classifying document {request.file_id}")

            # Analyze OCR text for document patterns
            if request.ocr_text:
                text_lower = request.ocr_text.lower()

                # Simple heuristic for demo
                if any(word in text_lower for word in ["kvitto", "receipt", "köp", "summa", "moms"]):
                    doc_type = "receipt"
                    confidence = 0.85
                elif any(word in text_lower for word in ["faktura", "invoice", "förfallodatum", "ocr"]):
                    doc_type = "invoice"
                    confidence = 0.80
                else:
                    doc_type = "other"
                    confidence = 0.60

                # Check if manual review is needed
                if confidence < 0.70 and doc_type == "other":
                    doc_type = "Manual Review"

            else:
                doc_type = "Manual Review"
                confidence = 0.0

            return DocumentClassificationResponse(
                file_id=request.file_id,
                document_type=doc_type,
                confidence=confidence,
                reasoning="Document classified based on text analysis"
            )

        except Exception as e:
            logger.error(f"Error in document classification: {str(e)}")
            raise

    def classify_expense(self, request: ExpenseClassificationRequest) -> ExpenseClassificationResponse:
        """
        AI2 - Classify expense type (personal or corporate).

        Args:
            request: Expense classification request

        Returns:
            Classification response with expense type
        """
        try:
            logger.info(f"Classifying expense for document {request.file_id}")

            # TODO: Implement actual AI classification
            # Check for corporate card indicators
            text_lower = request.ocr_text.lower() if request.ocr_text else ""

            card_patterns = ["first card", "mastercard", "företagskort", "corporate", "business card"]
            card_identifier = None

            for pattern in card_patterns:
                if pattern in text_lower:
                    expense_type = "corporate"
                    card_identifier = pattern
                    confidence = 0.90
                    break
            else:
                expense_type = "personal"
                confidence = 0.85

            return ExpenseClassificationResponse(
                file_id=request.file_id,
                expense_type=expense_type,
                confidence=confidence,
                card_identifier=card_identifier
            )

        except Exception as e:
            logger.error(f"Error in expense classification: {str(e)}")
            raise

    def extract_data(self, request: DataExtractionRequest) -> DataExtractionResponse:
        """
        AI3 - Extract structured data from document.

        Args:
            request: Data extraction request

        Returns:
            Extracted data including vendor, amounts, and line items
        """
        try:
            logger.info(f"Extracting data from document {request.file_id}")

            # TODO: Implement actual AI data extraction
            # This is a placeholder with sample data structure

            # Extract basic receipt information
            unified_file = UnifiedFileBase(
                file_type=request.document_type,
                orgnr="556677-8899",  # Would be extracted from OCR
                payment_type="card",
                purchase_datetime=datetime.now(),
                expense_type=request.expense_type,
                gross_amount_original=Decimal("125.00"),
                net_amount_original=Decimal("100.00"),
                exchange_rate=Decimal("1.00"),
                currency="SEK",
                gross_amount_sek=Decimal("125"),
                net_amount_sek=Decimal("100"),
                company_id=1,  # Would be looked up or created
                receipt_number="REC-2025-001",
                other_data=json.dumps({"extracted_by": "AI", "version": "1.0"})
            )

            # Extract line items
            receipt_items = [
                ReceiptItem(
                    main_id=request.file_id,
                    article_id="ART-001",
                    name="Product 1",
                    number=1,
                    item_price_ex_vat=Decimal("100.00"),
                    item_price_inc_vat=Decimal("125.00"),
                    item_total_price_ex_vat=Decimal("100.00"),
                    item_total_price_inc_vat=Decimal("125.00"),
                    currency="SEK",
                    vat=Decimal("25.00"),
                    vat_percentage=Decimal("0.25")
                )
            ]

            # Extract company information
            company = Company(
                name="Example Store AB",
                orgnr="556677-8899",
                address="Storgatan 1",
                zip="11122",
                city="Stockholm",
                country="Sweden"
            )

            return DataExtractionResponse(
                file_id=request.file_id,
                unified_file=unified_file,
                receipt_items=receipt_items,
                company=company,
                confidence=0.85
            )

        except Exception as e:
            logger.error(f"Error in data extraction: {str(e)}")
            raise

    def classify_accounting(self, request: AccountingClassificationRequest,
                           chart_of_accounts: List[Tuple]) -> AccountingClassificationResponse:
        """
        AI4 - Classify accounting entries according to BAS-2025.

        Args:
            request: Accounting classification request
            chart_of_accounts: List of available accounts from BAS-2025

        Returns:
            Accounting proposals with account assignments
        """
        try:
            logger.info(f"Classifying accounting for document {request.file_id}")

            # TODO: Implement actual AI accounting classification
            # This would analyze the vendor and items to suggest appropriate accounts

            proposals = []

            # Main purchase entry
            if request.expense_type == "personal":
                # Personal expense - typically goes to expense account
                proposals.append(AccountingProposal(
                    file_id=request.file_id,
                    account_number="5410",  # Förbrukningsinventarier
                    account_name="Förbrukningsinventarier",
                    debit_amount=request.net_amount,
                    credit_amount=None,
                    description="Inköp - " + request.vendor_name
                ))
            else:
                # Corporate card expense
                proposals.append(AccountingProposal(
                    file_id=request.file_id,
                    account_number="4010",  # Inköp av varor
                    account_name="Inköp av varor",
                    debit_amount=request.net_amount,
                    credit_amount=None,
                    description="Företagskortsinköp - " + request.vendor_name
                ))

            # VAT entry
            if request.vat_amount and request.vat_amount > 0:
                proposals.append(AccountingProposal(
                    file_id=request.file_id,
                    account_number="2640",  # Ingående moms
                    account_name="Ingående moms",
                    debit_amount=request.vat_amount,
                    credit_amount=None,
                    description="Moms på inköp",
                    vat_code="V25"  # 25% VAT
                ))

            # Balancing entry (credit side)
            total_amount = request.gross_amount
            if request.expense_type == "personal":
                # Personal expense - credit to employee liability
                proposals.append(AccountingProposal(
                    file_id=request.file_id,
                    account_number="2893",  # Skuld till anställda
                    account_name="Skuld till anställda",
                    debit_amount=None,
                    credit_amount=total_amount,
                    description="Utlägg att återbetala"
                ))
            else:
                # Corporate card - credit to card liability
                proposals.append(AccountingProposal(
                    file_id=request.file_id,
                    account_number="2499",  # Övriga kortfristiga skulder
                    account_name="Övriga kortfristiga skulder",
                    debit_amount=None,
                    credit_amount=total_amount,
                    description="Företagskortsskuld"
                ))

            return AccountingClassificationResponse(
                file_id=request.file_id,
                proposals=proposals,
                confidence=0.80,
                based_on_bas2025=True
            )

        except Exception as e:
            logger.error(f"Error in accounting classification: {str(e)}")
            raise

    def match_credit_card(self, request: CreditCardMatchRequest,
                         potential_matches: List[Tuple]) -> CreditCardMatchResponse:
        """
        AI5 - Match receipts with credit card transactions.

        Args:
            request: Credit card match request
            potential_matches: List of potential matching transactions

        Returns:
            Match response with matched transaction ID if found
        """
        try:
            logger.info(f"Matching credit card for document {request.file_id}")

            # TODO: Implement actual AI matching logic
            # This would use fuzzy matching on merchant names and amounts

            matched = False
            matched_id = None
            confidence = 0.0
            match_details = {}

            if potential_matches:
                # Simple matching: take first match with same date and amount
                for match in potential_matches:
                    transaction_id, merchant_name, amount = match

                    # Check if merchant names are similar
                    if request.merchant_name:
                        # TODO: Implement fuzzy string matching
                        name_similarity = 0.8  # Placeholder
                    else:
                        name_similarity = 0.5

                    # Amount matches exactly (already filtered in query)
                    amount_match = 1.0

                    # Calculate overall confidence
                    match_confidence = (name_similarity + amount_match) / 2

                    if match_confidence > 0.7:
                        matched = True
                        matched_id = transaction_id
                        confidence = match_confidence
                        match_details = {
                            "merchant_name_match": name_similarity,
                            "amount_match": amount_match,
                            "transaction_id": transaction_id
                        }
                        break

            return CreditCardMatchResponse(
                file_id=request.file_id,
                matched=matched,
                credit_card_invoice_item_id=matched_id,
                confidence=confidence,
                match_details=match_details
            )

        except Exception as e:
            logger.error(f"Error in credit card matching: {str(e)}")
            raise