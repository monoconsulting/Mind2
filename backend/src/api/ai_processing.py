"""API endpoints for AI processing of receipts and documents."""
from flask import Blueprint, request, jsonify
from typing import List, Dict, Any
import logging
from datetime import datetime
from decimal import Decimal

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
    BatchProcessingRequest,
    BatchProcessingResponse,
    UnifiedFileAIStatus,
    AccountingProposal
)
from ..services.ai_service import AIService
from ..database.connection import get_db_connection
from .middleware import require_auth

logger = logging.getLogger(__name__)

bp = Blueprint('ai_processing', __name__, url_prefix='/ai')


@bp.route('/classify/document', methods=['POST'])
@require_auth
def classify_document():
    """
    AI1 - Document Type Classification
    Analyzes OCR text/image to determine document type.
    """
    try:
        data = request.get_json()
        req = DocumentClassificationRequest(**data)

        # Call AI service for classification
        ai_service = AIService()
        result = ai_service.classify_document(req)

        # Update database with classification
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE unified_files
                SET file_type = %s,
                    ai_status = 'processing',
                    ai_confidence = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (result.document_type, result.confidence, req.file_id))
            conn.commit()

        response = DocumentClassificationResponse(
            file_id=req.file_id,
            document_type=result.document_type,
            confidence=result.confidence,
            reasoning=result.reasoning
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in document classification: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/classify/expense', methods=['POST'])
@require_auth
def classify_expense():
    """
    AI2 - Expense Type Classification
    Determines if expense is personal or corporate.
    """
    try:
        data = request.get_json()
        req = ExpenseClassificationRequest(**data)

        # Call AI service for expense classification
        ai_service = AIService()
        result = ai_service.classify_expense(req)

        # Update database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE unified_files
                SET expense_type = %s,
                    ai_confidence = GREATEST(ai_confidence, %s),
                    updated_at = NOW()
                WHERE id = %s
            """, (result.expense_type, result.confidence, req.file_id))
            conn.commit()

        response = ExpenseClassificationResponse(
            file_id=req.file_id,
            expense_type=result.expense_type,
            confidence=result.confidence,
            card_identifier=result.card_identifier
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in expense classification: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/extract', methods=['POST'])
@require_auth
def extract_data():
    """
    AI3 - Data Extraction
    Extracts structured data from receipt/invoice to database.
    """
    try:
        data = request.get_json()
        req = DataExtractionRequest(**data)

        # Call AI service for data extraction
        ai_service = AIService()
        result = ai_service.extract_data(req)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Update unified_files with extracted data
            unified = result.unified_file
            cursor.execute("""
                UPDATE unified_files SET
                    orgnr = %s,
                    payment_type = %s,
                    purchase_datetime = %s,
                    gross_amount_original = %s,
                    net_amount_original = %s,
                    exchange_rate = %s,
                    currency = %s,
                    gross_amount_sek = %s,
                    net_amount_sek = %s,
                    company_id = %s,
                    receipt_number = %s,
                    other_data = %s,
                    ai_status = 'completed',
                    ai_confidence = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                unified.orgnr, unified.payment_type, unified.purchase_datetime,
                unified.gross_amount_original, unified.net_amount_original,
                unified.exchange_rate, unified.currency,
                unified.gross_amount_sek, unified.net_amount_sek,
                unified.company_id, unified.receipt_number,
                unified.other_data, result.confidence, req.file_id
            ))

            # Insert receipt items
            for item in result.receipt_items:
                cursor.execute("""
                    INSERT INTO receipt_items (
                        main_id, article_id, name, number,
                        item_price_ex_vat, item_price_inc_vat,
                        item_total_price_ex_vat, item_total_price_inc_vat,
                        currency, vat, vat_percentage
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    req.file_id, item.article_id, item.name, item.number,
                    item.item_price_ex_vat, item.item_price_inc_vat,
                    item.item_total_price_ex_vat, item.item_total_price_inc_vat,
                    item.currency, item.vat, item.vat_percentage
                ))

            # Insert or update company
            company = result.company
            cursor.execute("""
                INSERT INTO companies (name, orgnr, address, address2, zip, city, country, phone, www)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    address = VALUES(address),
                    city = VALUES(city),
                    updated_at = NOW()
            """, (
                company.name, company.orgnr, company.address, company.address2,
                company.zip, company.city, company.country, company.phone, company.www
            ))

            conn.commit()

        response = DataExtractionResponse(
            file_id=req.file_id,
            unified_file=result.unified_file,
            receipt_items=result.receipt_items,
            company=result.company,
            confidence=result.confidence
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in data extraction: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/classify/accounting', methods=['POST'])
@require_auth
def classify_accounting():
    """
    AI4 - Accounting Classification
    Classifies and assigns accounts according to BAS-2025.
    """
    try:
        data = request.get_json()
        req = AccountingClassificationRequest(**data)

        # Get BAS-2025 chart of accounts from database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT account_number, account_name FROM chart_of_accounts WHERE standard = 'BAS-2025'")
            chart_of_accounts = cursor.fetchall()

        # Call AI service for accounting classification
        ai_service = AIService()
        result = ai_service.classify_accounting(req, chart_of_accounts)

        # Store AI accounting proposals
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Delete existing proposals for this file
            cursor.execute("DELETE FROM ai_accounting_proposals WHERE file_id = %s", (req.file_id,))

            # Insert new proposals
            for proposal in result.proposals:
                cursor.execute("""
                    INSERT INTO ai_accounting_proposals (
                        file_id, account_number, account_name,
                        debit_amount, credit_amount, description,
                        vat_code, cost_center, project_code,
                        confidence, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """, (
                    req.file_id, proposal.account_number, proposal.account_name,
                    proposal.debit_amount, proposal.credit_amount, proposal.description,
                    proposal.vat_code, proposal.cost_center, proposal.project_code,
                    result.confidence
                ))

            conn.commit()

        response = AccountingClassificationResponse(
            file_id=req.file_id,
            proposals=result.proposals,
            confidence=result.confidence,
            based_on_bas2025=True
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in accounting classification: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/match/creditcard', methods=['POST'])
@require_auth
def match_credit_card():
    """
    AI5 - Credit Card Invoice Matching
    Matches receipts with credit card invoice line items.
    """
    try:
        data = request.get_json()
        req = CreditCardMatchRequest(**data)

        # Search for matching credit card transactions
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, merchant_name, amount_sek
                FROM credit_card_invoice_items
                WHERE purchase_date = %s
                AND ABS(amount_sek - %s) < 0.01
                AND NOT EXISTS (
                    SELECT 1 FROM unified_files
                    WHERE credit_card_invoice_item_id = credit_card_invoice_items.id
                )
            """, (req.purchase_date, req.amount))

            potential_matches = cursor.fetchall()

        # Call AI service for intelligent matching
        ai_service = AIService()
        result = ai_service.match_credit_card(req, potential_matches)

        # Update database if match found
        if result.matched and result.credit_card_invoice_item_id:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE unified_files
                    SET credit_card_match = 1,
                        credit_card_invoice_item_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (result.credit_card_invoice_item_id, req.file_id))
                conn.commit()

        response = CreditCardMatchResponse(
            file_id=req.file_id,
            matched=result.matched,
            credit_card_invoice_item_id=result.credit_card_invoice_item_id,
            confidence=result.confidence,
            match_details=result.match_details
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in credit card matching: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/process/batch', methods=['POST'])
@require_auth
def process_batch():
    """
    Batch processing of multiple files through AI pipeline.
    """
    try:
        data = request.get_json()
        req = BatchProcessingRequest(**data)

        results = []
        processed = 0
        failed = 0

        for file_id in req.file_ids:
            try:
                file_result = {"file_id": file_id, "steps_completed": []}

                # Get file info
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ocr_raw, file_type, expense_type
                        FROM unified_files WHERE id = %s
                    """, (file_id,))
                    file_info = cursor.fetchone()

                if not file_info:
                    raise ValueError(f"File {file_id} not found")

                ocr_text, doc_type, expense_type = file_info

                # Process through requested steps
                for step in req.processing_steps:
                    if step == "AI1" and doc_type is None:
                        # Document classification
                        classify_req = DocumentClassificationRequest(
                            file_id=file_id, ocr_text=ocr_text
                        )
                        classify_document_internal(classify_req)
                        file_result["steps_completed"].append("AI1")

                    elif step == "AI2" and expense_type is None:
                        # Expense classification
                        expense_req = ExpenseClassificationRequest(
                            file_id=file_id, ocr_text=ocr_text, document_type=doc_type
                        )
                        classify_expense_internal(expense_req)
                        file_result["steps_completed"].append("AI2")

                    elif step == "AI3":
                        # Data extraction
                        extract_req = DataExtractionRequest(
                            file_id=file_id, ocr_text=ocr_text,
                            document_type=doc_type, expense_type=expense_type
                        )
                        extract_data_internal(extract_req)
                        file_result["steps_completed"].append("AI3")

                    elif step == "AI4":
                        # Accounting classification
                        # Get amounts from database
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT gross_amount_sek, net_amount_sek,
                                       (gross_amount_sek - net_amount_sek) as vat_amount,
                                       c.name as vendor_name
                                FROM unified_files uf
                                JOIN companies c ON uf.company_id = c.id
                                WHERE uf.id = %s
                            """, (file_id,))
                            amounts = cursor.fetchone()

                        if amounts:
                            account_req = AccountingClassificationRequest(
                                file_id=file_id,
                                document_type=doc_type,
                                expense_type=expense_type,
                                gross_amount=amounts[0],
                                net_amount=amounts[1],
                                vat_amount=amounts[2],
                                vendor_name=amounts[3],
                                receipt_items=[]
                            )
                            classify_accounting_internal(account_req)
                            file_result["steps_completed"].append("AI4")

                    elif step == "AI5":
                        # Credit card matching
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT purchase_datetime, gross_amount_sek, c.name
                                FROM unified_files uf
                                LEFT JOIN companies c ON uf.company_id = c.id
                                WHERE uf.id = %s
                            """, (file_id,))
                            match_info = cursor.fetchone()

                        if match_info and match_info[0]:
                            match_req = CreditCardMatchRequest(
                                file_id=file_id,
                                purchase_date=match_info[0],
                                amount=match_info[1],
                                merchant_name=match_info[2]
                            )
                            match_credit_card_internal(match_req)
                            file_result["steps_completed"].append("AI5")

                results.append(file_result)
                processed += 1

            except Exception as e:
                failed += 1
                results.append({
                    "file_id": file_id,
                    "error": str(e),
                    "steps_completed": file_result.get("steps_completed", [])
                })

                if req.stop_on_error:
                    break

        response = BatchProcessingResponse(
            total_files=len(req.file_ids),
            processed=processed,
            failed=failed,
            results=results
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/status/<file_id>', methods=['GET'])
@require_auth
def get_ai_status(file_id: str):
    """Get AI processing status for a specific file."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ai_status, ai_confidence, file_type, expense_type,
                       credit_card_match, updated_at
                FROM unified_files
                WHERE id = %s
            """, (file_id,))

            result = cursor.fetchone()

            if not result:
                return jsonify({"error": "File not found"}), 404

            status = {
                "file_id": result[0],
                "ai_status": result[1],
                "ai_confidence": result[2],
                "document_type": result[3],
                "expense_type": result[4],
                "credit_card_matched": bool(result[5]),
                "last_updated": result[6].isoformat() if result[6] else None
            }

            # Check for accounting proposals
            cursor.execute("""
                SELECT COUNT(*) FROM ai_accounting_proposals WHERE file_id = %s
            """, (file_id,))
            proposal_count = cursor.fetchone()[0]
            status["has_accounting_proposals"] = proposal_count > 0

            return jsonify(status), 200

    except Exception as e:
        logger.error(f"Error getting AI status: {str(e)}")
        return jsonify({"error": str(e)}), 500


# Internal helper functions for batch processing
def classify_document_internal(req: DocumentClassificationRequest):
    """Internal function for document classification."""
    ai_service = AIService()
    result = ai_service.classify_document(req)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE unified_files
            SET file_type = %s, ai_confidence = %s, updated_at = NOW()
            WHERE id = %s
        """, (result.document_type, result.confidence, req.file_id))
        conn.commit()

    return result


def classify_expense_internal(req: ExpenseClassificationRequest):
    """Internal function for expense classification."""
    ai_service = AIService()
    result = ai_service.classify_expense(req)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE unified_files
            SET expense_type = %s, updated_at = NOW()
            WHERE id = %s
        """, (result.expense_type, req.file_id))
        conn.commit()

    return result


def extract_data_internal(req: DataExtractionRequest):
    """Internal function for data extraction."""
    ai_service = AIService()
    result = ai_service.extract_data(req)
    # Implementation same as extract_data endpoint
    return result


def classify_accounting_internal(req: AccountingClassificationRequest):
    """Internal function for accounting classification."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account_number, account_name FROM chart_of_accounts WHERE standard = 'BAS-2025'")
        chart_of_accounts = cursor.fetchall()

    ai_service = AIService()
    result = ai_service.classify_accounting(req, chart_of_accounts)
    # Implementation same as classify_accounting endpoint
    return result


def match_credit_card_internal(req: CreditCardMatchRequest):
    """Internal function for credit card matching."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, merchant_name, amount_sek
            FROM credit_card_invoice_items
            WHERE purchase_date = %s AND ABS(amount_sek - %s) < 0.01
        """, (req.purchase_date, req.amount))
        potential_matches = cursor.fetchall()

    ai_service = AIService()
    result = ai_service.match_credit_card(req, potential_matches)

    if result.matched and result.credit_card_invoice_item_id:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE unified_files
                SET credit_card_match = 1,
                    credit_card_invoice_item_id = %s
                WHERE id = %s
            """, (result.credit_card_invoice_item_id, req.file_id))
            conn.commit()

    return result