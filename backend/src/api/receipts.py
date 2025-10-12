from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

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
except Exception:  # pragma: no cover - fallback for early scaffolding
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
                    "SELECT account_code, debit, credit, vat_rate, notes FROM ai_accounting_proposals "
                    "WHERE receipt_id=%s ORDER BY id ASC"
                ),
                (rid,),
            )
            for account, debit, credit, vat_rate, notes in cur.fetchall() or []:
                entries.append(
                    {
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


@receipts_bp.get("/receipts")
def list_receipts() -> Any:
    # Optional filters
    q_status = request.args.get("status")
    q_merchant = request.args.get("merchant")
    q_orgnr = request.args.get("orgnr")
    q_tags = request.args.get("tags")
    q_from = request.args.get("from")
    q_to = request.args.get("to")

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
            where: list[str] = []
            params: list[Any] = []
            if q_status:
                where.append("ai_status = %s")
                params.append(q_status)
            if q_merchant:
                where.append("merchant_name LIKE %s")
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

            where_sql = ("WHERE " + " AND ".join(where)) if where else ""

            # Count
            with db_cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(1) FROM unified_files {where_sql}",
                    tuple(params),
                )
                (total,) = cur.fetchone() or (0,)

            # Page
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT u.id, u.original_filename, u.merchant_name, u.purchase_datetime, u.net_amount, u.gross_amount, u.ai_status, u.submitted_by, "
                        "u.file_creation_timestamp, fl.lat, fl.lon, fl.acc, "
                        "COALESCE(GROUP_CONCAT(t.tag), '') as tags "
                        "FROM unified_files u "
                        "LEFT JOIN file_tags t ON t.file_id=u.id "
                        "LEFT JOIN file_locations fl ON fl.file_id=u.id "
                        + where_sql
                        + " GROUP BY u.id, u.file_creation_timestamp, fl.lat, fl.lon, fl.acc ORDER BY u.created_at DESC LIMIT %s OFFSET %s"
                    ),
                    tuple(params + [page_size, offset]),
                )
                for rid, fname, merchant, pdt, net, gross, status, submitted_by, file_creation_ts, lat, lon, acc, tag_csv in cur.fetchall():
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
                            "submitted_by": submitted_by,
                            "line_item_count": line_items,
                            "tags": [t for t in (tag_csv or "").split(",") if t],
                        }
                    )
        except Exception as e:
            # Fallback to empty but still 200
            items = []
            total = 0
    meta["total"] = int(total)
    meta["items"] = len(items)
    return jsonify({"items": items, "meta": meta}), 200


@receipts_bp.get("/receipts/<rid>")
def get_receipt(rid: str) -> Any:
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute(
                    (
                        "SELECT id, merchant_name, orgnr, purchase_datetime, gross_amount, "
                        "net_amount, ai_status, ai_confidence, ocr_raw FROM unified_files WHERE id=%s"
                    ),
                    (rid,),
                )
                row = cur.fetchone()
                if row:
                    (
                        _id,
                        merchant,
                        orgnr,
                        pdt,
                        gross,
                        net,
                        ai_status,
                        ai_confidence,
                        ocr_raw,
                    ) = row
                    return (
                        jsonify(
                            {
                                "id": _id,
                                "merchant": merchant,
                                "orgnr": orgnr,
                                "purchase_datetime": (
                                    pdt.isoformat() if hasattr(pdt, "isoformat") else pdt
                                ),
                                "gross_amount": (float(gross) if gross is not None else None),
                                "net_amount": (float(net) if net is not None else None),
                                "ai_status": ai_status,
                                "ai_confidence": ai_confidence,
                                "ocr_raw": ocr_raw,
                            }
                        ),
                        200,
                    )
        except Exception as e:
            logger.error(f"Error in get_receipt: {e}")
            pass
    # Placeholder minimal response if not found/DB error
    return jsonify({"id": rid, "status": "Placeholder"}), 200


@receipts_bp.route("/receipts/<rid>", methods=["PUT", "PATCH"])
def update_receipt(rid: str) -> Any:
    payload = request.get_json(silent=True) or {}
    updated = False
    # Shallow validation/coercion
    editable = {}
    if "merchant_name" in payload and isinstance(payload["merchant_name"], str):
        editable["merchant_name"] = payload["merchant_name"][:255]
    if "orgnr" in payload and isinstance(payload["orgnr"], str):
        editable["orgnr"] = payload["orgnr"][:32]
    for num_key in ("gross_amount", "net_amount"):
        if num_key in payload:
            try:
                editable[num_key] = float(payload[num_key])
            except Exception:
                # ignore invalid numeric
                pass
    # Allow status updates
    if "status" in payload and isinstance(payload["status"], str):
        editable["ai_status"] = payload["status"][:32]
    if "ai_status" in payload and isinstance(payload["ai_status"], str):
        editable["ai_status"] = payload["ai_status"][:32]
    # Purchase date (iso date string) optional
    if "purchase_date" in payload and isinstance(payload["purchase_date"], str):
        try:
            editable["purchase_datetime"] = payload["purchase_date"]  # store as string; DB may coerce
        except Exception:
            pass

    if db_cursor is not None and editable:
        fields = [f"{k}=%s" for k in editable.keys()]
        values: list[Any] = list(editable.values())
        values.append(rid)
        try:
            with db_cursor() as cur:
                set_clause = ", ".join(fields)
                sql = "UPDATE unified_files SET " + set_clause + ", updated_at=NOW() WHERE id=%s"
                cur.execute(sql, tuple(values))
                updated = cur.rowcount > 0
        except Exception:
            updated = False
    # Accept line_items in payload to persist to file store
    if "line_items" in payload and isinstance(payload["line_items"], list):
        try:
            _line_items_path(rid).write_text(json.dumps(payload["line_items"], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    return jsonify({"id": rid, "updated": updated, "data": payload}), 200


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
        root = _storage_dir().parent / rid
        p = root / "boxes.json"
        if not p.exists():
            return jsonify([]), 200
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
        return jsonify(data), 200
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
                        "SELECT id, merchant_name, purchase_datetime, gross_amount, net_amount, ai_confidence "
                        "FROM unified_files WHERE id=%s"
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
                        "SELECT id, merchant_name, orgnr, purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence "
                        "FROM unified_files WHERE id=%s"
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
