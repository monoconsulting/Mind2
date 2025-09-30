"""API endpoints for AI processing of receipts and documents."""
import logging
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from flask import Blueprint, request, jsonify

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
    AccountingProposal,
)
from ..services.ai_service import AIService
from ..services.db.connection import db_cursor, get_connection
from .middleware import auth_required

logger = logging.getLogger(__name__)

bp = Blueprint('ai_processing', __name__, url_prefix='/ai')


@bp.route('/classify/document', methods=['POST'])
@auth_required
def classify_document():
    """
    AI1 - Document Type Classification
    Analyzes OCR text/image to determine document type.
    """
    try:
        data = request.get_json()
        req = DocumentClassificationRequest(**data)

        ai_service = AIService()
        result = ai_service.classify_document(req)

        _persist_document_classification(
            file_id=req.file_id,
            document_type=result.document_type,
            confidence=result.confidence,
        )

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
@auth_required
def classify_expense():
    """
    AI2 - Expense Type Classification
    Determines if expense is personal or corporate.
    """
    try:
        data = request.get_json()
        req = ExpenseClassificationRequest(**data)

        ai_service = AIService()
        result = ai_service.classify_expense(req)

        _persist_expense_classification(
            file_id=req.file_id,
            expense_type=result.expense_type,
            confidence=result.confidence,
        )

        response = ExpenseClassificationResponse(
            file_id=req.file_id,
            expense_type=result.expense_type,
            confidence=result.confidence,
            card_identifier=result.card_identifier,
            reasoning=result.reasoning,
        )

        return jsonify(response.dict()), 200

    except Exception as e:
        logger.error(f"Error in expense classification: {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route('/extract', methods=['POST'])
@auth_required
def extract_data():
    """
    AI3 - Data Extraction
    Extracts structured data from receipt/invoice to database.
    """
    try:
        data = request.get_json()
        req = DataExtractionRequest(**data)

        ai_service = AIService()
        result = ai_service.extract_data(req)

        _persist_extraction_result(req.file_id, result)

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
@auth_required
def classify_accounting():
    """
    AI4 - Accounting Classification
    Classifies and assigns accounts according to BAS-2025.
    """
    try:
        data = request.get_json()
        req = AccountingClassificationRequest(**data)

        # Get BAS-2025 chart of accounts from database
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT sub_account, sub_account_description
                FROM chart_of_accounts
                WHERE sub_account IS NOT NULL AND sub_account <> ''
                """
            )
            chart_of_accounts = cursor.fetchall()

        # Call AI service for accounting classification
        ai_service = AIService()
        result = ai_service.classify_accounting(req, chart_of_accounts)

        _persist_accounting_proposals(
            file_id=req.file_id,
            proposals=result.proposals,
            confidence=result.confidence,
        )

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
@auth_required
def match_credit_card():
    """
    AI5 - Credit Card Invoice Matching
    Matches receipts with credit card invoice line items.
    """
    try:
        data = request.get_json()
        req = CreditCardMatchRequest(**data)

        purchase_date = req.purchase_date.date() if isinstance(req.purchase_date, datetime) else req.purchase_date

        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT i.id, i.merchant_name, i.amount_sek
                FROM creditcard_invoice_items AS i
                LEFT JOIN creditcard_receipt_matches AS m ON m.invoice_item_id = i.id
                WHERE i.purchase_date = %s
                  AND m.invoice_item_id IS NULL
                  AND (%s IS NULL OR i.amount_sek IS NULL OR ABS(i.amount_sek - %s) <= 5)
                ORDER BY ABS(IFNULL(i.amount_sek, %s) - %s)
                LIMIT 25
                """,
                (purchase_date, req.amount, req.amount, req.amount, req.amount),
            )
            potential_matches = cursor.fetchall()

        # Call AI service for intelligent matching
        ai_service = AIService()
        result = ai_service.match_credit_card(req, potential_matches)

        if result.matched and result.credit_card_invoice_item_id:
            _persist_credit_card_match(
                req.file_id,
                result.credit_card_invoice_item_id,
                req.amount,
                result.confidence,
            )

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


def _persist_document_classification(file_id: str, document_type: str, confidence: float) -> None:
    """Persist AI1 results and advance unified file status."""

    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE unified_files
                SET file_type = %s,
                    ai_status = %s,
                    ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (document_type, "ai1_completed", confidence, file_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def _persist_expense_classification(file_id: str, expense_type: str, confidence: float) -> None:
    """Persist AI2 results and advance unified file status."""

    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE unified_files
                SET expense_type = %s,
                    ai_status = %s,
                    ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (expense_type, "ai2_completed", confidence, file_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def _persist_extraction_result(file_id: str, result: DataExtractionResponse) -> None:
    """Persist the extraction response into unified_files, companies and receipt_items."""

    unified = result.unified_file
    company = result.company

    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            company_id: Optional[int] = None
            orgnr = (company.orgnr or "").strip() or None
            name = (company.name or "").strip() or None

            if orgnr:
                cursor.execute("SELECT id FROM companies WHERE orgnr = %s", (orgnr,))
                existing = cursor.fetchone()
                if existing:
                    company_id = existing[0]
                    cursor.execute(
                        """
                        UPDATE companies
                        SET name = COALESCE(%s, name),
                            address = COALESCE(%s, address),
                            address2 = COALESCE(%s, address2),
                            zip = COALESCE(%s, zip),
                            city = COALESCE(%s, city),
                            country = COALESCE(%s, country),
                            phone = COALESCE(%s, phone),
                            www = COALESCE(%s, www),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (
                            name,
                            company.address,
                            company.address2,
                            company.zip,
                            company.city,
                            company.country,
                            company.phone,
                            company.www,
                            company_id,
                        ),
                    )
                elif name:
                    cursor.execute(
                        """
                        INSERT INTO companies (name, orgnr, address, address2, zip, city, country, phone, www)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            name,
                            orgnr,
                            company.address,
                            company.address2,
                            company.zip,
                            company.city,
                            company.country,
                            company.phone,
                            company.www,
                        ),
                    )
                    company_id = cursor.lastrowid
            elif name:
                logger.info("Company orgnr missing for %s – skipping company insert", file_id)

            payment_type = unified.payment_type or "cash"
            expense_type = unified.expense_type or "personal"
            currency = (unified.currency or "SEK").upper()
            exchange_rate = unified.exchange_rate or Decimal("1")
            gross_amount_sek = unified.gross_amount_sek
            net_amount_sek = unified.net_amount_sek
            if gross_amount_sek is None:
                gross_amount_sek = unified.gross_amount_original if currency == "SEK" else Decimal("0")
            if net_amount_sek is None:
                net_amount_sek = unified.net_amount_original if currency == "SEK" else Decimal("0")

            updates = {
                "orgnr": unified.orgnr,
                "payment_type": payment_type,
                "purchase_datetime": unified.purchase_datetime,
                "expense_type": expense_type,
                "gross_amount_original": unified.gross_amount_original,
                "net_amount_original": unified.net_amount_original,
                "exchange_rate": exchange_rate,
                "currency": currency,
                "gross_amount_sek": gross_amount_sek,
                "net_amount_sek": net_amount_sek,
                "receipt_number": unified.receipt_number or "",
                "other_data": unified.other_data or "{}",
                "ocr_raw": unified.ocr_raw or "",
                "ai_status": "ai3_completed",
            }

            if company_id is not None:
                updates["company_id"] = company_id

            set_parts: List[str] = []
            params: List[Any] = []
            for column, value in updates.items():
                set_parts.append(f"{column} = %s")
                params.append(value)
            set_parts.append("ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s)")
            params.append(result.confidence)
            set_parts.append("updated_at = NOW()")
            params.append(file_id)

            cursor.execute(
                "UPDATE unified_files SET " + ", ".join(set_parts) + " WHERE id = %s",
                tuple(params),
            )

            cursor.execute("DELETE FROM receipt_items WHERE main_id = %s", (file_id,))
            for item in result.receipt_items:
                cursor.execute(
                    """
                    INSERT INTO receipt_items (
                        main_id, article_id, name, number,
                        item_price_ex_vat, item_price_inc_vat,
                        item_total_price_ex_vat, item_total_price_inc_vat,
                        currency, vat, vat_percentage
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        file_id,
                        item.article_id,
                        item.name,
                        item.number,
                        item.item_price_ex_vat,
                        item.item_price_inc_vat,
                        item.item_total_price_ex_vat,
                        item.item_total_price_inc_vat,
                        item.currency,
                        item.vat,
                        item.vat_percentage,
                    ),
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def _persist_credit_card_match(
    file_id: str,
    invoice_item_id: int,
    matched_amount: Optional[Decimal],
    confidence: float,
) -> None:
    """Persist the credit card match relation and update unified_files."""

    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO creditcard_receipt_matches (receipt_id, invoice_item_id, matched_amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE matched_amount = VALUES(matched_amount), matched_at = NOW()
                """,
                (file_id, invoice_item_id, matched_amount),
            )
            cursor.execute(
                """
                UPDATE unified_files
                SET credit_card_match = 1,
                    ai_status = %s,
                    ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s),
                    updated_at = NOW()
                WHERE id = %s
                """,
                ("ai5_completed", confidence, file_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def _persist_accounting_proposals(
    file_id: str,
    proposals: List[AccountingProposal],
    confidence: float,
) -> None:
    """Persist AI4 proposals atomically and advance status."""

    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM ai_accounting_proposals WHERE receipt_id = %s",
                (file_id,),
            )
            for proposal in proposals:
                cursor.execute(
                    """
                    INSERT INTO ai_accounting_proposals (
                        receipt_id, account_code, debit, credit, vat_rate, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        proposal.receipt_id,
                        proposal.account_code,
                        proposal.debit,
                        proposal.credit,
                        proposal.vat_rate,
                        proposal.notes,
                    ),
                )

            cursor.execute(
                """
                UPDATE unified_files
                SET ai_status = %s,
                    ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s),
                    updated_at = NOW()
                WHERE id = %s
                """,
                ("ai4_completed", confidence, file_id),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


@bp.route('/process/batch', methods=['POST'])
@auth_required
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
                with db_cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT ocr_raw, file_type, expense_type
                        FROM unified_files WHERE id = %s
                        """,
                        (file_id,),
                    )
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
                        with db_cursor() as cursor:
                            cursor.execute(
                                """
                                SELECT gross_amount_sek, net_amount_sek,
                                       (gross_amount_sek - net_amount_sek) AS vat_amount,
                                       c.name AS vendor_name
                                FROM unified_files uf
                                LEFT JOIN companies c ON uf.company_id = c.id
                                WHERE uf.id = %s
                                """,
                                (file_id,),
                            )
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
                        with db_cursor() as cursor:
                            cursor.execute(
                                """
                                SELECT purchase_datetime, gross_amount_sek, c.name
                                FROM unified_files uf
                                LEFT JOIN companies c ON uf.company_id = c.id
                                WHERE uf.id = %s
                                """,
                                (file_id,),
                            )
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
@auth_required
def get_ai_status(file_id: str):
    """Get AI processing status for a specific file."""
    try:
        with db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, ai_status, ai_confidence, file_type, expense_type,
                       credit_card_match, updated_at
                FROM unified_files
                WHERE id = %s
                """,
                (file_id,),
            )

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
            cursor.execute(
                """
                SELECT COUNT(*) FROM ai_accounting_proposals WHERE receipt_id = %s
                """,
                (file_id,),
            )
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

    _persist_document_classification(
        file_id=req.file_id,
        document_type=result.document_type,
        confidence=result.confidence,
    )

    return result



def classify_expense_internal(req: ExpenseClassificationRequest):
    """Internal function for expense classification."""
    ai_service = AIService()
    result = ai_service.classify_expense(req)

    _persist_expense_classification(
        file_id=req.file_id,
        expense_type=result.expense_type,
        confidence=result.confidence,
    )

    return result


def extract_data_internal(req: DataExtractionRequest):
    """Internal function for data extraction."""
    ai_service = AIService()
    result = ai_service.extract_data(req)
    _persist_extraction_result(req.file_id, result)
    return result


def classify_accounting_internal(req: AccountingClassificationRequest):
    """Internal function for accounting classification."""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT sub_account, sub_account_description
            FROM chart_of_accounts
            WHERE sub_account IS NOT NULL AND sub_account <> ''
            """
        )
        chart_of_accounts = cursor.fetchall()

    ai_service = AIService()
    result = ai_service.classify_accounting(req, chart_of_accounts)
    _persist_accounting_proposals(
        file_id=req.file_id,
        proposals=result.proposals,
        confidence=result.confidence,
    )
    return result


def match_credit_card_internal(req: CreditCardMatchRequest):
    """Internal function for credit card matching."""
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT i.id, i.merchant_name, i.amount_sek
            FROM creditcard_invoice_items AS i
            LEFT JOIN creditcard_receipt_matches AS m ON m.invoice_item_id = i.id
            WHERE i.purchase_date = %s
              AND m.invoice_item_id IS NULL
              AND (%s IS NULL OR i.amount_sek IS NULL OR ABS(i.amount_sek - %s) <= 5)
            ORDER BY ABS(IFNULL(i.amount_sek, %s) - %s)
            LIMIT 25
            """,
            (
                req.purchase_date.date() if isinstance(req.purchase_date, datetime) else req.purchase_date,
                req.amount,
                req.amount,
                req.amount,
                req.amount,
            ),
        )
        potential_matches = cursor.fetchall()

    ai_service = AIService()
    result = ai_service.match_credit_card(req, potential_matches)

    if result.matched and result.credit_card_invoice_item_id:
        _persist_credit_card_match(
            req.file_id,
            result.credit_card_invoice_item_id,
            req.amount,
            result.confidence,
        )

    return result
