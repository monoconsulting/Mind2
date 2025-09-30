"""Shared persistence helpers for AI pipeline stages."""
from __future__ import annotations

import logging
from contextlib import closing
from decimal import Decimal
from typing import Iterable, Optional

from ..models.ai_processing import AccountingProposal, DataExtractionResponse
from .db.connection import get_connection

logger = logging.getLogger(__name__)


def persist_extraction_result(file_id: str, result: DataExtractionResponse) -> None:
    """Persist AI3 extraction output atomically."""

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
                "ai_status": "completed",
                "ai_confidence": result.confidence,
            }

            set_parts = []
            params = []
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
    file_id: str, proposals: Iterable[AccountingProposal]
) -> None:
    """Replace accounting proposals for a receipt."""

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
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


def persist_credit_card_match(
    file_id: str, invoice_item_id: int, matched_amount: Optional[Decimal]
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
                "UPDATE unified_files SET credit_card_match = 1, updated_at = NOW() WHERE id = %s",
                (file_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
