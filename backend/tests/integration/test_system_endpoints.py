import os
import sys
from pathlib import Path
import json


def import_app(monkeypatch):
    # Prevent slow auto-migrate during tests
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from importlib import import_module

    return import_module("api.app").app  # type: ignore


def _login_token(app, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "secret!")
    client = app.test_client()
    r = client.post("/auth/login", json={"username": "admin", "password": "secret!"})
    assert r.status_code == 200
    return r.get_json()["access_token"]


def test_system_status_and_stats(monkeypatch):
    app = import_app(monkeypatch)
    client = app.test_client()

    r1 = client.get("/system/status")
    assert r1.status_code == 200
    data = r1.get_json()
    assert data.get("service") == "ai-api"
    assert "components" in data and isinstance(data["components"], dict)

    r2 = client.get("/system/stats")
    assert r2.status_code == 200
    stats = r2.get_json()
    assert isinstance(stats, dict)
    # Should include top-level keys even without DB
    assert "queues" in stats and "receipts" in stats and "invoices" in stats


def test_system_config_requires_auth_and_persists(monkeypatch, tmp_path):
    cfg_path = tmp_path / "system_config.json"
    monkeypatch.setenv("SYSTEM_CONFIG_FILE", str(cfg_path))
    app = import_app(monkeypatch)
    client = app.test_client()

    # Unauth should be 401
    r0 = client.get("/system/config")
    assert r0.status_code == 401

    token = _login_token(app, monkeypatch)
    headers = {"Authorization": f"Bearer {token}"}

    # Write a config value
    body = {"LOG_LEVEL": "DEBUG", "SHOULD_IGNORE": True}
    r1 = client.put("/system/config", headers=headers, json=body)
    assert r1.status_code == 200
    saved = r1.get_json()["saved"]
    assert saved == {"LOG_LEVEL": "DEBUG"}  # only whitelisted keys

    # File exists and contains the key
    content = json.loads(cfg_path.read_text("utf-8"))
    assert content == {"LOG_LEVEL": "DEBUG"}

    # Read back via API
    r2 = client.get("/system/config", headers=headers)
    assert r2.status_code == 200
    cfg = r2.get_json()
    assert cfg.get("LOG_LEVEL") == "DEBUG"

