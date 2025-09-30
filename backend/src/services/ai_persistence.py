"""Persistence helpers for AI pipeline stages.

These helpers centralise the SQL required to persist AI stage output so
that both the Flask API layer and Celery workers can share consistent
behaviour.  The functions purposely avoid any business logic so callers
can orchestrate transactions and status updates as needed.
"""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Sequence, Tuple

from services.db.connection import db_cursor, get_connection
from models.ai_processing import (
    AccountingClassificationResponse,
    DataExtractionResponse,
    DocumentClassificationResponse,
    ExpenseClassificationResponse,
)


def persist_document_classification(
    file_id: str, result: DocumentClassificationResponse
) -> None:
    """Store AI1 classification data on ``unified_files``."""

    with db_cursor() as cursor:
        cursor.execute(
            """
            UPDATE unified_files
            SET file_type = %s,
                ai_confidence = %s,
                updated_at = NOW()
            WHERE id = %s
            """,
            (result.document_type, result.confidence, file_id),
        )


def persist_expense_classification(
    file_id: str, result: ExpenseClassificationResponse
) -> None:
    """Persist AI2 expense classification values."""

    with db_cursor() as cursor:
        cursor.execute(
            """
            UPDATE unified_files
            SET expense_type = %s,
                ai_confidence = GREATEST(IFNULL(ai_confidence, 0), %s),
                updated_at = NOW()
            WHERE id = %s
            """,
            (result.expense_type, result.confidence, file_id),
        )


def persist_extraction_result(
    file_id: str, result: DataExtractionResponse
) -> None:
    """Persist AI3 extraction payload across dependent tables."""

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
                        INSERT INTO companies (
                            name, orgnr, address, address2, zip, city, country, phone, www
                        )
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
                # We still persist the unified file even if company orgnr is missing.
                pass

            updates = {
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
                "other_data": unified.other_data,
                "ocr_raw": unified.ocr_raw or "",
                "ai_confidence": result.confidence,
            }

            set_parts: List[str] = []
            params: List[Any] = []
            for column, value in updates.items():
                set_parts.append(f"{column} = %s")
                params.append(value)
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


def persist_accounting_proposals(
    response: AccountingClassificationResponse,
) -> None:
    """Replace AI4 proposals for a receipt with new values."""

    with closing(get_connection()) as conn:
        conn.start_transaction()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM ai_accounting_proposals WHERE receipt_id = %s",
                (response.file_id,),
            )
            for proposal in response.proposals:
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
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def persist_credit_card_match(
    file_id: str, invoice_item_id: int, matched_amount: Optional[Decimal]
) -> None:
    """Persist the AI5 credit card match relation."""

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
                "UPDATE unified_files SET credit_card_match = 1, updated_at = NOW() WHERE id = %s",
                (file_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def fetch_pipeline_context(file_id: str) -> Optional[Tuple[Any, ...]]:
    """Fetch the minimal unified file context needed for AI stages."""

    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT ocr_raw, file_type, expense_type, purchase_datetime,
                   gross_amount_sek, net_amount_sek, company_id
            FROM unified_files
            WHERE id = %s
            """,
            (file_id,),
        )
        return cursor.fetchone()


def fetch_company_name(company_id: Optional[int]) -> Optional[str]:
    if not company_id:
        return None
    with db_cursor() as cursor:
        cursor.execute(
            "SELECT name FROM companies WHERE id = %s",
            (company_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def fetch_chart_of_accounts() -> List[Tuple[str, str]]:
    with db_cursor() as cursor:
        cursor.execute(
            """
            SELECT sub_account, sub_account_description
            FROM chart_of_accounts
            WHERE sub_account IS NOT NULL AND sub_account <> ''
            """,
        )
        return cursor.fetchall() or []


def fetch_credit_card_candidates(
    purchase_date: datetime, amount: Optional[Decimal]
) -> Sequence[Tuple[Any, ...]]:
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
                purchase_date.date(),
                amount,
                amount,
                amount,
                amount,
            ),
        )
        return cursor.fetchall() or []


__all__ = [
    "fetch_chart_of_accounts",
    "fetch_company_name",
    "fetch_credit_card_candidates",
    "fetch_pipeline_context",
    "persist_accounting_proposals",
    "persist_credit_card_match",
    "persist_document_classification",
    "persist_expense_classification",
    "persist_extraction_result",
]

