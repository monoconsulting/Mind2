from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List

from flask import Blueprint, jsonify, request
from api.middleware import auth_required


tags_bp = Blueprint("tags", __name__)
_lock = threading.Lock()


def _tags_path() -> Path:
    base = os.getenv("TAGS_FILE", "/data/storage/tags.json")
    p = Path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> List[Dict[str, Any]]:
    p = _tags_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: List[Dict[str, Any]]) -> None:
    p = _tags_path()
    p.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


@tags_bp.get("/tags")
def list_tags():
    with _lock:
        return jsonify(_load()), 200


@tags_bp.post("/tags")
@auth_required
def create_tag():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "invalid"}), 400
    with _lock:
        items = _load()
        tid = body.get("id") or str(uuid.uuid4())
        items.append({"id": tid, "name": name})
        _save(items)
        return jsonify({"id": tid, "name": name}), 201


@tags_bp.put("/tags/<tid>")
@auth_required
def update_tag(tid: str):
    body = request.get_json(silent=True) or {}
    with _lock:
        items = _load()
        for i, t in enumerate(items):
            if t.get("id") == tid:
                t.update({k: v for k, v in body.items() if k in {"name"}})
                items[i] = t
                _save(items)
                return jsonify(t), 200
        return jsonify({"error": "not_found"}), 404


@tags_bp.delete("/tags/<tid>")
@auth_required
def delete_tag(tid: str):
    with _lock:
        items = _load()
        new_items = [t for t in items if t.get("id") != tid]
        if len(new_items) == len(items):
            return jsonify({"error": "not_found"}), 404
        _save(new_items)
        return jsonify({"ok": True}), 200

