from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request
from api.middleware import auth_required


rules_bp = Blueprint("rules", __name__)
_lock = threading.Lock()


def _rules_path() -> Path:
    base = os.getenv("RULES_FILE", "/data/storage/rules.json")
    p = Path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_rules() -> List[Dict[str, Any]]:
    p = _rules_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_rules(data: List[Dict[str, Any]]) -> None:
    p = _rules_path()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@rules_bp.get("/rules")
@auth_required
def list_rules():
    with _lock:
        return jsonify(_load_rules())


@rules_bp.post("/rules")
@auth_required
def create_rule():
    body = request.get_json(silent=True) or {}
    # minimal schema: id, matcher (merchant or line pattern), account (BAS account), note
    matcher = (body.get("matcher") or "").strip()
    account = (body.get("account") or "").strip()
    if not matcher or not account:
        return jsonify({"error": "invalid"}), 400
    with _lock:
        items = _load_rules()
        rid = body.get("id") or str(uuid.uuid4())
        rule = {"id": rid, "matcher": matcher, "account": account, "note": body.get("note")}
        items.append(rule)
        _save_rules(items)
        return jsonify(rule), 201


@rules_bp.put("/rules/<rid>")
@auth_required
def update_rule(rid: str):
    body = request.get_json(silent=True) or {}
    with _lock:
        items = _load_rules()
        for i, r in enumerate(items):
            if r.get("id") == rid:
                r.update({k: v for k, v in body.items() if k in {"matcher", "account", "note"}})
                items[i] = r
                _save_rules(items)
                return jsonify(r)
        return jsonify({"error": "not_found"}), 404


@rules_bp.delete("/rules/<rid>")
@auth_required
def delete_rule(rid: str):
    with _lock:
        items = _load_rules()
        new_items = [r for r in items if r.get("id") != rid]
        if len(new_items) == len(items):
            return jsonify({"error": "not_found"}), 404
        _save_rules(new_items)
        return jsonify({"ok": True})
