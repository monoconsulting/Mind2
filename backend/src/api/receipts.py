from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional

import json
import logging
import os
from pathlib import Path
from flask import Blueprint, jsonify, request, send_file

try:
    from PIL import Image
except Exception:
    Image = None  # type: ignore[assignment]

try:
    # Optional DB dependency; endpoints should still respond if DB missing
    from services.db.connection import db_cursor
except Exception:
    db_cursor = None  # type: ignore


logger = logging.getLogger(__name__)

receipts_bp = Blueprint("receipts", __name__)


def _storage_dir() -> Path:
    base = os.getenv("STORAGE_DIR", "/data/storage")
    p = Path(base) / "line_items"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _line_items_path(rid: str) -> Path:
    return _storage_dir() / f"{rid}.json"


def _coerce_float(value: Any) -> float | None:
    if value in (None, "", False):
        return None
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).replace(",", "."))
        except Exception:
            return None


def _coerce_int(value: Any) -> int | None:
    if value in (None, "", False):
        return None
    try:
        return int(value)
    except Exception:
        try:
            decimal_value = Decimal(str(value).replace(",", "."))
            return int(decimal_value)
        except Exception:
            return None


def _normalise_store_line_item(raw: dict[str, Any], receipt_currency: str | None = None) -> dict[str, Any] | None:
    name = (raw.get("name") or raw.get("description") or raw.get("item_name") or "").strip()
    if not name:
        return None

    quantity = _coerce_int(raw.get("number") or raw.get("quantity") or raw.get("qty") or 0) or 0

    unit_net = _coerce_float(
        raw.get("item_price_ex_vat")
        or raw.get("unit_price_ex_vat")
        or raw.get("price_ex_vat")
        or raw.get("unit_net")
    )
    unit_gross = _coerce_float(
        raw.get("item_price_inc_vat")
        or raw.get("unit_price_inc_vat")
        or raw.get("price_inc_vat")
        or raw.get("unit_gross")
        or raw.get("unit_price")
    )

    total_net = _coerce_float(
        raw.get("item_total_price_ex_vat")
        or raw.get("total_price_ex_vat")
        or raw.get("total_net")
        or raw.get("net_total")
        or raw.get("amount_ex_vat")
    )
    total_gross = _coerce_float(
        raw.get("item_total_price_inc_vat")
        or raw.get("total_price_inc_vat")
        or raw.get("total_gross")
        or raw.get("gross_total")
        or raw.get("total_amount")
        or raw.get("total")
    )

    vat_percentage = _coerce_float(raw.get("vat_percentage") or raw.get("vat_rate"))
    vat_amount = _coerce_float(raw.get("vat") or raw.get("vat_amount") or raw.get("item_vat_total"))

    if total_net is None and total_gross is not None and vat_percentage is not None:
        divisor = 1 + (vat_percentage / 100) if vat_percentage != -100 else 1
        if divisor:
            total_net = total_gross / divisor
    if total_gross is None and total_net is not None and vat_percentage is not None:
        total_gross = total_net * (1 + vat_percentage / 100)

    if vat_amount is None and total_gross is not None and total_net is not None:
        vat_amount = total_gross - total_net
    if vat_amount is None and vat_percentage is not None and total_net is not None:
        vat_amount = total_net * vat_percentage / 100

    if quantity > 0:
        if unit_net is None and total_net is not None:
            unit_net = total_net / quantity
        if unit_gross is None and total_gross is not None:
            unit_gross = total_gross / quantity

    currency = (raw.get("currency") or receipt_currency or "SEK").strip() or "SEK"

    return {
        "id": raw.get("id") or raw.get("item_id") or None,
        "article_id": (raw.get("article_id") or raw.get("articleNumber") or raw.get("item_code") or "").strip()[:222],
        "name": name[:222],
        "number": max(quantity, 0),
        "item_price_ex_vat": unit_net,
        "item_price_inc_vat": unit_gross,
        "item_total_price_ex_vat": total_net,
        "item_total_price_inc_vat": total_gross,
        "currency": currency[:11],
        "vat": vat_amount,
        "vat_percentage": vat_percentage,
    }


def _load_line_items_from_store(rid: str, receipt_currency: str | None = None) -> list[dict[str, Any]]:
    path = _line_items_path(rid)
    if not path.exists():
        return []
    try:
        raw_content = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Failed to parse stored line items for %s", rid, exc_info=True)
        return []

    if isinstance(raw_content, list):
        raw_items = raw_content
    elif isinstance(raw_content, dict):
        for key in ("items", "line_items", "receipt_items"):
            candidate = raw_content.get(key)
            if isinstance(candidate, list):
                raw_items = candidate
                break
        else:
            raw_items = []
    else:
        raw_items = []

    normalised: list[dict[str, Any]] = []
    for entry in raw_items:
        if isinstance(entry, dict):
            mapped = _normalise_store_line_item(entry, receipt_currency)
            if mapped:
                normalised.append(mapped)
    logger.debug("Line item store lookup for %s returned %d entries", rid, len(normalised))
    return normalised


def _store_line_items(rid: str, items: Iterable[dict[str, Any]]) -> bool:
    serialisable: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        serialisable.append(
            {
                "article_id": (item.get("article_id") or "")[:222],
                "name": (item.get("name") or "")[:222],
                "number": item.get("number") if isinstance(item.get("number"), int) else _coerce_int(item.get("number")) or 0,
                "item_price_ex_vat": _coerce_float(item.get("item_price_ex_vat")),
                "item_price_inc_vat": _coerce_float(item.get("item_price_inc_vat")),
                "item_total_price_ex_vat": _coerce_float(item.get("item_total_price_ex_vat")),
                "item_total_price_inc_vat": _coerce_float(item.get("item_total_price_inc_vat")),
                "currency": (item.get("currency") or "SEK")[:11],
                "vat": _coerce_float(item.get("vat")),
                "vat_percentage": _coerce_float(item.get("vat_percentage")),
            }
        )
    try:
        _line_items_path(rid).write_text(json.dumps(serialisable, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        logger.error("Failed to persist line items for %s", rid, exc_info=True)
        return False

# Preview directory removed - using original images only
# def _preview_dir() -> Path:
#     base = os.getenv("STORAGE_DIR", "/data/storage")
#     p = Path(base) / "previews"
#     p.mkdir(parents=True, exist_ok=True)
#     return p


# Preview path removed - using original images only
# def _preview_path(rid: str) -> Path:
#     return _preview_dir() / f"{rid}.jpg"


def _find_receipt_image_path(rid: str) -> Path | None:
    try:
        root = _storage_dir().parent / rid
        if not root.exists():
            return None
        for candidate in sorted(root.iterdir()):
            if candidate.is_file() and candidate.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                return candidate
    except Exception:
        return None
    return None


# Preview generation removed - using original images only
# def _generate_preview(rid: str, source: Path, target: Path) -> bool:
#     # This function is deprecated - we now use original images only
#     return False


# Preview generation removed - using original images only
# def _ensure_preview(rid: str) -> Path | None:
#     # This function is deprecated - we now use original images only
#     return None


def _count_line_items(rid: str) -> int:
    try:
        p = _line_items_path(rid)
        if not p.exists():
            return 0
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return len(items)
    except Exception:
        return 0
    return 0


def _fetch_saved_accounting_entries(rid: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if db_cursor is None:
        return entries
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, account_code, debit, credit, vat_rate, notes FROM ai_accounting_proposals "
                    "WHERE receipt_id=%s ORDER BY id ASC"
                ),
                (rid,),
            )
            for row in cur.fetchall() or []:
                (
                    entry_id,
                    account,
                    debit,
                    credit,
                    vat_rate,
                    notes,
                ) = row
                entries.append(
                    {
                        "id": int(entry_id) if entry_id is not None else None,
                        "account": account,
                        "debit": float(debit) if debit is not None else 0.0,
                        "credit": float(credit) if credit is not None else 0.0,
                        "vat_rate": float(vat_rate) if vat_rate is not None else None,
                        "notes": notes or "",
                    }
                )
    except Exception:
        entries = []
    return entries


def _save_accounting_entries(rid: str, entries: list[dict[str, Any]]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (rid,))
            for entry in entries:
                account = (entry.get("account") or "").strip()
                if not account:
                    continue
                debit = Decimal(str(entry.get("debit") or 0))
                credit = Decimal(str(entry.get("credit") or 0))
                vat_rate = entry.get("vat_rate")
                vat_val = Decimal(str(vat_rate)) if vat_rate not in (None, "", []) else None
                notes = entry.get("notes")
                cur.execute(
                    (
                        "INSERT INTO ai_accounting_proposals (receipt_id, account_code, debit, credit, vat_rate, notes) "
                        "VALUES (%s, %s, %s, %s, %s, %s)"
                    ),
                    (rid, account, debit, credit, vat_val, (notes or None)),
                )
        return True
    except Exception:
        return False


def _fetch_receipt_details(rid: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": rid,
        "merchant": None,
        "orgnr": None,
        "vat": None,
        "purchase_datetime": None,
        "receipt_number": None,
        "payment_type": None,
        "expense_type": None,
        "credit_card_number": None,
        "credit_card_last_4": None,
        "credit_card_type": None,
        "credit_card_brand_full": None,
        "credit_card_brand_short": None,
        "credit_card_payment_variant": None,
        "credit_card_token": None,
        "credit_card_entering_mode": None,
        "currency": None,
        "exchange_rate": None,
        "gross_amount": None,
        "net_amount": None,
        "gross_amount_sek": None,
        "net_amount_sek": None,
        "total_vat_25": None,
        "total_vat_12": None,
        "total_vat_6": None,
        "ai_status": None,
        "ai_confidence": None,
        "other_data": None,
        "ocr_raw": None,
        "tags": [],
    }
    if db_cursor is None:
        return data
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT u.id, c.name, u.company_id, u.vat, u.purchase_datetime, u.receipt_number, u.payment_type, "
                    "u.expense_type, u.credit_card_number, u.credit_card_last_4_digits, u.credit_card_type, "
                    "u.credit_card_brand_full, u.credit_card_brand_short, u.credit_card_payment_variant, "
                    "u.credit_card_token, u.credit_card_entering_mode, u.currency, u.exchange_rate, "
                    "u.gross_amount, u.net_amount, u.gross_amount_sek, u.net_amount_sek, "
                    "u.total_vat_25, u.total_vat_12, u.total_vat_6, "
                    "u.ai_status, u.ai_confidence, u.other_data, u.ocr_raw, "
                    "COALESCE(GROUP_CONCAT(DISTINCT t.tag), '') as tags "
                    "FROM unified_files u "
                    "LEFT JOIN companies c ON c.id = u.company_id "
                    "LEFT JOIN file_tags t ON t.file_id = u.id "
                    "WHERE u.id=%s AND u.deleted_at IS NULL "
                    "GROUP BY u.id, c.name, u.company_id, u.vat, u.purchase_datetime, u.receipt_number, u.payment_type, "
                    "u.expense_type, u.credit_card_number, u.credit_card_last_4_digits, u.credit_card_type, "
                    "u.credit_card_brand_full, u.credit_card_brand_short, u.credit_card_payment_variant, "
                    "u.credit_card_token, u.credit_card_entering_mode, u.currency, u.exchange_rate, "
                    "u.gross_amount, u.net_amount, u.gross_amount_sek, u.net_amount_sek, "
                    "u.total_vat_25, u.total_vat_12, u.total_vat_6, "
                    "u.ai_status, u.ai_confidence, u.other_data, u.ocr_raw"
                ),
                (rid,),
            )
            row = cur.fetchone()
            if not row:
                return data
            (
                _id, merchant, company_id, vat, purchase_dt, receipt_number, payment_type,
                expense_type, card_number, card_last_4, card_type, card_brand_full, card_brand_short,
                card_payment_variant, card_token, card_entering_mode, currency, exchange_rate,
                gross, net, gross_sek, net_sek, vat_25, vat_12, vat_6,
                status, confidence, other_data, ocr_raw, tag_csv,
            ) = row
            data.update(
                {
                    "id": _id,
                    "merchant": merchant,
                    "company_id": int(company_id) if company_id not in (None, 0) else None,
                    "vat": vat,
                    "purchase_datetime": purchase_dt.isoformat() if hasattr(purchase_dt, "isoformat") else purchase_dt,
                    "receipt_number": receipt_number,
                    "payment_type": payment_type,
                    "expense_type": expense_type,
                    "credit_card_number": card_number,
                    "credit_card_last_4": str(card_last_4) if card_last_4 not in (None, 0) else None,
                    "credit_card_last_4_digits": str(card_last_4) if card_last_4 not in (None, 0) else None,
                    "credit_card_type": card_type,
                    "credit_card_brand_full": card_brand_full,
                    "credit_card_brand_short": card_brand_short,
                    "credit_card_payment_variant": card_payment_variant,
                    "credit_card_token": card_token,
                    "credit_card_entering_mode": card_entering_mode,
                    "currency": currency,
                    "exchange_rate": float(exchange_rate) if exchange_rate not in (None, 0) else None,
                    "gross_amount": float(gross) if gross is not None else None,
                    "net_amount": float(net) if net is not None else None,
                    "gross_amount_sek": float(gross_sek) if gross_sek not in (None, 0) else None,
                    "net_amount_sek": float(net_sek) if net_sek not in (None, 0) else None,
                    "total_vat_25": float(vat_25) if vat_25 is not None else None,
                    "total_vat_12": float(vat_12) if vat_12 is not None else None,
                    "total_vat_6": float(vat_6) if vat_6 is not None else None,
                    "ai_status": status,
                    "ai_confidence": float(confidence) if confidence is not None else None,
                    "other_data": other_data,
                    "tags": [t for t in (tag_csv or "").split(",") if t],
                    "ocr_raw": ocr_raw,
                }
            )
    except Exception as e:
        logger.error(f"_fetch_receipt_details error for {rid}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return data
    return data


def _fetch_company_by_id(company_id: int | None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": None,
        "name": None,
        "orgnr": None,
        "address": None,
        "address2": None,
        "zip": None,
        "city": None,
        "country": None,
        "phone": None,
        "www": None,
        "email": None,
    }
    if db_cursor is None or company_id is None or company_id == 0:
        return data
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, name, orgnr, address, address2, zip, city, country, phone, www, email "
                    "FROM companies WHERE id=%s"
                ),
                (company_id,),
            )
            row = cur.fetchone()
            if not row:
                return data
            (cid, name, orgnr, address, address2, zip_code, city, country, phone, www, email) = row
            data.update(
                {
                    "id": int(cid) if cid is not None else None,
                    "name": name,
                    "orgnr": orgnr,
                    "address": address,
                    "address2": address2,
                    "zip": zip_code,
                    "city": city,
                    "country": country,
                    "phone": phone,
                    "www": www,
                    "email": email,
                }
            )
    except Exception:
        return data
    return data


def _fetch_receipt_items_from_db(rid: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if db_cursor is None:
        return items
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, article_id, name, number, item_price_ex_vat, item_price_inc_vat, "
                    "item_total_price_ex_vat, item_total_price_inc_vat, currency, vat, vat_percentage "
                    "FROM receipt_items WHERE main_id=%s ORDER BY id ASC"
                ),
                (rid,),
            )
            for row in cur.fetchall() or []:
                (
                    item_id,
                    article_id,
                    name,
                    number,
                    price_ex_vat,
                    price_inc_vat,
                    total_ex_vat,
                    total_inc_vat,
                    currency,
                    vat,
                    vat_percentage,
                ) = row
                items.append(
                    {
                        "id": int(item_id) if item_id is not None else None,
                        "article_id": article_id or "",
                        "name": name or "",
                        "number": int(number) if number not in (None, "") else None,
                        "item_price_ex_vat": float(price_ex_vat) if price_ex_vat is not None else None,
                        "item_price_inc_vat": float(price_inc_vat) if price_inc_vat is not None else None,
                        "item_total_price_ex_vat": float(total_ex_vat) if total_ex_vat is not None else None,
                        "item_total_price_inc_vat": float(total_inc_vat) if total_inc_vat is not None else None,
                        "currency": currency or "SEK",
                        "vat": float(vat) if vat is not None else None,
                        "vat_percentage": float(vat_percentage) if vat_percentage is not None else None,
                    }
                )
    except Exception:
        logger.error("Failed to fetch receipt items from database for %s", rid, exc_info=True)
        return []
    return items


def _fetch_receipt_items(rid: str, receipt_currency: str | None = None) -> list[dict[str, Any]]:
    db_items = _fetch_receipt_items_from_db(rid)
    if db_items:
        return db_items
    store_items = _load_line_items_from_store(rid, receipt_currency)
    return store_items


def _get_receipt_items_with_source(rid: str, receipt_currency: str | None = None) -> tuple[list[dict[str, Any]], str]:
    db_items = _fetch_receipt_items_from_db(rid)
    if db_items:
        return db_items, "database"
    store_items = _load_line_items_from_store(rid, receipt_currency)
    if store_items:
        logger.info("Using file_store items for %s (count=%d)", rid, len(store_items))
        return store_items, "file_store"
    logger.info("No receipt items found for %s", rid)
    return [], "empty"


def _normalise_decimal(value: Any) -> Decimal:
    try:
        if value in (None, ""):
            return Decimal("0")
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _normalise_receipt_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        name = (raw.get("name") or raw.get("description") or "").strip()
        if not name:
            continue
        article_id = (raw.get("article_id") or "").strip()
        try:
            quantity = int(raw.get("number") or raw.get("quantity") or 0)
        except Exception:
            quantity = 0
        currency = (raw.get("currency") or "SEK").strip() or "SEK"
        normalised.append(
            {
                "article_id": article_id[:222],
                "name": name[:222],
                "number": max(quantity, 0),
                "item_price_ex_vat": _normalise_decimal(raw.get("item_price_ex_vat")),
                "item_price_inc_vat": _normalise_decimal(raw.get("item_price_inc_vat")),
                "item_total_price_ex_vat": _normalise_decimal(raw.get("item_total_price_ex_vat")),
                "item_total_price_inc_vat": _normalise_decimal(raw.get("item_total_price_inc_vat")),
                "currency": currency[:11],
                "vat": _normalise_decimal(raw.get("vat")),
                "vat_percentage": _normalise_decimal(raw.get("vat_percentage")),
            }
        )
    return normalised


def _normalise_accounting_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        account = (raw.get("account") or raw.get("account_code") or "").strip()
        if not account:
            continue
        try:
            debit = float(raw.get("debit") or 0)
        except Exception:
            debit = 0.0
        try:
            credit = float(raw.get("credit") or 0)
        except Exception:
            credit = 0.0
        vat_rate = raw.get("vat_rate")
        try:
            vat_value = float(vat_rate) if vat_rate not in (None, "", []) else None
        except Exception:
            vat_value = None
        notes = (raw.get("notes") or "").strip()
        normalised.append(
            {
                "account": account[:32],
                "debit": debit,
                "credit": credit,
                "vat_rate": vat_value,
                "notes": notes or None,
            }
        )
    return normalised


def _normalise_receipt_update(payload: dict[str, Any]) -> dict[str, Any]:
    editable: dict[str, Any] = {}
    if not isinstance(payload, dict):
        return editable

    def add_string(source_key: str, *, target_key: Optional[str] = None, max_length: Optional[int] = None) -> None:
        if source_key not in payload:
            return
        key = target_key or source_key
        value = payload.get(source_key)
        if value is None:
            editable[key] = None
            return
        if isinstance(value, str):
            cleaned = value.strip()
        else:
            cleaned = str(value).strip()
        if cleaned == "":
            editable[key] = None
            return
        if max_length is not None:
            editable[key] = cleaned[:max_length]
        else:
            editable[key] = cleaned

    def add_float(source_key: str, *, target_key: Optional[str] = None) -> None:
        if source_key not in payload:
            return
        key = target_key or source_key
        value = payload.get(source_key)
        if value in (None, "", []):
            editable[key] = None
            return
        try:
            editable[key] = float(value)
        except Exception:
            pass

    add_string("vat", max_length=32)
    add_string("orgnr", target_key="vat", max_length=32)
    add_string("receipt_number", max_length=128)
    add_string("payment_type", max_length=255)
    add_string("expense_type", max_length=64)
    add_string("credit_card_number", max_length=64)
    add_string("credit_card_last_4_digits", max_length=8)
    add_string("credit_card_last_4", target_key="credit_card_last_4_digits", max_length=8)
    add_string("credit_card_type", max_length=64)
    add_string("credit_card_brand_full", max_length=128)
    add_string("credit_card_brand_short", max_length=64)
    add_string("credit_card_payment_variant", max_length=64)
    add_string("credit_card_token", max_length=128)
    add_string("credit_card_entering_mode", max_length=64)
    add_string("currency", max_length=16)
    add_string("ai_status", max_length=64)
    add_string("status", target_key="ai_status", max_length=64)
    add_string("other_data")
    add_string("ocr_raw")
    add_string("purchase_datetime")
    add_string("purchase_date", target_key="purchase_datetime")

    add_float("gross_amount")
    add_float("net_amount")
    add_float("gross_amount_sek")
    add_float("net_amount_sek")
    add_float("total_vat_25")
    add_float("total_vat_12")
    add_float("total_vat_6")
    add_float("exchange_rate")
    add_float("ai_confidence")

    return editable


def _commit_receipt_update(rid: str, editable: dict[str, Any]) -> bool:
    if db_cursor is None or not editable:
        return False
    fields = [f"{k}=%s" for k in editable.keys()]
    values: list[Any] = list(editable.values())
    values.append(rid)
    try:
        with db_cursor() as cur:
            set_clause = ", ".join(fields)
            sql = "UPDATE unified_files SET " + set_clause + ", updated_at=NOW() WHERE id=%s"
            cur.execute(sql, tuple(values))
            return cur.rowcount > 0
    except Exception:
        return False


def _normalise_company_update(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    fields = {
        "name": 255,
        "orgnr": 32,
        "address": 255,
        "address2": 255,
        "zip": 32,
        "city": 128,
        "country": 128,
        "phone": 64,
        "www": 255,
        "email": 255,
    }
    normalised: dict[str, Any] = {}
    for key, max_len in fields.items():
        if key not in payload:
            continue
        value = payload.get(key)
        if value is None:
            normalised[key] = None
            continue
        text = str(value).strip()
        if text == "":
            normalised[key] = None
            continue
        normalised[key] = text[:max_len]
    return normalised


def _commit_company_update(rid: str, company_id: Optional[int], payload: dict[str, Any]) -> tuple[bool, Optional[int]]:
    if db_cursor is None or not payload:
        return False, company_id
    try:
        with db_cursor() as cur:
            if company_id:
                fields = [f"{column}=%s" for column in payload.keys()]
                values = list(payload.values())
                values.append(company_id)
                sql = "UPDATE companies SET " + ", ".join(fields) + ", updated_at=NOW() WHERE id=%s"
                cur.execute(sql, tuple(values))
                return cur.rowcount > 0, company_id

            has_value = any(value not in (None, "", []) for value in payload.values())
            if not has_value:
                return False, company_id
            columns = ", ".join(payload.keys())
            placeholders = ", ".join(["%s"] * len(payload))
            values = list(payload.values())
            cur.execute(
                f"INSERT INTO companies ({columns}, created_at, updated_at) VALUES ({placeholders}, NOW(), NOW())",
                tuple(values),
            )
            new_company_id = int(cur.lastrowid)
            cur.execute(
                "UPDATE unified_files SET company_id=%s, updated_at=NOW() WHERE id=%s",
                (new_company_id, rid),
            )
            return True, new_company_id
    except Exception:  # pragma: no cover - defensive log
        logger.error("Failed to persist company update for %s", rid, exc_info=True)
        return False, company_id


def _normalise_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        return []
    normalised: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = str(candidate).strip()
        if not text:
            continue
        tag = text[:64]
        if tag not in seen:
            normalised.append(tag)
            seen.add(tag)
    return normalised


def _replace_file_tags(rid: str, tags: list[str]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM file_tags WHERE file_id=%s", (rid,))
            if not tags:
                return True
            sql = "INSERT INTO file_tags (file_id, tag, created_at) VALUES (%s, %s, NOW())"
            for tag in tags:
                cur.execute(sql, (rid, tag))
        return True
    except Exception:  # pragma: no cover - defensive log
        logger.error("Failed to replace tags for %s", rid, exc_info=True)
        return False


def _replace_receipt_items(rid: str, items: list[dict[str, Any]]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM receipt_items WHERE main_id=%s", (rid,))
            if not items:
                return True
            insert_sql = (
                "INSERT INTO receipt_items (main_id, article_id, name, number, item_price_ex_vat, item_price_inc_vat, "
                "item_total_price_ex_vat, item_total_price_inc_vat, currency, vat, vat_percentage) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            for item in items:
                cur.execute(
                    insert_sql,
                    (
                        rid,
                        item.get("article_id") or "",
                        item.get("name") or "",
                        item.get("number") or 0,
                        item.get("item_price_ex_vat"),
                        item.get("item_price_inc_vat"),
                        item.get("item_total_price_ex_vat"),
                        item.get("item_total_price_inc_vat"),
                        item.get("currency") or "SEK",
                        item.get("vat"),
                        item.get("vat_percentage"),
                    ),
                )
        return True
    except Exception:
        return False


def _load_boxes(rid: str) -> list[dict[str, Any]]:
    try:
        root = _storage_dir().parent / rid
        p = root / "boxes.json"
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


@receipts_bp.get("/receipts")
def list_receipts() -> Any:
    # Optional filters
    q_status = request.args.get("status")
    q_merchant = request.args.get("merchant")
    q_orgnr = request.args.get("orgnr")
    q_tags = request.args.get("tags")
    q_from = request.args.get("from")
    q_to = request.args.get("to")
    q_file_type = request.args.get("file_type")

    # Simple pagination
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except Exception:
        page = 1
    try:
        page_size = int(request.args.get("page_size", 50))
    except Exception:
        page_size = 50
    page_size = max(1, min(page_size, 100))
    offset = (page - 1) * page_size

    items: list[dict[str, Any]] = []
    total = 0
    meta = {"page": page, "page_size": page_size}

    if db_cursor is not None:
        try:
            where: list[str] = ["u.deleted_at IS NULL", "u.file_type != 'pdf'"]
            params: list[Any] = []
            if q_status:
                where.append("ai_status = %s")
                params.append(q_status)
            if q_merchant:
                where.append("c.name LIKE %s")
                params.append(f"%{q_merchant}%")
            if q_orgnr:
                where.append("orgnr = %s")
                params.append(q_orgnr)
            if q_from:
                where.append("purchase_datetime >= %s")
                params.append(q_from)
            if q_to:
                where.append("purchase_datetime <= %s")
                params.append(q_to)
            if q_file_type:
                where.append("u.file_type = %s")
                params.append(q_file_type)
            if q_tags:
                # Simple ANY tag filter (comma-separated)
                tag_list = [t.strip() for t in q_tags.split(",") if t.strip()]
                if tag_list:
                    placeholders = ",".join(["%s"] * len(tag_list))
                    where.append(
                        (
                            f"id IN (SELECT file_id FROM file_tags WHERE tag IN ({placeholders}))"
                        )
                    )
                    params.extend(tag_list)

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""

            # Count (needs same joins as main query)
            with db_cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(1) FROM unified_files u LEFT JOIN companies c ON c.id = u.company_id {where_sql}",
                    tuple(params),
                )
                (total,) = cur.fetchone() or (0,)

            # Page
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT u.id, u.original_filename, c.name as company_name, u.purchase_datetime, u.net_amount_sek, u.gross_amount_sek, u.ai_status, u.file_type, u.submitted_by, "
                        "u.file_creation_timestamp, fl.lat, fl.lon, fl.acc, "
                        "COALESCE(GROUP_CONCAT(t.tag), '') as tags "
                        "FROM unified_files u "
                        "LEFT JOIN companies c ON c.id = u.company_id "
                        "LEFT JOIN file_tags t ON t.file_id=u.id "
                        "LEFT JOIN file_locations fl ON fl.file_id=u.id "
                        + where_sql
                        + " GROUP BY u.id, u.file_creation_timestamp, fl.lat, fl.lon, fl.acc, c.name ORDER BY u.created_at DESC LIMIT %s OFFSET %s"
                    ),
                    tuple(params + [page_size, offset]),
                )
                results = cur.fetchall()
                logger.info(f"Query returned {len(results)} rows")
                for rid, fname, merchant, pdt, net, gross, status, file_type, submitted_by, file_creation_ts, lat, lon, acc, tag_csv in results:
                    purchase_iso = pdt.isoformat() if hasattr(pdt, "isoformat") else pdt
                    purchase_date = None
                    if hasattr(pdt, "date"):
                        try:
                            purchase_date = pdt.date().isoformat()
                        except Exception:
                            purchase_date = None
                    elif isinstance(pdt, str) and pdt:
                        purchase_date = pdt.split("T")[0]

                    # Format file creation timestamp
                    file_creation_iso = None
                    if file_creation_ts:
                        if hasattr(file_creation_ts, "isoformat"):
                            file_creation_iso = file_creation_ts.isoformat()
                        elif isinstance(file_creation_ts, str):
                            file_creation_iso = file_creation_ts

                    # Build location object if coordinates exist
                    location = None
                    if lat is not None and lon is not None:
                        location = {
                            "lat": float(lat),
                            "lon": float(lon),
                            "accuracy": float(acc) if acc is not None else None
                        }

                    net_value = float(net) if net is not None else None
                    gross_value = float(gross) if gross is not None else None
                    line_items = _count_line_items(rid)
                    items.append(
                        {
                            "id": rid,
                            "original_filename": fname,
                            "merchant": merchant,
                            "purchase_datetime": purchase_iso,
                            "purchase_date": purchase_date,
                            "file_creation_timestamp": file_creation_iso,
                            "location": location,
                            "net_amount": net_value,
                            "gross_amount": gross_value,
                            "status": status,
                            "ai_status": status,  # Add ai_status field so frontend deps can detect changes
                            "file_type": file_type,
                            "submitted_by": submitted_by,
                            "line_item_count": line_items,
                            "tags": [t for t in (tag_csv or "").split(",") if t],
                        }
                    )
        except Exception as e:
            # Fallback to empty but still 200
            logger.error(f"Error listing receipts: {e}")
            import traceback
            logger.error(traceback.format_exc())
            items = []
            total = 0
    meta["total"] = int(total)
    meta["items"] = len(items)
    return jsonify({"items": items, "meta": meta}), 200


@receipts_bp.get("/receipts/<rid>")
def get_receipt(rid: str) -> Any:
    details = _fetch_receipt_details(rid)
    found = any(
        details.get(key) not in (None, [], "")
        for key in ("merchant", "purchase_datetime", "gross_amount", "net_amount")
    )
    if not found:
        details.setdefault("status", "Placeholder")
    details["found"] = found
    return jsonify(details), 200


@receipts_bp.route("/receipts/<rid>", methods=["PUT", "PATCH"])
def update_receipt(rid: str) -> Any:
    payload = request.get_json(silent=True) or {}
    editable = _normalise_receipt_update(payload)
    updated = _commit_receipt_update(rid, editable)
    # Accept line_items in payload to persist to file store
    if "line_items" in payload and isinstance(payload["line_items"], list):
        try:
            _line_items_path(rid).write_text(json.dumps(payload["line_items"], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return jsonify({"id": rid, "updated": updated, "data": payload}), 200


@receipts_bp.get("/receipts/<rid>/modal")
def get_receipt_modal(rid: str) -> Any:
    details = _fetch_receipt_details(rid)
    company_id = details.get("company_id")
    company = _fetch_company_by_id(company_id)
    items, items_source = _get_receipt_items_with_source(rid, details.get("currency"))
    proposals = _fetch_saved_accounting_entries(rid)
    boxes = _load_boxes(rid)
    response = {
        "id": rid,
        "receipt": details,
        "company": company,
        "items": items,
        "proposals": proposals,
        "boxes": boxes,
        "meta": {
            "items_count": len(items),
            "items_source": items_source,
            "proposals_count": len(proposals),
            "boxes_count": len(boxes),
        },
    }
    if items_source != "database":
        response["line_items"] = items
    return jsonify(response), 200


@receipts_bp.put("/receipts/<rid>/modal")
def put_receipt_modal(rid: str) -> Any:
    if db_cursor is None:
        return jsonify({"error": "db_unavailable"}), 503

    payload = request.get_json(silent=True) or {}

    current_details = _fetch_receipt_details(rid)
    current_company_id = None
    existing_tags: list[str] = []
    existing_company_snapshot: dict[str, Any] = {}
    if isinstance(current_details, dict):
        current_company_id = current_details.get("company_id")
        existing_tags = list(current_details.get("tags") or [])
        if current_company_id not in (None, 0):
            existing_company_snapshot = _fetch_company_by_id(current_company_id)

    receipt_payload = payload.get("receipt") or {}
    company_payload = payload.get("company") or {}
    items_payload = payload.get("items")
    proposals_payload = (
        payload.get("proposals")
        if "proposals" in payload
        else payload.get("accounting") or payload.get("accounting_proposals")
    )

    editable = _normalise_receipt_update(receipt_payload)
    receipt_updated = _commit_receipt_update(rid, editable)

    tags_updated = False
    if isinstance(receipt_payload, dict) and "tags" in receipt_payload:
        tags = _normalise_tags(receipt_payload.get("tags"))
        if tags != existing_tags:
            tags_updated = _replace_file_tags(rid, tags)

    def _normalise_existing_company_value(value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value

    company_updated = False
    if isinstance(company_payload, dict):
        company_updates = _normalise_company_update(company_payload)
        if company_updates:
            if current_company_id in (None, 0):
                has_changes = any(value is not None for value in company_updates.values())
            else:
                has_changes = any(
                    company_updates[key]
                    != _normalise_existing_company_value(existing_company_snapshot.get(key))
                    for key in company_updates.keys()
                )
            if has_changes:
                company_updated, current_company_id = _commit_company_update(
                    rid,
                    int(current_company_id) if current_company_id not in (None, 0) else None,
                    company_updates,
                )

    items_updated = False
    if items_payload is not None:
        normalised_items = _normalise_receipt_items(items_payload)
        db_items_updated = _replace_receipt_items(rid, normalised_items)
        store_items_updated = _store_line_items(rid, normalised_items)
        items_updated = db_items_updated or store_items_updated

    proposals_updated = False
    if proposals_payload is not None:
        normalised_proposals = _normalise_accounting_entries(proposals_payload)
        proposals_updated = _save_accounting_entries(rid, normalised_proposals)

    refreshed_receipt = _fetch_receipt_details(rid)
    refreshed_items, refreshed_items_source = _get_receipt_items_with_source(rid, refreshed_receipt.get("currency"))
    refreshed_proposals = _fetch_saved_accounting_entries(rid)
    refreshed_company = _fetch_company_by_id(refreshed_receipt.get("company_id"))
    refreshed = {
        "receipt": refreshed_receipt,
        "company": refreshed_company,
        "items": refreshed_items,
        "proposals": refreshed_proposals,
        "meta": {
            "items_source": refreshed_items_source,
            "items_count": len(refreshed_items),
            "proposals_count": len(refreshed_proposals),
        },
    }
    if refreshed_items_source != "database":
        refreshed["line_items"] = refreshed_items

    receipt_updated = bool(receipt_updated or company_updated or tags_updated)

    return (
        jsonify(
            {
                "id": rid,
                "receipt_updated": receipt_updated,
                "items_updated": items_updated,
                "proposals_updated": proposals_updated,
                "company_updated": company_updated,
                "tags_updated": tags_updated,
                "data": refreshed,
            }
        ),
        200,
    )


@receipts_bp.get("/receipts/monthly-summary")
def receipts_monthly_summary() -> Any:
    now = datetime.now(timezone.utc)
    data = {"month": now.strftime("%Y-%m"), "count": 0, "total": 0.0}
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                query_parts = [
                    "SELECT DATE_FORMAT(purchase_datetime, '%Y-%m') as ym, COUNT(1),",
                    "COALESCE(SUM(gross_amount),0)",
                    "FROM unified_files",
                    "WHERE purchase_datetime IS NOT NULL",
                    "GROUP BY ym ORDER BY ym DESC LIMIT 1",
                ]
                cur.execute(" ".join(query_parts))
                row = cur.fetchone()
                if row:
                    ym, cnt, tot = row
                    data = {"month": ym, "count": int(cnt), "total": float(tot)}
        except Exception:
            pass
    return jsonify(data), 200


@receipts_bp.get("/receipts/<rid>/line-items")
def get_line_items(rid: str) -> Any:
    p = _line_items_path(rid)
    if not p.exists():
        return jsonify({"id": rid, "line_items": []}), 200
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
    except Exception:
        data = []
    return jsonify({"id": rid, "line_items": data}), 200


@receipts_bp.put("/receipts/<rid>/line-items")
def put_line_items(rid: str) -> Any:
    payload = request.get_json(silent=True) or {}
    items = payload if isinstance(payload, list) else payload.get("line_items")
    if not isinstance(items, list):
        return jsonify({"error": "invalid"}), 400
    try:
        _line_items_path(rid).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify({"id": rid, "count": len(items)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@receipts_bp.get("/receipts/<rid>/image")
def get_receipt_image(rid: str):
    try:
        source = _find_receipt_image_path(rid)
        if source is None:
            return jsonify({"error": "no_image"}), 404

        quality = (request.args.get("quality") or "normal").lower()
        size_param = (request.args.get("size") or "original").lower()
        rotate_param = (request.args.get("rotate") or "auto").lower()

        if Image is None:
            return send_file(str(source))

        from io import BytesIO
        from PIL import ImageOps

        with Image.open(source) as img:  # type: ignore[attr-defined]
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            resample_attr = getattr(Image, "Resampling", None)
            resample_method = getattr(resample_attr, "LANCZOS", getattr(Image, "LANCZOS", Image.BICUBIC))  # type: ignore[arg-type]

            force_portrait = rotate_param == "portrait"
            force_landscape = rotate_param == "landscape"
            skip_resize = size_param in {"original", "full", "raw", "normal"}

            if force_portrait and img.width > img.height:
                img = img.rotate(-90, expand=True)
            elif force_landscape and img.height > img.width:
                img = img.rotate(90, expand=True)

            if not skip_resize:
                target_limit = None
                if size_param in {"preview", "thumbnail", "thumb"}:
                    target_limit = 720
                elif size_param.startswith("max:"):
                    try:
                        target_limit = int(size_param.split(":", 1)[1])
                    except (TypeError, ValueError):
                        target_limit = None
                else:
                    try:
                        parsed = int(size_param)
                        if parsed > 0:
                            target_limit = parsed
                    except (TypeError, ValueError):
                        target_limit = None

                if target_limit:
                    longest_side = max(img.size)
                    if longest_side > target_limit:
                        img.thumbnail((target_limit, target_limit), resample=resample_method)

            if rotate_param == "portrait" and img.width > img.height:
                img = img.rotate(-90, expand=True)

            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode not in {"RGB"}:
                img = img.convert("RGB")

            output = BytesIO()
            save_kwargs = {"optimize": True, "quality": 95}
            if quality == "high":
                save_kwargs.update({"quality": 100, "subsampling": 0, "optimize": False})
            elif quality == "low":
                save_kwargs["quality"] = 80

            img.save(output, "JPEG", **save_kwargs)
            output.seek(0)
            return send_file(output, mimetype="image/jpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Preview endpoint removed - using original images only
# @receipts_bp.get("/receipts/<rid>/preview")
# def get_receipt_preview(rid: str):
#     # This endpoint is deprecated - we now use original images only
#     return jsonify({"error": "preview_disabled"}), 404


@receipts_bp.get("/receipts/<rid>/ocr/boxes")
def get_ocr_boxes(rid: str) -> Any:
    try:
        return jsonify(_load_boxes(rid)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@receipts_bp.get("/receipts/<rid>/validation")
def get_receipt_validation(rid: str) -> Any:
    try:
        from models.receipts import Receipt
        from services.validation import validate_receipt
    except Exception:
        return jsonify({"error": "unavailable"}), 503
    data = None
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT u.id, c.name, u.purchase_datetime, u.gross_amount, u.net_amount, u.ai_confidence "
                        "FROM unified_files u "
                        "LEFT JOIN companies c ON c.id = u.company_id "
                        "WHERE u.id=%s"
                    ),
                    (rid,),
                )
                data = cur.fetchone()
        except Exception:
            data = None
    if not data:
        return jsonify({"error": "not_found"}), 404
    _id, merchant, pdt, gross, net, conf = data
    from datetime import datetime
    r = Receipt(
        id=_id,
        submitted_by=None,
        submitted_at=datetime.utcnow(),
        pages=[],
        tags=[],
        location_opt_in=False,
        merchant_name=merchant,
        orgnr=None,
        purchase_datetime=pdt,
        gross_amount=gross,
        net_amount=net,
        vat_breakdown={},
        company_card_flag=False,
        confidence_summary=conf,
    )
    report = validate_receipt(r)
    return jsonify(
        {
            "status": report.status,
            "messages": [
                {"message": m.message, "severity": m.severity, "field": m.field_ref}
                for m in report.messages
            ],
        }
    ), 200


@receipts_bp.get("/receipts/<rid>/accounting/proposal")
def get_receipt_accounting_proposal(rid: str) -> Any:
    saved = _fetch_saved_accounting_entries(rid)
    if saved:
        return jsonify({"entries": saved, "source": "saved"}), 200
    try:
        from models.receipts import Receipt
        from services.accounting import propose_accounting_entries
    except Exception:
        return jsonify({"error": "unavailable"}), 503

    data = None
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT u.id, c.name, c.orgnr, u.purchase_datetime, u.gross_amount, u.net_amount, u.ai_status, u.ai_confidence "
                        "FROM unified_files u "
                        "LEFT JOIN companies c ON c.id = u.company_id "
                        "WHERE u.id=%s"
                    ),
                    (rid,),
                )
                data = cur.fetchone()
        except Exception:
            data = None
    if not data:
        return jsonify({"entries": [], "source": "generated"}), 200
    (
        _id,
        merchant,
        orgnr,
        pdt,
        gross,
        net,
        ai_status,
        ai_confidence,
    ) = data
    r = Receipt(
        id=_id,
        submitted_by=None,
        submitted_at=datetime.utcnow(),
        pages=[],
        tags=[],
        location_opt_in=False,
        merchant_name=merchant,
        orgnr=orgnr,
        purchase_datetime=pdt,
        gross_amount=gross,
        net_amount=net,
        vat_breakdown={},
        company_card_flag=False,
        status=ai_status or None,
        confidence_summary=ai_confidence,
    )
    entries = [
        {
            "account": e.account_code,
            "debit": float(e.debit),
            "credit": float(e.credit),
            "vat_rate": float(e.vat_rate) if e.vat_rate is not None else None,
            "notes": e.notes,
        }
        for e in propose_accounting_entries(r)
    ]
    return jsonify({"entries": entries, "source": "generated"}), 200


@receipts_bp.put("/receipts/<rid>/accounting/proposal")
def put_receipt_accounting_proposal(rid: str) -> Any:
    payload = request.get_json(silent=True) or {}
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return jsonify({"error": "invalid_entries"}), 400

    normalised: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        account = (entry.get("account") or "").strip()
        if not account:
            continue
        try:
            debit = float(entry.get("debit") or 0)
            credit = float(entry.get("credit") or 0)
        except Exception:
            return jsonify({"error": "invalid_amount"}), 400
        vat_rate = entry.get("vat_rate")
        try:
            vat_value = float(vat_rate) if vat_rate not in (None, "", []) else None
        except Exception:
            vat_value = None
        normalised.append(
            {
                "account": account,
                "debit": debit,
                "credit": credit,
                "vat_rate": vat_value,
                "notes": (entry.get("notes") or "").strip() or None,
            }
        )

    if not normalised:
        return jsonify({"error": "no_valid_entries"}), 400

    saved = _save_accounting_entries(rid, normalised)
    if not saved:
        return jsonify({"error": "persist_failed"}), 500

    return jsonify({"ok": True, "entries": _fetch_saved_accounting_entries(rid)}), 200


@receipts_bp.post("/receipts/<rid>/approve")
def approve_receipt(rid: str) -> Any:
    ok = False
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE unified_files SET ai_status='completed', updated_at=NOW() WHERE id=%s",
                    (rid,),
                )
                ok = cur.rowcount > 0
        except Exception:
            ok = False
    return jsonify({"id": rid, "approved": ok}), 200


@receipts_bp.route("/receipts/<rid>", methods=["DELETE"])
def soft_delete_receipt(rid: str) -> Any:
    """Soft delete a receipt by setting deleted_at timestamp."""
    ok = False
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    "UPDATE unified_files SET deleted_at=NOW(), updated_at=NOW() WHERE id=%s AND deleted_at IS NULL",
                    (rid,),
                )
                ok = cur.rowcount > 0
        except Exception:
            logger.error(f"Error soft deleting receipt {rid}", exc_info=True)
            ok = False
    return jsonify({"id": rid, "deleted": ok}), 200


@receipts_bp.get("/receipts/<rid>/ai-history")
def get_ai_processing_history(rid: str) -> Any:
    """Get all AI processing history records for a specific file."""
    history: list[dict[str, Any]] = []
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id, file_id, job_type, status, created_at,
                        ai_stage_name, log_text, error_message, confidence,
                        processing_time_ms, provider, model_name
                    FROM ai_processing_history
                    WHERE file_id = %s
                    ORDER BY created_at ASC, id ASC
                    """,
                    (rid,),
                )
                for row in cur.fetchall() or []:
                    (
                        history_id, file_id, job_type, status, created_at,
                        ai_stage_name, log_text, error_message, confidence,
                        processing_time_ms, provider, model_name
                    ) = row
                    history.append({
                        "id": history_id,
                        "file_id": file_id,
                        "job_type": job_type,
                        "status": status,
                        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                        "ai_stage_name": ai_stage_name,
                        "log_text": log_text,
                        "error_message": error_message,
                        "confidence": float(confidence) if confidence is not None else None,
                        "processing_time_ms": processing_time_ms,
                        "provider": provider,
                        "model": model_name,
                    })
        except Exception as e:
            logger.error(f"Error fetching AI history for {rid}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            history = []
    return jsonify({"file_id": rid, "history": history}), 200


@receipts_bp.get("/receipts/<rid>/workflow-status")
def get_workflow_status(rid: str) -> Any:
    """Get the current status of each workflow phase for a file."""
    workflow_status = {
        "file_id": rid,
        "title": None,
        "datetime": None,
        "upload": "N/A",
        "filename": None,
        "pdf_convert": "N/A",
        "ocr": {"status": "pending", "data": None},
        "ai1": {"status": "pending", "data": None},
        "ai2": {"status": "pending", "data": None},
        "ai3": {"status": "pending", "data": None},
        "ai4": {"status": "pending", "data": None},
        "ai5": {"status": "pending", "data": None},
        "match": {"status": "pending", "data": None},
    }

    # Default to "pending" instead of "N/A" - will be updated based on detected_kind
    pdf_convert_status = "pending"

    if db_cursor is not None:
        try:
            # Get file metadata
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        u.id, u.original_filename, u.file_creation_timestamp,
                        u.submitted_by, c.name as company_name, u.created_at, u.ocr_raw, u.other_data
                    FROM unified_files u
                    LEFT JOIN companies c ON c.id = u.company_id
                    WHERE u.id = %s
                    """,
                    (rid,),
                )
                file_row = cur.fetchone()
                if file_row:
                    file_id, original_filename, file_creation_ts, submitted_by, company_name, created_at, ocr_raw, other_data = file_row

                    # Set title: company name if exists, otherwise file ID
                    workflow_status["title"] = company_name if company_name else f"ID: {file_id}"

                    # Set datetime: created_at timestamp
                    if created_at:
                        if hasattr(created_at, "strftime"):
                            workflow_status["datetime"] = created_at.strftime("%Y-%m-%d %H:%M")
                        else:
                            workflow_status["datetime"] = str(created_at)

                    # Set upload source
                    workflow_status["upload"] = "Upload" if submitted_by and "upload" in submitted_by.lower() else "FTP"
                    workflow_status["filename"] = original_filename

                    # Store OCR raw text for modal display
                    workflow_status["ocr_raw"] = ocr_raw

                    # Determine PDF conversion status based on detected file type
                    try:
                        other_data_dict = json.loads(other_data) if other_data else {}
                        detected_kind = other_data_dict.get("detected_kind")
                        source_pdf = other_data_dict.get("source_pdf")

                        if detected_kind == "pdf_page" or source_pdf:
                            # This is a PDF page - PDF conversion was successful
                            pdf_convert_status = "success"
                        elif detected_kind == "pdf":
                            # This is a PDF parent file - check if pages were generated
                            pdf_convert_status = "success" if other_data_dict.get("page_count", 0) > 0 else "pending"
                        elif detected_kind == "image":
                            # Regular image - no PDF conversion needed
                            pdf_convert_status = "N/A"
                        elif not detected_kind and original_filename:
                            # Fallback: If detected_kind is missing (e.g., FTP files), check filename
                            filename_lower = original_filename.lower()
                            if filename_lower.endswith(('.jpg', '.jpeg')) and '-page-' not in filename_lower:
                                # Regular JPG image file (not a PDF page) - no conversion needed
                                pdf_convert_status = "N/A"
                            elif filename_lower.endswith('.png') and '-page-' in filename_lower:
                                # This looks like a PDF page (e.g., "file-page-0001.png")
                                pdf_convert_status = "success"
                            elif filename_lower.endswith('.png') and '-page-' not in filename_lower:
                                # Regular PNG image - no conversion needed
                                pdf_convert_status = "N/A"
                            elif filename_lower.endswith('.pdf'):
                                # PDF parent file
                                pdf_convert_status = "pending"
                            # Otherwise keep default "pending" for unknown file types
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, try filename fallback
                        if original_filename:
                            filename_lower = original_filename.lower()
                            if filename_lower.endswith(('.jpg', '.jpeg', '.png')) and '-page-' not in filename_lower:
                                pdf_convert_status = "N/A"

            # Get AI processing history
            with db_cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        job_type, status, ai_stage_name, log_text, error_message,
                        confidence, processing_time_ms, provider, model_name, created_at
                    FROM ai_processing_history
                    WHERE file_id = %s
                    ORDER BY created_at DESC, id DESC
                    """,
                    (rid,),
                )

                # Process history records
                seen_stages = set()
                for row in cur.fetchall() or []:
                    (
                        job_type, status, ai_stage_name, log_text, error_message,
                        confidence, processing_time_ms, provider, model_name, created_at
                    ) = row

                    # Map job_type and ai_stage_name to workflow phases
                    stage_key = None
                    if job_type == "ocr":
                        stage_key = "ocr"
                    elif ai_stage_name:
                        # Map AI stage names to workflow phases
                        stage_lower = ai_stage_name.lower()
                        if "ai1" in stage_lower or "document" in stage_lower and "classif" in stage_lower:
                            stage_key = "ai1"
                        elif "ai2" in stage_lower or "expense" in stage_lower and "classif" in stage_lower:
                            stage_key = "ai2"
                        elif "ai3" in stage_lower or "extract" in stage_lower:
                            stage_key = "ai3"
                        elif "ai4" in stage_lower or "accounting" in stage_lower:
                            stage_key = "ai4"
                        elif "ai5" in stage_lower or ("credit" in stage_lower and "card" in stage_lower):
                            stage_key = "ai5"
                        elif "match" in stage_lower:
                            stage_key = "match"

                    # Only update if we haven't seen this stage yet (most recent first)
                    if stage_key and stage_key not in seen_stages:
                        seen_stages.add(stage_key)
                        workflow_status[stage_key] = {
                            "status": status,
                            "ai_stage_name": ai_stage_name,
                            "log_text": log_text,
                            "error_message": error_message,
                            "confidence": float(confidence) if confidence is not None else None,
                            "processing_time_ms": processing_time_ms,
                            "provider": provider,
                            "model": model_name,
                            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                        }

        except Exception as e:
            logger.error(f"Error fetching workflow status for {rid}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # Set pdf_convert status
    workflow_status["pdf_convert"] = pdf_convert_status

    return jsonify(workflow_status), 200
