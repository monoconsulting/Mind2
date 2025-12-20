"""API endpoints for AI processing of receipts and documents."""
from __future__ import annotations

import json
import logging
import re
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from difflib import SequenceMatcher
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
from services.box_enrichment import run_box_enrichment
from services.db.connection import db_cursor, get_connection
from services.status_constants import InvoiceLineMatchStatus, AiStatus
from api.middleware import auth_required
from observability.events import log_event

logger = logging.getLogger(__name__)

bp = Blueprint("ai_processing", __name__, url_prefix="/ai")

_AI_STAGE_STATUS = {
    "AI1": AiStatus.PROCESSING.value,
    "AI2": AiStatus.PROCESSING.value,
    # AI3 completes data extraction, but the overall document must not be marked completed
    # until the workflow finalizes successfully (finalize_ok/KLAR). See SoT 30_STATUS_MODEL.md.
    "AI3": AiStatus.PROCESSING.value,
    "AI4": AiStatus.PROCESSING.value,
    "AI5_TRUE": AiStatus.PROCESSING.value,
    "AI5_FALSE": AiStatus.PROCESSING.value,
}


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

_VAT_BUCKET_RATES: tuple[int, ...] = (25, 12, 6)


def _decimal_2(value: Any) -> Decimal | None:
    if value in (None, "", False, "null"):
        return None
    try:
        return Decimal(str(value).replace(",", ".")).quantize(Decimal("0.01"))
    except Exception:
        return None


def _parse_vat_rate(value: Any) -> int | None:
    if value in (None, "", False, "null"):
        return None
    try:
        rate = int(round(float(str(value).replace(",", "."))))
    except Exception:
        return None
    return rate if rate in _VAT_BUCKET_RATES else None


def _parse_vat_summary(vat_summary: Any) -> list[dict[str, Any]]:
    if not isinstance(vat_summary, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in vat_summary:
        if not isinstance(raw, dict):
            continue
        rate = _parse_vat_rate(
            raw.get("vat_rate")
            or raw.get("vat_rate_percent")
            or raw.get("vat_percentage")
            or raw.get("vatRate")
            or raw.get("vatRatePercent")
            or raw.get("vatPercentage")
            or raw.get("rate")
        )
        vat_amount = _decimal_2(raw.get("vat_amount") or raw.get("vat") or raw.get("vatAmount"))
        gross_amount = _decimal_2(raw.get("gross_amount") or raw.get("gross") or raw.get("grossAmount"))
        net_amount = _decimal_2(raw.get("net_amount") or raw.get("net") or raw.get("netAmount"))
        rows.append(
            {
                "rate": rate,
                "vat_amount": vat_amount,
                "gross_amount": gross_amount,
                "net_amount": net_amount,
            }
        )
    return rows


def _vat_totals_from_summary(vat_rows: list[dict[str, Any]]) -> dict[int, Decimal]:
    totals: dict[int, Decimal] = {}
    for row in vat_rows:
        rate = row.get("rate")
        vat_amount = row.get("vat_amount")
        if rate in _VAT_BUCKET_RATES and isinstance(vat_amount, Decimal):
            totals[rate] = (totals.get(rate) or Decimal("0.00")) + vat_amount
    for k, v in list(totals.items()):
        totals[k] = v.quantize(Decimal("0.01"))
    return totals


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

    # Do not downgrade a completed/manual_review/failed status back to processing
    try:
        cursor.execute("SELECT ai_status FROM unified_files WHERE id = %s", (file_id,))
        current = cursor.fetchone()
        if current:
            current_status = current[0]
            if current_status in (
                AiStatus.COMPLETED.value,
                AiStatus.MANUAL_REVIEW.value,
                AiStatus.FAILED.value,
            ) and status_value == AiStatus.PROCESSING.value:
                return
    except Exception:
        pass

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


def _ensure_company(cursor, company: Company) -> tuple[int, str, bool]:
    """
    Deterministically resolve (or create) a company based on VAT/ORGNR and name.

    Resolution order:
    1) VAT/ORGNR match (normalized digits)
    2) Name match (exact, starts-with, fuzzy >= 0.85)
    3) Auto-create using provided company fields

    Returns:
        (company_id, match_type, created_flag)
        match_type is one of: vat, name, new
    """

    def _normalize_vat(value: Optional[str]) -> Optional[str]:
        digits = "".join(ch for ch in (value or "") if ch.isdigit())
        return digits or None

    def _normalize_name(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        lowered = value.lower()
        lowered = lowered.replace("†", "a").replace("„", "o").replace("”", "o")
        collapsed = re.sub(r"\s+", " ", lowered).strip()
        return collapsed or None

    name_raw = (company.name or "").strip()
    vat_raw = company.vat or company.orgnr
    vat_norm = _normalize_vat(vat_raw)
    name_norm = _normalize_name(name_raw)

    if not vat_norm and not name_norm:
        raise ValueError("Company resolution failed: both vat/orgnr and name are missing")

    company_id: Optional[int] = None
    match_type: Optional[str] = None

    # 1) VAT/ORGNR match
    if vat_norm:
        cursor.execute(
            "SELECT id, name, orgnr FROM companies "
            "WHERE REPLACE(REPLACE(IFNULL(orgnr, ''), '-', ''), ' ', '') = %s "
            "LIMIT 1",
            (vat_norm,),
        )
        row = cursor.fetchone()
        if row:
            company_id = int(row[0])
            match_type = "vat"

    # 2) Name match (exact, then startswith, then fuzzy)
    if company_id is None and name_norm:
        cursor.execute(
            "SELECT id, name FROM companies WHERE LOWER(TRIM(name)) = %s ORDER BY id LIMIT 1",
            (name_norm,),
        )
        row = cursor.fetchone()
        if row:
            company_id = int(row[0])
            match_type = "name"

    if company_id is None and name_norm:
        cursor.execute(
            "SELECT id, name FROM companies WHERE LOWER(name) LIKE %s ORDER BY LENGTH(name) ASC LIMIT 20",
            (f"{name_norm}%",),
        )
        candidates = cursor.fetchall() or []
        best_match = None
        best_score = 0.0
        for cid, cname in candidates:
            score = SequenceMatcher(None, name_norm, _normalize_name(cname)).ratio()
            if score > best_score:
                best_score = score
                best_match = (cid, cname)
        if best_match and best_score >= 0.85:
            company_id = int(best_match[0])
            match_type = "name"

    # 3) Auto-create
    created = False
    if company_id is None:
        if not name_norm:
            raise ValueError("Company resolution failed: name required for auto-create")
        cursor.execute(
            """
            INSERT INTO companies
                (name, orgnr, address, address2, zip, city, country, phone, www, email, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (
                name_raw or name_norm,
                vat_norm,
                company.address,
                company.address2,
                company.zip,
                company.city,
                company.country,
                company.phone,
                company.www,
                getattr(company, "email", None),
            ),
        )
        company_id = int(cursor.lastrowid)
        match_type = "new"
        created = True

    # Update existing record with any new data (safe merge)
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
               email = COALESCE(%s, email),
               updated_at = NOW()
         WHERE id = %s
        """,
        (
            name_raw or name_norm,
            vat_norm,
            company.address,
            company.address2,
            company.zip,
            company.city,
            company.country,
            company.phone,
            company.www,
            getattr(company, "email", None),
            company_id,
        ),
    )

    return company_id, match_type or "name", created


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

        needs_review_reason: str | None = None
        resolved_company_id: int | None = None
        resolved_match_type: str | None = None
        created = False
        try:
            resolved_company_id, resolved_match_type, created = _ensure_company(cursor, result.company)
        except ValueError as exc:
            # Controlled handling: missing vendor identity must degrade to needs_review, never crash.
            # This error happens when OCR/AI3 did not provide enough vendor identity (vat/orgnr + name).
            if str(exc).startswith("Company resolution failed:"):
                needs_review_reason = "missing_vendor_identity_in_ocr"
                resolved_company_id = None
                resolved_match_type = needs_review_reason
                created = False
            else:
                raise
        unified = result.unified_file
        # Reflect resolved company metadata back on the response model
        result.company_match_type = resolved_match_type
        result.company_create_needed = created

        # Normalise/merge other_data as JSON string and attach match metadata
        other_data_payload: dict[str, Any] = {}
        if unified.other_data:
            try:
                other_data_payload = json.loads(unified.other_data)
            except Exception:
                other_data_payload = {"raw_other_data": unified.other_data}
        other_data_payload["company_match_type"] = resolved_match_type
        other_data_payload["company_create_needed"] = created or bool(result.company_create_needed)
        if needs_review_reason:
            other_data_payload["needs_review_reason"] = needs_review_reason

        # Load current DB values so we can avoid wiping existing non-null fields
        cursor.execute(
            """
            SELECT
              currency, exchange_rate,
              gross_amount_original, net_amount_original,
              gross_amount_sek, net_amount_sek,
              total_vat_25, total_vat_12, total_vat_6,
              gross_amount, net_amount
            FROM unified_files
            WHERE id = %s
            """,
            (file_id,),
        )
        existing_row = cursor.fetchone()
        if existing_row is None:
            raise ValueError(f"File {file_id} not found")
        (
            existing_currency,
            existing_exchange_rate,
            existing_gross_original,
            existing_net_original,
            existing_gross_sek,
            existing_net_sek,
            existing_vat_25,
            existing_vat_12,
            existing_vat_6,
            existing_gross_legacy,
            existing_net_legacy,
        ) = existing_row

        # Deterministic repairs (gross/net/VAT totals + SEK invariant)
        currency = (unified.currency or existing_currency or "SEK").strip().upper() if isinstance((unified.currency or existing_currency or "SEK"), str) else "SEK"
        exchange_rate = unified.exchange_rate if unified.exchange_rate is not None else existing_exchange_rate

        gross_original = unified.gross_amount_original if unified.gross_amount_original is not None else existing_gross_original
        net_original = unified.net_amount_original if unified.net_amount_original is not None else existing_net_original
        gross_sek = unified.gross_amount_sek if unified.gross_amount_sek is not None else existing_gross_sek
        net_sek = unified.net_amount_sek if unified.net_amount_sek is not None else existing_net_sek

        if currency == "SEK":
            exchange_rate = Decimal("1.000000")
            if gross_original is None and isinstance(gross_sek, Decimal):
                gross_original = gross_sek
            if net_original is None and isinstance(net_sek, Decimal):
                net_original = net_sek
            if gross_sek is None and isinstance(gross_original, Decimal):
                gross_sek = gross_original
            if net_sek is None and isinstance(net_original, Decimal):
                net_sek = net_original
        else:
            if exchange_rate in (0, Decimal("0")):
                exchange_rate = None

        vat_rows = _parse_vat_summary(other_data_payload.get("vat_summary"))
        vat_totals = _vat_totals_from_summary(vat_rows)
        vat_rates_detected = sorted({r.get("rate") for r in vat_rows if r.get("rate") in _VAT_BUCKET_RATES})

        # Case A: one-row VAT summary can deterministically complete header totals
        if len(vat_rows) == 1:
            row = vat_rows[0]
            row_vat = row.get("vat_amount")
            row_gross = row.get("gross_amount")
            if isinstance(row_vat, Decimal) and isinstance(row_gross, Decimal):
                if gross_original is None:
                    gross_original = row_gross
                if net_original is None:
                    net_candidate = (row_gross - row_vat).quantize(Decimal("0.01"))
                    if net_candidate >= Decimal("0.00"):
                        net_original = net_candidate

        # VAT buckets: compute from vat_summary, else derive from gross-net if single rate detected
        total_vat_25 = existing_vat_25
        total_vat_12 = existing_vat_12
        total_vat_6 = existing_vat_6

        if total_vat_25 is None and 25 in vat_totals:
            total_vat_25 = vat_totals[25]
        if total_vat_12 is None and 12 in vat_totals:
            total_vat_12 = vat_totals[12]
        if total_vat_6 is None and 6 in vat_totals:
            total_vat_6 = vat_totals[6]

        if (
            total_vat_25 is None
            and total_vat_12 is None
            and total_vat_6 is None
            and isinstance(gross_original, Decimal)
            and isinstance(net_original, Decimal)
        ):
            vat_diff = (gross_original - net_original).quantize(Decimal("0.01"))
            if vat_diff >= Decimal("0.00") and len(vat_rates_detected) == 1:
                rate = int(vat_rates_detected[0])
                if rate == 25:
                    total_vat_25 = vat_diff
                elif rate == 12:
                    total_vat_12 = vat_diff
                elif rate == 6:
                    total_vat_6 = vat_diff

        other_data_json = json.dumps(other_data_payload, ensure_ascii=False)

        updates: Dict[str, Any] = {
            "vat": unified.vat,
            "payment_type": unified.payment_type,
            "purchase_datetime": unified.purchase_datetime,
            "expense_type": unified.expense_type,
            "gross_amount_original": gross_original,
            "net_amount_original": net_original,
            "total_vat_25": total_vat_25,
            "total_vat_12": total_vat_12,
            "total_vat_6": total_vat_6,
            "exchange_rate": exchange_rate,
            "currency": currency,
            "gross_amount": gross_sek if gross_sek is not None else existing_gross_legacy,  # legacy column
            "net_amount": net_sek if net_sek is not None else existing_net_legacy,  # legacy column
            "gross_amount_sek": gross_sek,
            "net_amount_sek": net_sek,
            "company_id": resolved_company_id,
            "receipt_number": unified.receipt_number,
            "other_data": other_data_json,
            "ocr_raw": unified.ocr_raw or "",
            "credit_card_number": unified.credit_card_number,
            "credit_card_last_4_digits": unified.credit_card_last_4_digits,
            "credit_card_brand_full": unified.credit_card_brand_full,
            "credit_card_brand_short": unified.credit_card_brand_short,
            "credit_card_payment_variant": unified.credit_card_payment_variant,
            "credit_card_type": unified.credit_card_type,
            "credit_card_token": unified.credit_card_token,
            "credit_card_entering_mode": unified.credit_card_entering_mode,
            "ai_status": AiStatus.MANUAL_REVIEW.value if needs_review_reason else AiStatus.COMPLETED.value,
            "ai_confidence": result.confidence,
        }

        set_parts: List[str] = [f"{column} = %s" for column in updates.keys()]
        params: List[Any] = list(updates.values())
        set_parts.append("updated_at = NOW()")
        params.append(file_id)

        cursor.execute(
            "UPDATE unified_files SET " + ", ".join(set_parts) + " WHERE id = %s",
            tuple(params),
        )

        # Ensure receipt items carry currency fallback
        receipt_items_with_currency: list[ReceiptItem] = []
        for item in result.receipt_items:
            if not item.currency and unified.currency:
                item.currency = unified.currency
            receipt_items_with_currency.append(item)

        inserted_ids = _replace_receipt_items(cursor, file_id, receipt_items_with_currency)
        for item, item_id in zip(receipt_items_with_currency, inserted_ids):
            item.id = item_id

        logger.info(
            "AI3 created %d receipt_items for %s with IDs: %s (company_match_type=%s created=%s)",
            len(inserted_ids),
            file_id,
            inserted_ids,
            resolved_match_type,
            created,
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
    match_origin: Optional[str] = None,
    connection=None,
) -> None:
    owns_connection = connection is None
    conn = connection or get_connection()
    cursor = conn.cursor()
    try:
        if owns_connection:
            conn.start_transaction()
        match_value = 0
        if matched:
            if match_origin == "manual":
                match_value = 2
            elif match_origin == "confirmed":
                match_value = 3
            else:
                match_value = 1
        if invoice_item_id is not None:
            cursor.execute(
                "UPDATE creditcard_invoice_items SET matched = %s, updated_at = NOW() WHERE id = %s",
                (match_value, invoice_item_id),
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
            f"""
            SELECT il.id,
                   COALESCE(il.merchant_name, il.description) AS candidate_name,
                   il.amount
              FROM invoice_lines AS il
         LEFT JOIN creditcard_receipt_matches AS m ON m.invoice_item_id = il.id
             WHERE (%s IS NULL OR DATE(il.transaction_date) = %s)
               AND (%s IS NULL OR il.amount IS NULL OR ABS(il.amount - %s) <= 5)
               AND (il.match_status IS NULL OR il.match_status IN ('{InvoiceLineMatchStatus.PENDING.value}','{InvoiceLineMatchStatus.UNMATCHED.value}'))
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
    result = ai_service.run_ai1_document_classification(req)
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
    result = ai_service.run_ai2_expense_classification(req)
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
    try:
        result = ai_service.run_ai3_data_extraction(req)
        _persist_extraction_result(req.file_id, result)
        return result
    except Exception as exc:
        _mark_manual_review(req.file_id, str(exc))
        raise


def classify_accounting_internal(req: AccountingClassificationRequest) -> AccountingClassificationResponse:
    chart_of_accounts = _load_chart_of_accounts()
    ai_service = AIService()
    result = ai_service.run_ai4_accounting_classification(req, chart_of_accounts)
    _persist_accounting_proposals(req.file_id, result.proposals, result.confidence)
    return result


def match_credit_card_internal(req: CreditCardMatchRequest) -> CreditCardMatchResponse:
    potential_matches = _potential_credit_matches(req)
    log_event(
        logger,
        "matching.ai.requested",
        file_id=req.file_id,
        purchase_date=req.purchase_date,
        amount=req.amount,
        merchant_name=req.merchant_name,
        candidates=len(potential_matches),
    )
    ai_service = AIService()
    result = ai_service.run_ai5_credit_card_match(req, potential_matches)
    log_event(
        logger,
        "matching.ai.result",
        file_id=req.file_id,
        matched=result.matched,
        confidence=result.confidence,
        invoice_item_id=result.credit_card_invoice_item_id,
        details=result.match_details,
    )
    matched_amount: Optional[Decimal] = None
    if result.match_details and result.match_details.get("matched_amount") is not None:
        matched_amount = Decimal(str(result.match_details["matched_amount"]))
    persist_ok = True
    try:
        _persist_credit_card_match(
            req.file_id,
            result.credit_card_invoice_item_id,
            matched_amount,
            result.confidence,
            result.matched,
            match_origin="auto" if result.matched else None,
        )
    except Exception:
        persist_ok = False
        log_event(
            logger,
            "matching.ai.persist_failed",
            file_id=req.file_id,
            invoice_item_id=result.credit_card_invoice_item_id,
            level="error",
        )
        raise
    log_event(
        logger,
        "matching.ai.persisted",
        file_id=req.file_id,
        invoice_item_id=result.credit_card_invoice_item_id,
        matched_amount=matched_amount,
        matched=result.matched,
        persisted=persist_ok,
    )
    # AI7: Enrichment after credit card match
    try:
        run_box_enrichment(req.file_id)
    except Exception:
        logger.exception("AI7 error after credit card match on %s", req.file_id)
        log_event(
            logger,
            "matching.ai.box_enrichment_failed",
            file_id=req.file_id,
            level="error",
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
        ai7_stats = run_box_enrichment(req.file_id)
        if not ai7_stats.get("success"):
            logger.warning(
                "AI7 box enrichment failed for %s via classify_accounting: %s",
                req.file_id,
                ai7_stats.get("error", "unknown"),
            )
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
                        from services.tasks.file_management_tasks import _load_accounting_inputs, _load_receipt_items, _move_to_manual_review

                        accounting = _load_accounting_inputs(file_id)
                        if not accounting:
                            continue

                        if accounting.get("ai4_ready") is False:
                            reason = str(accounting.get("reason") or "missing totals for accounting")
                            file_result["ai4_status"] = "needs_review"
                            file_result["ai4_reason"] = reason
                            _move_to_manual_review(file_id, reason)
                            continue

                        receipt_items_for_ai4 = _load_receipt_items(file_id)
                        vendor_name = accounting.get("vendor_name") or ""

                        logger.info(
                            "AI4 processing %s with %d receipt_items",
                            file_id,
                            len(receipt_items_for_ai4),
                        )

                        try:
                            from services.ai_service import AccountingProposalValidationError
                            from services.ai_logging import log_ai_call

                            classify_accounting_internal(
                                AccountingClassificationRequest(
                                    file_id=file_id,
                                    document_type=document_type or "other",
                                    expense_type=expense_type or "personal",
                                    gross_amount=Decimal(str(accounting.get("gross_amount_sek") or 0)),
                                    net_amount=Decimal(str(accounting.get("net_amount_sek") or 0)),
                                    vat_amount=Decimal(str(accounting.get("vat_amount_sek") or 0)),
                                    vendor_name=vendor_name,
                                    receipt_items=receipt_items_for_ai4,
                                )
                            )
                        except AccountingProposalValidationError as exc:
                            error_msg = f"{type(exc).__name__}: {str(exc)}"
                            file_result["ai4_status"] = "needs_review"
                            file_result["ai4_error"] = error_msg
                            _move_to_manual_review(file_id, error_msg)
                            log_ai_call(
                                file_id=file_id,
                                job="ai4",
                                status="error",
                                ai_stage_name="AI4-AccountingClassification",
                                log_text="Needs review: AI4 validation failed",
                                error_message=error_msg,
                            )
                        else:
                            file_result["steps_completed"].append("AI4")
                            stats = run_box_enrichment(file_id)
                            if stats.get("success"):
                                if "AI7" not in file_result["steps_completed"]:
                                    file_result["steps_completed"].append("AI7")
                                file_result["ai7"] = stats
                            else:
                                file_result["ai7_error"] = stats.get("error", "unknown")
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
                    elif step == "AI7":
                        stats = run_box_enrichment(file_id)
                        if stats.get("success"):
                            if "AI7" not in file_result["steps_completed"]:
                                file_result["steps_completed"].append("AI7")
                            file_result["ai7"] = stats
                        else:
                            file_result["ai7_error"] = stats.get("error", "unknown")
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
