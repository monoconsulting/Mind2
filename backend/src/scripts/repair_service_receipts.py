from __future__ import annotations

import argparse
import json
from decimal import Decimal
from typing import Any, Optional

from services.db.connection import db_cursor
from services.receipt_fallback_rules import is_service_receipt_candidate


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic service receipt fallback for missing items/VAT.")
    parser.add_argument("--apply", action="store_true", help="Apply updates (default is dry-run).")
    parser.add_argument("--file-id", default=None, help="Repair a single file_id only.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of records to inspect.")
    return parser.parse_args()


def _extract_text(ocr_raw: Optional[str], other_data_raw: Optional[str]) -> str:
    if other_data_raw:
        try:
            payload = json.loads(other_data_raw)
            for key in ("combined_ocr_text", "parsed_text", "ocr_text"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        except Exception:
            pass
    return ocr_raw or ""


def _load_targets(file_id: Optional[str], limit: Optional[int]) -> list[dict[str, Any]]:
    where = [
        "uf.file_type = 'receipt'",
        "COALESCE(NULLIF(uf.currency, ''), 'SEK') = 'SEK'",
        "(uf.gross_amount_original IS NOT NULL OR uf.gross_amount IS NOT NULL OR uf.gross_amount_sek IS NOT NULL)",
    ]
    params: list[Any] = []
    if file_id:
        where.append("uf.id = %s")
        params.append(file_id)
    limit_clause = ""
    if limit:
        limit_clause = "LIMIT %s"
        params.append(int(limit))

    sql = f"""
        SELECT
            uf.id,
            uf.currency,
            uf.ocr_raw,
            uf.other_data,
            uf.gross_amount_original,
            uf.net_amount_original,
            uf.gross_amount_sek,
            uf.net_amount_sek,
            uf.total_vat_25,
            uf.total_vat_12,
            uf.total_vat_6,
            (
                SELECT COUNT(*)
                FROM receipt_items ri
                WHERE ri.main_id = uf.id
            ) AS item_count
        FROM unified_files uf
        WHERE {' AND '.join(where)}
        ORDER BY uf.created_at DESC
        {limit_clause}
    """
    with db_cursor(dictionary=True) as cur:
        cur.execute(sql, tuple(params) if params else None)
        return cur.fetchall() or []


def main() -> int:
    args = _parse_args()
    rows = _load_targets(args.file_id, args.limit)
    if not rows:
        print("No receipt records found for service receipt fallback.")
        return 0

    mode = "APPLY" if args.apply else "DRY-RUN"
    updated = 0
    skipped = 0

    with db_cursor() as cur:
        for row in rows:
            file_id = row.get("id")
            text = _extract_text(row.get("ocr_raw"), row.get("other_data")).lower()
            if not is_service_receipt_candidate(text):
                skipped += 1
                continue

            if row.get("item_count", 0):
                skipped += 1
                continue

            gross_base = row.get("gross_amount_original") or row.get("gross_amount_sek")
            if gross_base is None:
                skipped += 1
                continue

            net_original = row.get("net_amount_original")
            net_sek = row.get("net_amount_sek")
            gross_original = row.get("gross_amount_original") or gross_base
            gross_sek = row.get("gross_amount_sek") or gross_base

            if net_original is None:
                net_original = gross_base
            if net_sek is None:
                net_sek = net_original

            total_vat_25 = row.get("total_vat_25")
            total_vat_12 = row.get("total_vat_12")
            total_vat_6 = row.get("total_vat_6")
            if total_vat_25 is None and total_vat_12 is None and total_vat_6 is None:
                total_vat_25 = Decimal("0.00")
                total_vat_12 = Decimal("0.00")
                total_vat_6 = Decimal("0.00")

            other_data_payload: dict[str, Any] = {}
            if row.get("other_data"):
                try:
                    other_data_payload = json.loads(row.get("other_data"))
                except Exception:
                    other_data_payload = {"raw_other_data": row.get("other_data")}
            other_data_payload["vat_exempt_reason"] = "healthcare_service_receipt"
            other_data_payload["deterministic_receipt_items"] = "service_receipt_fallback"
            other_data_json = json.dumps(other_data_payload, ensure_ascii=False)

            if args.apply:
                cur.execute(
                    """
                    UPDATE unified_files
                       SET gross_amount_original=%s,
                           net_amount_original=%s,
                           gross_amount_sek=%s,
                           net_amount_sek=%s,
                           total_vat_25=%s,
                           total_vat_12=%s,
                           total_vat_6=%s,
                           other_data=%s,
                           updated_at=NOW()
                     WHERE id=%s
                    """,
                    (
                        gross_original,
                        net_original,
                        gross_sek,
                        net_sek,
                        total_vat_25,
                        total_vat_12,
                        total_vat_6,
                        other_data_json,
                        file_id,
                    ),
                )
                cur.execute(
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
                        "",
                        "Service",
                        1,
                        net_original,
                        gross_original,
                        net_original,
                        gross_original,
                        "SEK",
                        Decimal("0.00"),
                        Decimal("0.00"),
                    ),
                )

            updated += 1
            print(f"{mode} {file_id}: inserted 1 service receipt item + VAT-exempt totals")

    print(f"[{mode}] updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
