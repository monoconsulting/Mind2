from __future__ import annotations

import os
from flask import Flask
from pathlib import Path
import sys

# Ensure backend/src is on sys.path for absolute imports like `api.auth`
_here = Path(__file__).resolve()
_repo_root = _here.parents[2]
_src = _repo_root / "src"
sys.path.insert(0, str(_src))

# Use the auth blueprint directly to avoid importing full app (which applies migrations)
from api.auth import auth_bp  # type: ignore
from api.limits import limiter  # type: ignore


def create_test_app():
    app = Flask(__name__)
    # Initialize limiter for decorators to work
    limiter.init_app(app)
    app.register_blueprint(auth_bp, url_prefix="/ai/api")
    return app


def test_login_disabled(monkeypatch):
    # No ADMIN_PASSWORD -> 503
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    app = create_test_app()
    client = app.test_client()
    resp = client.post("/ai/api/auth/login", json={"username": "admin", "password": "x"})
    assert resp.status_code == 503


def test_login_success(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret!")
    app = create_test_app()
    client = app.test_client()
    resp = client.post("/ai/api/auth/login", json={"username": "admin", "password": "secret!"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data and "access_token" in data


def test_login_invalid_credentials(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret!")
    app = create_test_app()
    client = app.test_client()
    # Missing username
    resp = client.post("/ai/api/auth/login", json={"password": "secret!"})
    assert resp.status_code == 401
    # Wrong password
    resp2 = client.post("/ai/api/auth/login", json={"username": "admin", "password": "nope"})
    assert resp2.status_code == 401


def test_token_expiry_rejection(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret!")
    app = create_test_app()
    # Protected route
    from api.middleware import auth_required  # type: ignore
    from flask import jsonify

    @app.get("/ai/api/admin/ping2")
    @auth_required
    def _admin_ping2():  # pragma: no cover - trivial
        return jsonify({"ok": True})

    client = app.test_client()
    # Issue an already expired token by passing a negative lifetime
    resp = client.post("/ai/api/auth/login", json={"username": "admin", "password": "secret!", "hours": -1})
    assert resp.status_code == 200
    token = resp.get_json()["access_token"]

    r2 = client.get("/ai/api/admin/ping2", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 401
