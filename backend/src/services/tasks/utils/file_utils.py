from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from models.ai_processing import ReceiptItem
from models.receipts import AccountingEntry, Receipt, ReceiptStatus

from ..base import db_cursor, logger


def _update_file_status(file_id: str, status: str, confidence: float | None = None) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            if confidence is None:
                cur.execute(
                    "UPDATE unified_files SET ai_status=%s, updated_at=NOW() WHERE id=%s",
                    (status, file_id),
                )
            else:
                cur.execute(
                    "UPDATE unified_files SET ai_status=%s, ai_confidence=%s, updated_at=NOW() "
                    "WHERE id=%s",
                    (status, confidence, file_id),
                )
            return cur.rowcount > 0
    except Exception:
        return False


def _update_file_fields(
    file_id: str,
    ocr_raw: str | None = None,
) -> bool:
    """Update ONLY OCR raw text. All business data set by AI, not OCR."""
    if db_cursor is None:
        return False
    try:
        if ocr_raw is None:
            return False
        with db_cursor() as cur:
            cur.execute(
                "UPDATE unified_files SET ocr_raw=%s, updated_at=NOW() WHERE id=%s",
                (ocr_raw, file_id),
            )
            return cur.rowcount > 0
    except Exception:
        return False


def _enforce_file_metadata(
    file_id: str,
    *,
    file_type: str | None = None,
    workflow_type: str | None = None,
) -> None:
    """Best-effort update of file_type/workflow_type for a file record."""
    if db_cursor is None:
        return
    updates: list[str] = []
    params: list[Any] = []
    if file_type is not None:
        updates.append("file_type=%s")
        params.append(file_type)
    if workflow_type is not None:
        updates.append("workflow_type=%s")
        params.append(workflow_type)
    if not updates:
        return
    updates.append("updated_at=NOW()")
    params.append(file_id)
    try:
        with db_cursor() as cur:
            cur.execute(
                f"UPDATE unified_files SET {', '.join(updates)} WHERE id=%s",
                tuple(params),
            )
    except Exception:
        logger.warning("Failed to enforce metadata for file %s", file_id, exc_info=True)


def _load_unified_file_info(file_id: str) -> dict[str, Any] | None:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                (
                    "SELECT id, file_type, workflow_type, original_file_id, other_data, mime_type, "
                    "original_filename, original_file_name "
                    "FROM unified_files WHERE id=%s"
                ),
                (file_id,),
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    (
        uid,
        file_type,
        workflow_type,
        original_file_id,
        raw_other,
        mime_type,
        original_filename,
        original_file_name,
    ) = row
    other_data: dict[str, Any]
    if raw_other:
        try:
            other_data = json.loads(raw_other)
        except Exception:
            other_data = {}
    else:
        other_data = {}
    return {
        "id": uid,
        "file_type": file_type or "",
        "workflow_type": workflow_type or "",
        "original_file_id": original_file_id,
        "other_data": other_data,
        "mime_type": mime_type,
        "original_filename": original_filename,
        "original_file_name": original_file_name,
    }


def _load_receipt_model(file_id: str) -> Optional[Receipt]:
    """Load receipt model with company name from companies table, not merchant_name."""
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT uf.id, uf.submitted_by, uf.created_at, c.name AS company_name,
                       uf.orgnr, uf.purchase_datetime, uf.gross_amount, uf.net_amount,
                       uf.ai_confidence
                FROM unified_files uf
                LEFT JOIN companies c ON uf.company_id = c.id
                WHERE uf.id = %s
                """,
                (file_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        (
            rid,
            submitted_by,
            created_at,
            company_name,
            orgnr,
            purchase_dt,
            gross,
            net,
            ai_conf,
        ) = row

        tags: List[str] = []
        try:
            with db_cursor() as cur:
                cur.execute("SELECT tag FROM file_tags WHERE file_id=%s", (file_id,))
                tags = [tag for (tag,) in cur.fetchall() or []]
        except Exception:
            tags = []

        submitted_at = created_at or datetime.now(timezone.utc)
        if isinstance(submitted_at, datetime):
            if submitted_at.tzinfo is None:
                submitted_at = submitted_at.replace(tzinfo=timezone.utc)
        else:
            submitted_at = datetime.now(timezone.utc)

        if isinstance(purchase_dt, datetime):
            purchase_at: Optional[datetime] = (
                purchase_dt if purchase_dt.tzinfo is not None else purchase_dt.replace(tzinfo=timezone.utc)
            )
        elif isinstance(purchase_dt, str):
            try:
                parsed = datetime.fromisoformat(purchase_dt)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                purchase_at = parsed
            except Exception:
                purchase_at = None
        else:
            purchase_at = None

        gross_dec = Decimal(str(gross)) if gross is not None else None
        net_dec = Decimal(str(net)) if net is not None else None
        confidence = float(ai_conf) if ai_conf is not None else None

        return Receipt(
            id=rid,
            submitted_by=submitted_by,
            submitted_at=submitted_at,
            merchant_name=company_name,  # From companies table via JOIN
            orgnr=orgnr,
            purchase_datetime=purchase_at,
            gross_amount=gross_dec,
            net_amount=net_dec,
            vat_breakdown={},
            tags=tags,
            location_opt_in=False,
            company_card_flag=False,
            status=ReceiptStatus.PROCESSING,
            confidence_summary=confidence,
        )
    except Exception:
        return None


def _get_file_type(file_id: str) -> Optional[str]:
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute("SELECT file_type FROM unified_files WHERE id=%s", (file_id,))
            row = cur.fetchone()
            if row:
                (file_type,) = row
                return file_type
    except Exception:
        return None
    return None


def _collect_text_hints(file_id: str) -> str:
    base = Path(os.getenv("STORAGE_DIR", "/data/storage"))
    hints: List[str] = []
    line_items_path = base / "line_items" / f"{file_id}.json"
    if line_items_path.exists():
        try:
            data = json.loads(line_items_path.read_text(encoding="utf-8"))
        except Exception:
            data = None
        if data is not None:
            def _consume(value: Any) -> None:
                if isinstance(value, str) and value.strip():
                    hints.append(value.strip().lower())
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for v in item.values():
                            _consume(v)
                    else:
                        _consume(item)
            elif isinstance(data, dict):
                for v in data.values():
                    _consume(v)
            else:
                _consume(data)
    return " ".join(hints)


def _load_ai_context(file_id: str):
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
                "SELECT ocr_raw, file_type, expense_type FROM unified_files WHERE id=%s",
                (file_id,),
            )
            return cur.fetchone()
    except Exception:
        return None


def _load_accounting_inputs(file_id: str):
    if db_cursor is None:
        return None
    try:
        with db_cursor() as cur:
            cur.execute(
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
            return cur.fetchone()
    except Exception:
        return None


def _load_receipt_items(file_id: str):
    """Load receipt items with their IDs from the database."""
    if db_cursor is None:
        return []
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, main_id, article_id, name, number,
                       item_price_ex_vat, item_price_inc_vat,
                       item_total_price_ex_vat, item_total_price_inc_vat,
                       currency, vat, vat_percentage
                FROM receipt_items
                WHERE main_id = %s
                """,
                (file_id,),
            )
            rows = cur.fetchall()
            items = []
            for row in rows:
                items.append(ReceiptItem(
                    id=row[0],
                    main_id=row[1],
                    article_id=row[2] or "",
                    name=row[3],
                    number=row[4],
                    item_price_ex_vat=Decimal(str(row[5] or 0)),
                    item_price_inc_vat=Decimal(str(row[6] or 0)),
                    item_total_price_ex_vat=Decimal(str(row[7] or 0)),
                    item_total_price_inc_vat=Decimal(str(row[8] or 0)),
                    currency=row[9] or "SEK",
                    vat=Decimal(str(row[10] or 0)),
                    vat_percentage=Decimal(str(row[11] or 0)),
                ))
            return items
    except Exception:
        return []


def _save_accounting_entries(file_id: str, entries: List[AccountingEntry]) -> bool:
    if db_cursor is None:
        return False
    try:
        with db_cursor() as cur:
            cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (file_id,))
            for entry in entries:
                cur.execute(
                    (
                        "INSERT INTO ai_accounting_proposals "
                        "(receipt_id, item_id, account_code, debit, credit, vat_rate, notes) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    ),
                    (
                        file_id,
                        entry.item_id if hasattr(entry, 'item_id') and entry.item_id else None,
                        entry.account_code,
                        float(entry.debit or 0),
                        float(entry.credit or 0),
                        (float(entry.vat_rate) if entry.vat_rate is not None else None),
                        (entry.notes[:255] if entry.notes else None),
                    ),
                )
        return True
    except Exception:
        return False


__all__ = [
    "_update_file_status",
    "_update_file_fields",
    "_enforce_file_metadata",
    "_load_unified_file_info",
    "_load_receipt_model",
    "_get_file_type",
    "_collect_text_hints",
    "_load_ai_context",
    "_load_accounting_inputs",
    "_load_receipt_items",
    "_save_accounting_entries",
]
