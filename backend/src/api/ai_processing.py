"""API endpoints for AI processing of receipts and documents."""
from __future__ import annotations

import logging
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from models.ai_processing import (
    AccountingClassificationRequest,
    AccountingClassificationResponse,
    AccountingProposal,
    BatchProcessingRequest,
    BatchProcessingResponse,
    Company,
    CreditCardMatchRequest,
    CreditCardMatchResponse,
    DataExtractionRequest,
    DataExtractionResponse,
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    ExpenseClassificationRequest,
    ExpenseClassificationResponse,
    ReceiptItem,
)
from services.ai_service import AIService
from services.db.connection import db_cursor, get_connection
from api.middleware import auth_required

logger = logging.getLogger(__name__)

bp = Blueprint("ai_processing", __name__, url_prefix="/ai")

_AI_STAGE_STATUS = {
    "AI1": "ai1_completed",
    "AI2": "ai2_completed",
    "AI3": "ai3_completed",
    "AI4": "ai4_completed",
    "AI5_TRUE": "ai5_completed",
    "AI5_FALSE": "ai5_no_match",
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _stage_status(stage: str, matched: Optional[bool] = None) -> str:
    if stage == "AI5":
        key = f"AI5_{str(bool(matched)).upper()}"
        return _AI_STAGE_STATUS[key]
    return _AI_STAGE_STATUS[stage]


def _set_ai_stage(
    cursor,
    file_id: str,
    stage: str,
    confidence: Optional[float] = None,
    matched: Optional[bool] = None,
) -> None:
    """Set AI stage status. Note: rowcount may be 0 if values don't change, which is OK."""
    status_value = _stage_status(stage, matched)
    if confidence is None:
        cursor.execute(
            "UPDATE unified_files SET ai_status = %s, updated_at = NOW() WHERE id = %s",
            (status_value, file_id),
        )
    else:
        cursor.execute(
            """
            UPDATE unified_files
               SET ai_status = %s,
                   ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s),
                   updated_at = NOW()
             WHERE id = %s
            """,
            (status_value, confidence, file_id),
        )
    # Note: We don't check rowcount here because MySQL returns 0 if values don't change
    # The file existence is verified by the calling function


def _ensure_company(cursor, company: Company) -> Optional[int]:
    """
    Ensure company exists in database and return its ID.

    Strategy:
    1. Search by orgnr if provided (most reliable identifier)
    2. Fall back to name search if no orgnr match
    3. Update existing company with new data
    4. Create new company if not found

    Returns:
        Company ID if company was found/created, None if insufficient data
    """
    name = (company.name or "").strip() or None
    orgnr = (company.orgnr or "").strip() or None

    if not name and not orgnr:
        logger.warning("Cannot ensure company: both name and orgnr are empty")
        return None

    company_id: Optional[int] = None

    # Strategy 1: Try to find by orgnr (most reliable)
    if orgnr:
        cursor.execute("SELECT id FROM companies WHERE orgnr = %s", (orgnr,))
        row = cursor.fetchone()
        if row:
            company_id = int(row[0])
            logger.debug(f"Found company by orgnr={orgnr}: company_id={company_id}")

    # Strategy 2: Fall back to name search if orgnr didn't match
    if company_id is None and name:
        cursor.execute(
            "SELECT id FROM companies WHERE name = %s ORDER BY id LIMIT 1",
            (name,),
        )
        row = cursor.fetchone()
        if row:
            company_id = int(row[0])
            logger.debug(f"Found company by name='{name}': company_id={company_id}")

    # Update existing company with new information
    if company_id is not None:
        cursor.execute(
            """
            UPDATE companies
               SET name = COALESCE(%s, name),
                   orgnr = COALESCE(%s, orgnr),
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
                orgnr,
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
        logger.info(f"Updated company {company_id} with new data")
        return company_id

    # Create new company if not found
    if not name:
        logger.warning("Cannot create company: name is required but missing")
        return None

    if not orgnr:
        logger.warning(f"Cannot create company '{name}': orgnr is required but missing")
        return None

    try:
        cursor.execute(
            """
            INSERT INTO companies
                (name, orgnr, address, address2, zip, city, country, phone, www)
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
        company_id = int(cursor.lastrowid)
        logger.info(f"Created new company: {company_id} (name='{name}', orgnr={orgnr})")
        return company_id
    except Exception as exc:
        logger.error(f"Failed to create company (name='{name}', orgnr={orgnr}): {exc}")
        raise


def _replace_receipt_items(cursor, file_id: str, items: Iterable[ReceiptItem]) -> List[int]:
    """Replace receipt items and return the list of generated IDs."""
    items_list = list(items)  # Convert to list to count and iterate
    logger.info(
        "AI3 _replace_receipt_items: Deleting old items and inserting %d new items for file_id=%s",
        len(items_list), file_id
    )

    cursor.execute("DELETE FROM receipt_items WHERE main_id = %s", (file_id,))
    deleted_count = cursor.rowcount
    if deleted_count > 0:
        logger.debug("AI3 deleted %d old receipt_items for file_id=%s", deleted_count, file_id)

    inserted_ids: List[int] = []
    for idx, item in enumerate(items_list, 1):
        # Validate main_id before insert
        if item.main_id != file_id:
            logger.error(
                "AI3 receipt_items[%d] has main_id='%s' but expected file_id='%s' - this is a critical data integrity error!",
                idx, item.main_id, file_id
            )
            raise ValueError(f"Receipt item main_id mismatch: {item.main_id} != {file_id}")

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
        # Get the auto-generated ID from the last insert
        item_id = int(cursor.lastrowid)
        inserted_ids.append(item_id)
        logger.debug(
            "AI3 inserted receipt_items[%d] with id=%d: name='%s', qty=%d, article_id='%s', total_inc_vat=%s %s",
            idx, item_id, item.name, item.number, item.article_id or 'N/A',
            item.item_total_price_inc_vat, item.currency
        )

    logger.info(
        "AI3 _replace_receipt_items: Successfully inserted %d items for file_id=%s with IDs: %s",
        len(inserted_ids), file_id, inserted_ids
    )
    return inserted_ids


def _persist_extraction_result(
    file_id: str,
    result: DataExtractionResponse,
    *,
    connection=None,
) -> None:
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor()
    try:
        if owns_connection:
            conn.start_transaction()
        company_id = _ensure_company(cursor, result.company)
        unified = result.unified_file
        updates: Dict[str, Any] = {
            "orgnr": unified.orgnr,
            "payment_type": unified.payment_type,
            "purchase_datetime": unified.purchase_datetime,
            "expense_type": unified.expense_type,
            "gross_amount_original": unified.gross_amount_original,
            "net_amount_original": unified.net_amount_original,
            "exchange_rate": unified.exchange_rate,
            "currency": unified.currency,
            "gross_amount_sek": unified.gross_amount_sek,
            "net_amount_sek": unified.net_amount_sek,
            "company_id": company_id,
            "receipt_number": unified.receipt_number,
            "other_data": unified.other_data or "{}",
            "ocr_raw": unified.ocr_raw or "",
            "credit_card_number": unified.credit_card_number,
            "credit_card_last_4_digits": unified.credit_card_last_4_digits,
            "credit_card_brand_full": unified.credit_card_brand_full,
            "credit_card_brand_short": unified.credit_card_brand_short,
            "credit_card_payment_variant": unified.credit_card_payment_variant,
            "credit_card_type": unified.credit_card_type,
            "credit_card_token": unified.credit_card_token,
            "credit_card_entering_mode": unified.credit_card_entering_mode,
        }
        set_parts: List[str] = []
        params: List[Any] = []
        for column, value in updates.items():
            if value is None:
                continue
            set_parts.append(f"{column} = %s")
            params.append(value)
        set_parts.append("updated_at = NOW()")
        params.append(file_id)
        # Check if file exists first
        cursor.execute("SELECT id FROM unified_files WHERE id = %s", (file_id,))
        if cursor.fetchone() is None:
            raise ValueError(f"File {file_id} not found")
        cursor.execute(
            "UPDATE unified_files SET " + ", ".join(set_parts) + " WHERE id = %s",
            tuple(params),
        )
        inserted_ids = _replace_receipt_items(cursor, file_id, result.receipt_items)
        # Update the receipt_items in the result with their database IDs
        for item, item_id in zip(result.receipt_items, inserted_ids):
            item.id = item_id
        logger.info(
            "AI3 created %d receipt_items for %s with IDs: %s",
            len(inserted_ids),
            file_id,
            inserted_ids
        )
        _set_ai_stage(cursor, file_id, "AI3", result.confidence)
        if owns_connection:
            conn.commit()
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()


def _persist_accounting_proposals(
    file_id: str,
    proposals: Iterable[AccountingProposal],
    confidence: float,
    *,
    connection=None,
) -> None:
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor()
    try:
        if owns_connection:
            conn.start_transaction()
        cursor.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id = %s", (file_id,))
        for proposal in proposals:
            cursor.execute(
                """
                INSERT INTO ai_accounting_proposals (
                    receipt_id, account_code, debit, credit, vat_rate, notes, item_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    proposal.receipt_id,
                    proposal.account_code,
                    proposal.debit,
                    proposal.credit,
                    proposal.vat_rate,
                    proposal.notes,
                    proposal.item_id,
                ),
            )
        _set_ai_stage(cursor, file_id, "AI4", confidence)
        if owns_connection:
            conn.commit()
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()


def _persist_credit_card_match(
    file_id: str,
    invoice_item_id: Optional[int],
    matched_amount: Optional[Decimal],
    confidence: Optional[float],
    matched: bool,
    *,
    connection=None,
) -> None:
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor()
    try:
        if owns_connection:
            conn.start_transaction()
        if invoice_item_id is not None:
            cursor.execute(
                "UPDATE creditcard_invoice_items SET matched = %s, updated_at = NOW() WHERE id = %s",
                (1 if matched else 0, invoice_item_id),
            )
        if matched and invoice_item_id is not None:
            cursor.execute(
                """
                INSERT INTO creditcard_receipt_matches (receipt_id, invoice_item_id, matched_amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE matched_amount = VALUES(matched_amount), matched_at = NOW()
                """,
                (file_id, invoice_item_id, matched_amount),
            )
        elif invoice_item_id is not None:
            cursor.execute(
                "DELETE FROM creditcard_receipt_matches WHERE invoice_item_id = %s",
                (invoice_item_id,),
            )
        cursor.execute(
            "UPDATE unified_files SET credit_card_match = %s, matched = %s, updated_at = NOW() WHERE id = %s",
            (1 if matched else 0, 1 if matched else 0, file_id),
        )
        _set_ai_stage(cursor, file_id, "AI5", confidence, matched=matched)
        if owns_connection:
            conn.commit()
    except Exception:
        if owns_connection:
            conn.rollback()
        raise
    finally:
        cursor.close()
        if owns_connection:
            conn.close()


def _mark_manual_review(file_id: str, reason: Optional[str] = None) -> None:
    try:
        with db_cursor() as cursor:
            cursor.execute(
                "UPDATE unified_files SET ai_status = 'manual_review', updated_at = NOW() WHERE id = %s",
                (file_id,),
            )
    except Exception as exc:  # pragma: no cover - best effort logging only
        logger.warning("Failed to mark %s for manual review: %s", file_id, exc)
    if reason:
        logger.warning("Manual review for %s: %s", file_id, reason)


# ---------------------------------------------------------------------------
# Internal loaders
# ---------------------------------------------------------------------------

def _load_chart_of_accounts() -> List[Tuple[Any, ...]]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT sub_account, sub_account_description
              FROM chart_of_accounts
             WHERE sub_account IS NOT NULL AND sub_account <> ''
            """
        )
        return cursor.fetchall()


def _load_unified_file(file_id: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT ocr_raw, file_type, expense_type FROM unified_files WHERE id = %s",
            (file_id,),
        )
        return cursor.fetchone()


def _load_match_context(file_id: str) -> Optional[Tuple[datetime, Optional[Decimal], Optional[str]]]:
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
        return cursor.fetchone()


def _potential_credit_matches(req: CreditCardMatchRequest) -> List[Tuple[Any, ...]]:
    with db_cursor() as cursor:
        date_value: Optional[Any]
        if isinstance(req.purchase_date, datetime):
            date_value = req.purchase_date.date()
        else:
            date_value = req.purchase_date
        amount_value = req.amount
        amount_for_order = amount_value if amount_value is not None else Decimal("0")
        cursor.execute(
            """
            SELECT il.id,
                   COALESCE(il.merchant_name, il.description) AS candidate_name,
                   il.amount
              FROM invoice_lines AS il
         LEFT JOIN creditcard_receipt_matches AS m ON m.invoice_item_id = il.id
             WHERE (%s IS NULL OR DATE(il.transaction_date) = %s)
               AND (%s IS NULL OR il.amount IS NULL OR ABS(il.amount - %s) <= 5)
               AND (il.match_status IS NULL OR il.match_status IN ('pending','unmatched'))
               AND m.invoice_item_id IS NULL
               AND (%s IS NULL OR il.invoice_id = %s)
          ORDER BY ABS(IFNULL(il.amount, %s) - %s)
             LIMIT 25
            """,
            (
                date_value,
                date_value,
                amount_value,
                amount_value,
                req.invoice_id,
                req.invoice_id,
                amount_for_order,
                amount_for_order,
            ),
        )
        return cursor.fetchall()


# ---------------------------------------------------------------------------
# Internal AI stage executors
# ---------------------------------------------------------------------------

def classify_document_internal(req: DocumentClassificationRequest) -> DocumentClassificationResponse:
    ai_service = AIService()
    result = ai_service.classify_document(req)
    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            # Check if file exists first
            cursor.execute("SELECT id FROM unified_files WHERE id = %s", (req.file_id,))
            if cursor.fetchone() is None:
                raise ValueError(f"File {req.file_id} not found")
            cursor.execute(
                "UPDATE unified_files SET file_type = %s WHERE id = %s",
                (result.document_type, req.file_id),
            )
            _set_ai_stage(cursor, req.file_id, "AI1", result.confidence)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return result


def classify_expense_internal(req: ExpenseClassificationRequest) -> ExpenseClassificationResponse:
    ai_service = AIService()
    result = ai_service.classify_expense(req)
    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            # Check if file exists first
            cursor.execute("SELECT id FROM unified_files WHERE id = %s", (req.file_id,))
            if cursor.fetchone() is None:
                raise ValueError(f"File {req.file_id} not found")
            cursor.execute(
                "UPDATE unified_files SET expense_type = %s WHERE id = %s",
                (result.expense_type, req.file_id),
            )
            _set_ai_stage(cursor, req.file_id, "AI2", result.confidence)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    return result


def extract_data_internal(req: DataExtractionRequest) -> DataExtractionResponse:
    ai_service = AIService()
    result = ai_service.extract_data(req)
    _persist_extraction_result(req.file_id, result)
    return result


def classify_accounting_internal(req: AccountingClassificationRequest) -> AccountingClassificationResponse:
    chart_of_accounts = _load_chart_of_accounts()
    ai_service = AIService()
    result = ai_service.classify_accounting(req, chart_of_accounts)
    _persist_accounting_proposals(req.file_id, result.proposals, result.confidence)
    return result


def match_credit_card_internal(req: CreditCardMatchRequest) -> CreditCardMatchResponse:
    potential_matches = _potential_credit_matches(req)
    ai_service = AIService()
    result = ai_service.match_credit_card(req, potential_matches)
    matched_amount: Optional[Decimal] = None
    if result.match_details and result.match_details.get("matched_amount") is not None:
        matched_amount = Decimal(str(result.match_details["matched_amount"]))
    _persist_credit_card_match(
        req.file_id,
        result.credit_card_invoice_item_id,
        matched_amount,
        result.confidence,
        result.matched,
    )
    return result


# ---------------------------------------------------------------------------
# Flask endpoints
# ---------------------------------------------------------------------------

@bp.route("/classify/document", methods=["POST"])
@auth_required
def classify_document() -> Any:
    try:
        payload = request.get_json(force=True) or {}
        req = DocumentClassificationRequest(**payload)
        result = classify_document_internal(req)
        return jsonify(result.dict()), 200
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Error in document classification")
        _mark_manual_review(payload.get("file_id", ""), str(exc))
        return jsonify({"error": "Document classification failed"}), 500


@bp.route("/classify/expense", methods=["POST"])
@auth_required
def classify_expense() -> Any:
    try:
        payload = request.get_json(force=True) or {}
        req = ExpenseClassificationRequest(**payload)
        result = classify_expense_internal(req)
        return jsonify(result.dict()), 200
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Error in expense classification")
        _mark_manual_review(payload.get("file_id", ""), str(exc))
        return jsonify({"error": "Expense classification failed"}), 500


@bp.route("/extract", methods=["POST"])
@auth_required
def extract_data() -> Any:
    try:
        payload = request.get_json(force=True) or {}
        req = DataExtractionRequest(**payload)
        result = extract_data_internal(req)
        return jsonify(result.dict()), 200
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Error in data extraction")
        _mark_manual_review(payload.get("file_id", ""), str(exc))
        return jsonify({"error": "Data extraction failed"}), 500


@bp.route("/classify/accounting", methods=["POST"])
@auth_required
def classify_accounting() -> Any:
    try:
        payload = request.get_json(force=True) or {}
        req = AccountingClassificationRequest(**payload)
        result = classify_accounting_internal(req)
        return jsonify(result.dict()), 200
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Error in accounting classification")
        _mark_manual_review(payload.get("file_id", ""), str(exc))
        return jsonify({"error": "Accounting classification failed"}), 500


@bp.route("/match/creditcard", methods=["POST"])
@auth_required
def match_credit_card() -> Any:
    try:
        payload = request.get_json(force=True) or {}
        req = CreditCardMatchRequest(**payload)
        result = match_credit_card_internal(req)
        return jsonify(result.dict()), 200
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Error in credit card matching")
        _mark_manual_review(payload.get("file_id", ""), str(exc))
        return jsonify({"error": "Credit card matching failed"}), 500


@bp.route("/process/batch", methods=["POST"])
@auth_required
def process_batch() -> Any:
    try:
        payload = request.get_json(force=True) or {}
        req = BatchProcessingRequest(**payload)
        results: List[Dict[str, Any]] = []
        processed = 0
        failed = 0
        for file_id in req.file_ids:
            file_result: Dict[str, Any] = {"file_id": file_id, "steps_completed": []}
            try:
                for step in req.processing_steps:
                    context = _load_unified_file(file_id)
                    if context is None:
                        raise ValueError(f"File {file_id} not found")
                    ocr_text, document_type, expense_type = context
                    if step == "AI1":
                        classify_document_internal(
                            DocumentClassificationRequest(file_id=file_id, ocr_text=ocr_text)
                        )
                        file_result["steps_completed"].append("AI1")
                    elif step == "AI2":
                        classify_expense_internal(
                            ExpenseClassificationRequest(
                                file_id=file_id,
                                ocr_text=ocr_text,
                                document_type=document_type or "other",
                            )
                        )
                        file_result["steps_completed"].append("AI2")
                    elif step == "AI3":
                        extract_data_internal(
                            DataExtractionRequest(
                                file_id=file_id,
                                ocr_text=ocr_text or "",
                                document_type=document_type or "other",
                                expense_type=expense_type or "personal",
                            )
                        )
                        file_result["steps_completed"].append("AI3")
                    elif step == "AI4":
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
                            # Fetch receipt_items from database with their IDs
                            cursor.execute(
                                """
                                SELECT id, main_id, article_id, name, number,
                                       item_price_ex_vat, item_price_inc_vat,
                                       item_total_price_ex_vat, item_total_price_inc_vat,
                                       currency, vat, vat_percentage
                                  FROM receipt_items
                                 WHERE main_id = %s
                                 ORDER BY id
                                """,
                                (file_id,),
                            )
                            items_rows = cursor.fetchall()

                        receipt_items_for_ai4: List[ReceiptItem] = []
                        for row in items_rows:
                            receipt_items_for_ai4.append(ReceiptItem(
                                id=row[0],
                                main_id=row[1],
                                article_id=row[2] or "",
                                name=row[3],
                                number=row[4],
                                item_price_ex_vat=row[5],
                                item_price_inc_vat=row[6],
                                item_total_price_ex_vat=row[7],
                                item_total_price_inc_vat=row[8],
                                currency=row[9],
                                vat=row[10],
                                vat_percentage=row[11],
                            ))

                        if amounts:
                            logger.info(
                                "AI4 processing %s with %d receipt_items (IDs: %s)",
                                file_id,
                                len(receipt_items_for_ai4),
                                [item.id for item in receipt_items_for_ai4]
                            )
                            classify_accounting_internal(
                                AccountingClassificationRequest(
                                    file_id=file_id,
                                    document_type=document_type or "other",
                                    expense_type=expense_type or "personal",
                                    gross_amount=Decimal(str(amounts[0] or 0)),
                                    net_amount=Decimal(str(amounts[1] or 0)),
                                    vat_amount=Decimal(str(amounts[2] or 0)),
                                    vendor_name=amounts[3] or "",
                                    receipt_items=receipt_items_for_ai4,
                                )
                            )
                            file_result["steps_completed"].append("AI4")
                    elif step == "AI5":
                        match_info = _load_match_context(file_id)
                        if match_info and match_info[0]:
                            match_credit_card_internal(
                                CreditCardMatchRequest(
                                    file_id=file_id,
                                    purchase_date=match_info[0],
                                    amount=match_info[1],
                                    merchant_name=match_info[2],
                                )
                            )
                            file_result["steps_completed"].append("AI5")
                processed += 1
                results.append(file_result)
            except Exception as exc:
                failed += 1
                file_result["error"] = str(exc)
                results.append(file_result)
                if req.stop_on_error:
                    break
        response = BatchProcessingResponse(
            total_files=len(req.file_ids),
            processed=processed,
            failed=failed,
            results=results,
        )
        return jsonify(response.dict()), 200
    except ValidationError as exc:
        return jsonify({"error": exc.errors()}), 400
    except Exception as exc:
        logger.exception("Error in batch processing")
        return jsonify({"error": str(exc)}), 500


@bp.route("/status/<file_id>", methods=["GET"])
@auth_required
def get_ai_status(file_id: str):
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
                "last_updated": result[6].isoformat() if result[6] else None,
            }
            cursor.execute(
                "SELECT COUNT(*) FROM ai_accounting_proposals WHERE receipt_id = %s",
                (file_id,),
            )
            status["has_accounting_proposals"] = cursor.fetchone()[0] > 0
        return jsonify(status), 200
    except Exception as exc:
        logger.error("Error getting AI status: %s", exc)
        return jsonify({"error": str(exc)}), 500
