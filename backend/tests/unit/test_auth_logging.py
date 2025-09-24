from __future__ import annotations

import sys
from pathlib import Path
import logging
from flask import Flask


def create_test_app() -> Flask:
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


def test_auth_logs_without_secrets(monkeypatch, caplog):
    # login disabled path
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    app = create_test_app()
    client = app.test_client()
    caplog.set_level(logging.INFO)
    r = client.post("/ai/api/auth/login", json={"username": "admin", "password": "bad"})
    assert r.status_code == 503
    joined = "\n".join(m for _, _, m in caplog.record_tuples)
    assert "bad" not in joined  # password must not be present

    # invalid password path (with admin password set)
    caplog.clear()
    monkeypatch.setenv("ADMIN_PASSWORD", "secret!")
    app2 = create_test_app()
    client2 = app2.test_client()
    r2 = client2.post("/ai/api/auth/login", json={"username": "admin", "password": "wrongpw"})
    assert r2.status_code == 401
    joined2 = "\n".join(m for _, _, m in caplog.record_tuples)
    assert "wrongpw" not in joined2