from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from services.db.connection import db_cursor
from services.doc_type_rules import (
    detect_deterministic_doc_type,
    has_invoice_signature,
    has_receipt_evidence,
    has_terminal_slip_signature,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic document-type repair for misclassified receipts.")
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
    where = ["uf.ocr_raw IS NOT NULL", "uf.ocr_raw <> ''"]
    params: list[Any] = []
    if file_id:
        where.append("uf.id = %s")
        params.append(file_id)
    else:
        where.append("uf.file_type = 'receipt'")
    limit_clause = ""
    if limit:
        limit_clause = "LIMIT %s"
        params.append(int(limit))

    sql = f"""
        SELECT
            uf.id,
            uf.file_type,
            uf.ocr_raw,
            uf.other_data,
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


def _load_workflow_types() -> set[str]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT DISTINCT workflow_type FROM unified_files WHERE workflow_type IS NOT NULL"
        )
        return {str(row[0]) for row in (cur.fetchall() or []) if row[0]}


def _is_terminal_slip_candidate(text: str, row: dict[str, Any]) -> bool:
    if not has_terminal_slip_signature(text):
        return False
    if has_receipt_evidence(text):
        return False
    if row.get("item_count", 0):
        return False
    if any(row.get(col) is not None for col in ("total_vat_25", "total_vat_12", "total_vat_6")):
        return False
    return True


def main() -> int:
    args = _parse_args()
    rows = _load_targets(args.file_id, args.limit)
    if not rows:
        print("No receipt records found for deterministic repair.")
        return 0

    workflow_types = _load_workflow_types()
    invoice_workflow_type = "invoice" if "invoice" in workflow_types else None
    other_workflow_type = "other" if "other" in workflow_types else None

    mode = "APPLY" if args.apply else "DRY-RUN"
    updated = 0
    skipped = 0

    with db_cursor() as cur:
        for row in rows:
            file_id = row.get("id")
            text = _extract_text(row.get("ocr_raw"), row.get("other_data"))
            doc_type, reason = detect_deterministic_doc_type(text)
            if doc_type is None:
                skipped += 1
                continue

            if doc_type == "other":
                if not _is_terminal_slip_candidate(text, row):
                    skipped += 1
                    continue
            elif doc_type == "invoice":
                if not has_invoice_signature(text):
                    skipped += 1
                    continue
                new_workflow_type = invoice_workflow_type
            else:
                new_workflow_type = None

            if doc_type == "other":
                new_workflow_type = other_workflow_type

            if args.apply:
                cur.execute(
                    "UPDATE unified_files SET file_type=%s, workflow_type=%s, updated_at=NOW() WHERE id=%s",
                    (doc_type, new_workflow_type, file_id),
                )
            updated += 1
            wf_suffix = f", workflow_type={new_workflow_type}" if doc_type != "receipt" else ""
            print(f"{mode} {file_id}: file_type=receipt -> {doc_type}{wf_suffix} ({reason})")

    print(f"[{mode}] updated={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
