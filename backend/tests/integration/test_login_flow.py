from __future__ import annotations

import sys
from pathlib import Path
from flask import Flask, jsonify


def create_test_app() -> Flask:
    # Mirror unit test approach: add backend/src to sys.path, register auth blueprint
    _here = Path(__file__).resolve()
    _repo_root = _here.parents[2]
    _src = _repo_root / "src"
    sys.path.insert(0, str(_src))
    from api.auth import auth_bp  # type: ignore
    from api.limits import limiter  # type: ignore

    app = Flask(__name__)
    limiter.init_app(app)
    app.register_blueprint(auth_bp, url_prefix="/ai/api")
    return app


def test_login_then_admin_ping(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret!")
    app: Flask = create_test_app()
    # Register a minimal protected endpoint using same decorator to simulate /admin/ping BEFORE first request
    from api.middleware import auth_required  # type: ignore

    @app.get("/ai/api/admin/ping")
    @auth_required
    def _admin_ping():  # pragma: no cover - trivial
        return jsonify({"ok": True})
    client = app.test_client()

    # Login
    r = client.post("/ai/api/auth/login", json={"username": "admin", "password": "secret!"})
    assert r.status_code == 200
    token = r.get_json()["access_token"]

    r2 = client.get("/ai/api/admin/ping", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.get_json().get("ok") is True
