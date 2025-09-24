from __future__ import annotations

from typing import Any, Iterable, List, Optional, Tuple

from .connection import db_cursor


def set_ai_status(file_id: str, status: str) -> bool:
    with db_cursor() as cur:
        cur.execute(
            "UPDATE unified_files SET ai_status=%s, updated_at=NOW() WHERE id=%s",
            (status, file_id),
        )
        return cur.rowcount > 0


def list_unprocessed(limit: int = 50) -> List[str]:
    with db_cursor() as cur:
        cur.execute(
            (
                "SELECT id FROM unified_files "
                "WHERE ai_status IS NULL OR ai_status IN ('new','queued') "
                "ORDER BY created_at DESC LIMIT %s"
            ),
            (limit,),
        )
        return [row[0] for row in cur.fetchall() or []]


def get_receipt(file_id: str) -> Optional[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            (
                "SELECT id, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence "
                "FROM unified_files WHERE id=%s"
            ),
            (file_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            _id,
            merchant,
            orgnr,
            pdt,
            gross,
            net,
            ai_status,
            ai_confidence,
        ) = row
        return {
            "id": _id,
            "merchant": merchant,
            "orgnr": orgnr,
            "purchase_datetime": (pdt.isoformat() if hasattr(pdt, "isoformat") else pdt),
            "gross_amount": (float(gross) if gross is not None else None),
            "net_amount": (float(net) if net is not None else None),
            "ai_status": ai_status,
            "ai_confidence": ai_confidence,
        }
