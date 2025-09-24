from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from flask import Blueprint, Response, request

try:
    from services.db.connection import db_cursor  # type: ignore
except Exception:  # pragma: no cover - allow running without DB
    db_cursor = None  # type: ignore

from services.storage import FileStorage

export_bp = Blueprint("export", __name__)
_jobs: Dict[str, dict] = {}


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None


def _fetch_proposals(period_from: Optional[date], period_to: Optional[date]) -> Tuple[List[dict], Dict[str, str]]:
    if db_cursor is None:
        return [], {}

    where: List[str] = ["uf.ai_status = 'completed'"]
    params: List[Any] = []
    if period_from:
        where.append("DATE(COALESCE(uf.purchase_datetime, uf.created_at)) >= %s")
        params.append(period_from.isoformat())
    if period_to:
        where.append("DATE(COALESCE(uf.purchase_datetime, uf.created_at)) <= %s")
        params.append(period_to.isoformat())

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT
            uf.id,
            COALESCE(uf.purchase_datetime, uf.created_at) AS dt,
            COALESCE(uf.merchant_name, '') AS merchant,
            ap.account_code,
            ap.debit,
            ap.credit,
            ap.notes
        FROM ai_accounting_proposals ap
        JOIN unified_files uf ON uf.id = ap.receipt_id
        WHERE {where_sql}
        ORDER BY dt ASC, uf.id ASC, ap.id ASC
    """

    grouped: Dict[str, dict] = {}
    account_labels: Dict[str, str] = {}

    try:
        with db_cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall() or []
    except Exception:
        return [], {}

    for rid, dt, merchant, account, debit, credit, notes in rows:
        entry_amount = Decimal(str(debit or 0)) - Decimal(str(credit or 0))
        if rid not in grouped:
            ver_date = dt.date() if hasattr(dt, "date") else datetime.utcnow().date()
            grouped[rid] = {
                "date": ver_date,
                "text": merchant or f"Receipt {rid}",
                "entries": [],
            }
        grouped[rid]["entries"].append(
            {
                "account": account,
                "amount": entry_amount,
                "notes": notes or "",
            }
        )
        if account not in account_labels:
            label = (notes or "").strip()
            account_labels[account] = label or f"Account {account}"
    verifications = list(grouped.values())
    verifications.sort(key=lambda item: (item["date"], item["text"]))
    return verifications, account_labels


def _format_amount(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal("0.01"))
    return f"{quantized:.2f}"


def _sanitize_text(value: str) -> str:
    return value.replace('"', "'").strip() or "Receipt"



def _build_sie(verifications: List[dict], account_labels: Dict[str, str], period_from: Optional[date], period_to: Optional[date]) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    lines = [
        "#FLAGGA 0",
        "#FORMAT PC8",
        '#PROGRAM "Mind Admin" "1.0"',
        f"#GEN {today}",
        "#SIETYP 4",
    ]

    if period_from or period_to:
        comment_from = period_from.isoformat() if period_from else "(start)"
        comment_to = period_to.isoformat() if period_to else "(end)"
        lines.append(f"; Export period {comment_from} to {comment_to}")

    for account in sorted(account_labels.keys()):
        label = _sanitize_text(account_labels[account])
        lines.append(f'#KONTO {account} "{label}"')

    if not verifications:
        lines.append("; No verifications available for selected period")
        return "\n".join(lines) + "\n"

    for index, ver in enumerate(verifications, start=1):
        ver_date = ver["date"].strftime("%Y%m%d") if isinstance(ver["date"], date) else today
        ver_text = _sanitize_text(ver["text"])
        ver_nr = f"{index:04d}"
        lines.append(f'#VER "A" "{ver_nr}" {ver_date} "{ver_text}"')
        for entry in ver["entries"]:
            amount = entry.get("amount", Decimal("0"))
            if not isinstance(amount, Decimal):
                amount = Decimal(str(amount or 0))
            if amount == 0:
                continue
            formatted_amount = _format_amount(amount)
            entry_text = _sanitize_text(entry.get("notes") or ver_text)
            lines.append(f'#TRANS {entry["account"]} {{}} {formatted_amount} "{entry_text}"')

    return "\n".join(lines) + "\n"


def _build_filename(period_from: Optional[date], period_to: Optional[date]) -> str:
    if period_from and period_to:
        return f"export_{period_from.isoformat()}_{period_to.isoformat()}.sie"
    if period_from:
        return f"export_{period_from.isoformat()}_end.sie"
    if period_to:
        return f"export_start_{period_to.isoformat()}.sie"
    return "export_all.sie"


def _collect_company_card_data(statement_id: str) -> Tuple[Optional[dict], List[Tuple[str, bytes]], Optional[str]]:
    if db_cursor is None:
        return None, [], "db_unavailable"

    statement_sql = (
        "SELECT id, period_start, period_end, status, uploaded_at FROM invoice_documents "
        "WHERE id=%s AND invoice_type='company_card'"
    )

    lines_sql = (
        "SELECT id, transaction_date, amount, merchant_name, description, matched_file_id, match_status "
        "FROM invoice_lines WHERE invoice_id=%s ORDER BY transaction_date ASC, id ASC"
    )

    receipt_map: Dict[str, dict] = {}
    try:
        with db_cursor() as cur:
            cur.execute(statement_sql, (statement_id,))
            row = cur.fetchone()
            if not row:
                return None, [], "not_found"
            sid, p_start, p_end, status, uploaded_at = row
            statement_info = {
                "id": sid,
                "period_start": p_start.isoformat() if hasattr(p_start, "isoformat") and p_start else None,
                "period_end": p_end.isoformat() if hasattr(p_end, "isoformat") and p_end else None,
                "status": status,
                "uploaded_at": uploaded_at.isoformat() if hasattr(uploaded_at, "isoformat") else str(uploaded_at),
            }

            cur.execute(lines_sql, (statement_id,))
            line_rows = cur.fetchall() or []
    except Exception:
        return None, [], "db_error"

    lines: List[dict] = []
    receipt_ids: List[str] = []
    for (lid, tx, amount, merchant_name, description, matched_file_id, match_status) in line_rows:
        if matched_file_id:
            receipt_ids.append(matched_file_id)
        lines.append(
            {
                "id": int(lid),
                "transaction_date": tx.isoformat() if hasattr(tx, "isoformat") else tx,
                "amount": float(amount) if amount is not None else None,
                "merchant_name": merchant_name,
                "description": description,
                "matched_file_id": matched_file_id,
                "match_status": match_status,
            }
        )

    if receipt_ids:
        placeholders = ",".join(["%s"] * len(receipt_ids))
        receipt_sql = (
            "SELECT id, merchant_name, purchase_datetime, gross_amount, net_amount, ai_status, submitted_by "
            f"FROM unified_files WHERE id IN ({placeholders})"
        )
        try:
            with db_cursor() as cur:
                cur.execute(receipt_sql, tuple(receipt_ids))
                for rid, merchant, purchase_dt, gross, net, ai_status, submitted_by in cur.fetchall() or []:
                    receipt_map[rid] = {
                        "id": rid,
                        "merchant_name": merchant,
                        "purchase_datetime": purchase_dt.isoformat() if hasattr(purchase_dt, "isoformat") else purchase_dt,
                        "gross_amount": float(gross) if gross is not None else None,
                        "net_amount": float(net) if net is not None else None,
                        "ai_status": ai_status,
                        "submitted_by": submitted_by,
                        "files": [],
                    }
        except Exception:
            return None, [], "db_error"

    storage = FileStorage(os.getenv("STORAGE_DIR", "/data/storage"))
    assets: List[Tuple[str, bytes]] = []
    for rid in receipt_map.keys():
        try:
            files = storage.list(rid)
        except Exception:
            files = []
        for fname in files:
            try:
                data = storage.load(rid, fname)
                zip_path = f"receipts/{rid}/{fname}"
                assets.append((zip_path, data))
                receipt_map[rid]["files"].append(zip_path)
            except Exception:
                continue

    bundle = {
        "statement": statement_info,
        "lines": [],
    }

    for line in lines:
        rid = line.get("matched_file_id")
        matched_receipt = receipt_map.get(rid) if rid else None
        bundle["lines"].append(
            {
                **line,
                "matched_receipt": matched_receipt,
            }
        )

    return bundle, assets, None


@export_bp.get("/export/sie")
def export_sie() -> Any:
    period_from = _parse_date(request.args.get("from"))
    period_to = _parse_date(request.args.get("to"))
    if period_from and period_to and period_from > period_to:
        period_from, period_to = period_to, period_from

    verifications, account_labels = _fetch_proposals(period_from, period_to)
    sie_content = _build_sie(verifications, account_labels, period_from, period_to)

    job_id = datetime.utcnow().strftime("sie-%Y%m%d%H%M%S%f")
    _jobs[job_id] = {
        "status": "done",
        "from": period_from.isoformat() if period_from else None,
        "to": period_to.isoformat() if period_to else None,
        "verifications": len(verifications),
    }

    filename = _build_filename(period_from, period_to)
    resp = Response(sie_content, status=200, mimetype="text/plain; charset=utf-8")
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    resp.headers["X-Export-Job-Id"] = job_id
    return resp


@export_bp.get("/export/company-card")
def export_company_card() -> Any:
    statement_id = request.args.get("statement_id")
    if not statement_id or not statement_id.strip():
        return Response("statement_id is required", status=400, mimetype="text/plain; charset=utf-8")

    bundle, assets, error = _collect_company_card_data(statement_id.strip())
    if error == "db_unavailable":
        return Response("database unavailable", status=503, mimetype="text/plain; charset=utf-8")
    if error == "not_found":
        return Response("statement not found", status=404, mimetype="text/plain; charset=utf-8")
    if error == "db_error" or bundle is None:
        return Response("failed to build export", status=500, mimetype="text/plain; charset=utf-8")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("statement.json", json.dumps(bundle, ensure_ascii=False, indent=2))
        for path, data in assets:
            zf.writestr(path, data)

    job_id = datetime.utcnow().strftime("cc-%Y%m%d%H%M%S%f")
    _jobs[job_id] = {
        "status": "done",
        "statement_id": statement_id,
        "attachments": len(assets),
    }

    buffer.seek(0)
    filename = f"company_card_{statement_id}.zip"
    resp = Response(buffer.getvalue(), status=200, mimetype="application/zip")
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    resp.headers["X-Export-Job-Id"] = job_id
    return resp
