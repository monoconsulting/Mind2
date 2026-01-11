from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any

from services.db.connection import db_cursor
from services.tasks.file_management_tasks import (
    _load_accounting_inputs,
    _load_receipt_items,
    _move_to_manual_review,
)
from services.box_enrichment import run_box_enrichment
from services.ai_service import AccountingProposalValidationError
from services.ai_logging import log_ai_call
from api.ai_processing import classify_accounting_internal
from models.ai_processing import AccountingClassificationRequest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill AI4 accounting proposals for receipts without proposals.")
    parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run).")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of receipts to process.")
    parser.add_argument("--file-id", default=None, help="Process a single file_id only.")
    return parser.parse_args()


def _load_targets(limit: int | None, file_id: str | None) -> list[dict[str, Any]]:
    select_columns = ["uf.id"]
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'unified_files'
              AND COLUMN_NAME IN ('document_type', 'expense_type')
            """
        )
        existing = {row[0] for row in (cur.fetchall() or [])}

    if "document_type" in existing:
        select_columns.append("uf.document_type")
    else:
        select_columns.append("NULL AS document_type")

    if "expense_type" in existing:
        select_columns.append("uf.expense_type")
    else:
        select_columns.append("NULL AS expense_type")

    where = ["uf.file_type = 'receipt'", "uf.ai_status IN ('completed', 'manual_review')", "ap.id IS NULL"]
    params: list[Any] = []
    if file_id:
        where.append("uf.id = %s")
        params.append(file_id)

    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT %s"
        params.append(int(limit))

    sql = f"""
    SELECT {', '.join(select_columns)}
    FROM unified_files uf
    LEFT JOIN ai_accounting_proposals ap ON ap.receipt_id = uf.id
    WHERE {' AND '.join(where)}
    ORDER BY uf.created_at DESC
    {limit_clause}
    """

    with db_cursor(dictionary=True) as cur:
        cur.execute(sql, tuple(params) if params else None)
        return cur.fetchall() or []


def _run_ai4_for_file(file_id: str, document_type: str | None, expense_type: str | None, *, apply: bool) -> str:
    accounting = _load_accounting_inputs(file_id)
    if not accounting:
        return "skipped:no_inputs"

    if accounting.get("ai4_ready") is False:
        reason = str(accounting.get("reason") or "missing totals for accounting")
        if apply:
            _move_to_manual_review(file_id, reason)
        return f"skipped:needs_review:{reason}"

    receipt_items_for_ai4 = _load_receipt_items(file_id)
    vendor_name = accounting.get("vendor_name") or ""

    if not apply:
        return "dry_run:ready"

    try:
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
        _move_to_manual_review(file_id, error_msg)
        log_ai_call(
            file_id=file_id,
            job="ai4",
            status="error",
            ai_stage_name="AI4-AccountingClassification",
            log_text="Needs review: AI4 validation failed",
            error_message=error_msg,
        )
        return f"failed:{error_msg}"

    stats = run_box_enrichment(file_id)
    if not stats.get("success"):
        return f"success:ai7_failed:{stats.get('error', 'unknown')}"
    return "success"


def main() -> int:
    args = _parse_args()

    targets = _load_targets(args.limit, args.file_id)
    if not targets:
        print("No receipts found for AI4 backfill.")
        return 0

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] receipts_to_process={len(targets)}")

    stats: dict[str, int] = {
        "success": 0,
        "dry_run": 0,
        "skipped": 0,
        "failed": 0,
    }

    for row in targets:
        file_id = row.get("id")
        document_type = row.get("document_type")
        expense_type = row.get("expense_type")
        result = _run_ai4_for_file(str(file_id), document_type, expense_type, apply=bool(args.apply))

        if result.startswith("success"):
            stats["success"] += 1
        elif result.startswith("dry_run"):
            stats["dry_run"] += 1
        elif result.startswith("skipped"):
            stats["skipped"] += 1
        else:
            stats["failed"] += 1

        print(f"{file_id}: {result}")

    print(
        f"[{mode}] success={stats['success']} dry_run={stats['dry_run']} "
        f"skipped={stats['skipped']} failed={stats['failed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
