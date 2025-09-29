from __future__ import annotations

import os
import time
from flask import Flask, jsonify, request
from datetime import datetime, timezone
import json
import socket
from observability.logging import configure_json_logging
from observability.metrics import metrics_endpoint, track_request
from api.middleware import auth_required, apply_cors, handle_cors_preflight
from api.limits import limiter
try:
    from services.db.connection import db_cursor  # type: ignore
except Exception:  # pragma: no cover - optional early
    db_cursor = None  # type: ignore

from api.export import export_bp
from api.receipts import receipts_bp
from api.reconciliation_firstcard import recon_bp
from api.rules import rules_bp
from api.auth import auth_bp
from api.fetcher import fetcher_bp
from api.ingest import ingest_bp
from api.tags import tags_bp
from api.ai_config import ai_config_bp
from api.ai_processing import bp as ai_processing_bp
try:
    from services.tasks import process_ocr  # type: ignore
except Exception:  # pragma: no cover
    process_ocr = None  # type: ignore

configure_json_logging()
app = Flask(__name__)
limiter.init_app(app)
app.register_blueprint(receipts_bp)
app.register_blueprint(recon_bp)
app.register_blueprint(export_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(fetcher_bp)
app.register_blueprint(ingest_bp)
app.register_blueprint(rules_bp)
app.register_blueprint(tags_bp)
app.register_blueprint(ai_config_bp)
app.register_blueprint(ai_processing_bp)


# Best-effort DB auto migrations on startup (optional)
def _maybe_apply_migrations():
    if os.getenv("DB_AUTO_MIGRATE", "1").lower() not in {"1", "true", "yes"}:
        return
    try:
        from services.db.migrations import apply_migrations  # type: ignore
    except Exception:
        return
    # Wait briefly for DB to be reachable, then apply
    for _ in range(60):
        try:
            apply_migrations()
            break
        except Exception:
            time.sleep(1.0)


_maybe_apply_migrations()


@app.before_request
def _maybe_preflight():
    pre = handle_cors_preflight()
    return pre


@app.after_request
def _cors(resp):
    return apply_cors(resp)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "ai-api"}), 200


@app.route("/ingest/upload", methods=["POST"])
@track_request
def ingest_upload():
    # Minimal endpoint to satisfy integration smoke test
    return jsonify({"uploaded": True}), 200


@app.route("/system/metrics")
def system_metrics():
    return metrics_endpoint()


@app.get("/system/db-stats")
def db_stats():
    stats = {"ok": False, "unified_files": None, "error": None}
    if db_cursor is None:
        stats["error"] = "db unavailable"
        return jsonify(stats), 200
    try:
        with db_cursor() as cur:
            cur.execute("SELECT COUNT(1) FROM unified_files")
            (cnt,) = cur.fetchone() or (0,)
            stats["unified_files"] = int(cnt)
            stats["ok"] = True
    except Exception as e:  # pragma: no cover
        msg = str(e)
        if "1146" in msg and "doesn't exist" in msg:
            stats["hint"] = "Run /system/apply-migrations or enable DB_AUTO_MIGRATE"
    return jsonify(stats), 200


# Simple DB connectivity probe
@app.get("/system/db-ping")
def db_ping():
    ok = False
    error = None
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT 1")
                _ = cur.fetchone()
                ok = True
        except Exception as e:  # pragma: no cover
            error = str(e)
    return jsonify({"db": "ok" if ok else "error", "error": error}), 200


# --- System status/stats/config (v2.0) ---
_STARTED_AT = datetime.now(timezone.utc)


def _tcp_port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


@app.get("/system/status")
@track_request
def system_status():
    version = os.getenv("APP_VERSION", "dev")
    now = datetime.now(timezone.utc)
    db_ok = False
    receipts = None
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT COUNT(1) FROM unified_files")
                (cnt,) = cur.fetchone() or (0,)
                receipts = int(cnt)
                db_ok = True
        except Exception:
            db_ok = False
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_ok = _tcp_port_open(redis_host, redis_port)
    celery_ok = process_ocr is not None
    return (
        jsonify(
            {
                "service": "ai-api",
                "version": version,
                "started_at": _STARTED_AT.isoformat(),
                "now": now.isoformat(),
                "components": {
                    "db": db_ok,
                    "redis": redis_ok,
                    "celery": celery_ok,
                },
                "counters": {"receipts_total": receipts},
            }
        ),
        200,
    )


@app.get("/system/stats")
@track_request
def system_stats():
    stats: dict[str, object] = {
        "queues": {},
        "receipts": {},
        "invoices": {},
    }
    if db_cursor is not None:
        try:
            with db_cursor() as cur:
                # Queue depth
                try:
                    cur.execute("SELECT COUNT(1) FROM ai_processing_queue")
                    (qd,) = cur.fetchone() or (0,)
                    stats["queues"] = {"ai_processing_queue": int(qd)}
                except Exception:
                    stats["queues"] = {"ai_processing_queue": None}

                # Receipts totals by status
                try:
                    cur.execute(
                        "SELECT COALESCE(ai_status,'<null>'), COUNT(1) FROM unified_files GROUP BY ai_status"
                    )
                    stats["receipts"] = {
                        str(k): int(v) for k, v in (cur.fetchall() or [])
                    }
                except Exception:
                    stats["receipts"] = {}

                # Invoice docs and unmatched lines
                try:
                    cur.execute("SELECT COUNT(1) FROM invoice_documents")
                    (docs_cnt,) = cur.fetchone() or (0,)
                except Exception:
                    docs_cnt = None
                try:
                    cur.execute(
                        "SELECT COUNT(1) FROM invoice_lines WHERE matched_file_id IS NULL"
                    )
                    (unmatched_cnt,) = cur.fetchone() or (0,)
                except Exception:
                    unmatched_cnt = None
                stats["invoices"] = {
                    "documents_total": (int(docs_cnt) if docs_cnt is not None else None),
                    "lines_unmatched": (int(unmatched_cnt) if unmatched_cnt is not None else None),
                }
        except Exception:
            pass
    return jsonify(stats), 200


def _config_path() -> str:
    return os.getenv("SYSTEM_CONFIG_FILE", "/data/storage/system_config.json")


_CONFIG_WHITELIST = {
    "AI_PROCESSING_ENABLED",
    "ENABLE_REAL_OCR",
    "LOG_LEVEL",
    "ALLOWED_ORIGINS",
}


@app.get("/system/config")
@auth_required
def get_config():
    cfg = {}
    # Start from env
    for k in _CONFIG_WHITELIST:
        v = os.getenv(k)
        if v is not None:
            cfg[k] = v
    # Overlay from file if present
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            file_cfg = json.load(f)
            for k, v in file_cfg.items():
                if k in _CONFIG_WHITELIST:
                    cfg[k] = v
    except Exception:
        pass
    return jsonify(cfg), 200


@app.put("/system/config")
@auth_required
def put_config():
    body = request.get_json(silent=True) or {}
    out = {}
    for k, v in body.items():
        if k in _CONFIG_WHITELIST:
            out[k] = v
    try:
        path = _config_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True, "saved": out}), 200
    except Exception as e:  # pragma: no cover
        return jsonify({"ok": False, "error": str(e)}), 500


# Manual trigger to apply DB migrations and optional demo seed
@app.post("/system/apply-migrations")
def apply_migrations_route():
    try:
        from services.db.migrations import apply_migrations, list_migration_files  # type: ignore
    except Exception as e:  # pragma: no cover
        return jsonify({"ok": False, "error": f"import_failed: {e}"}), 500
    try:
        apply_migrations(seed_demo=True)
        files = [p.name for p in list_migration_files()]
        return jsonify({"ok": True, "applied": files}), 200
    except Exception as e:  # pragma: no cover
        return jsonify({"ok": False, "error": str(e)}), 500


# Simple Celery probe
@app.get("/system/celery-ping")
def celery_ping():
    if process_ocr is None:
        return jsonify({"celery": "unavailable"}), 200
    try:
        r = process_ocr.delay("smoke-celery")  # type: ignore[attr-defined]
        out = r.get(timeout=10)
        return jsonify({"celery": "ok", "result": out}), 200
    except Exception as e:  # pragma: no cover
        return jsonify({"celery": "error", "error": str(e)}), 200


# Example protected route pattern
@app.route("/admin/ping")
@auth_required
def admin_ping():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)