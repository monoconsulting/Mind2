import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402
import os
import json
import base64
import hmac
from hashlib import sha256
import time

api_app = import_module("api.app")


def _make_token(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    def b64(d: bytes) -> str:
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode("utf-8")
    header_b64 = b64(json.dumps(header).encode("utf-8"))
    payload_b64 = b64(json.dumps(payload).encode("utf-8"))
    signing = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing, sha256).digest()
    sig_b64 = b64(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def test_auth_protected_endpoint_requires_bearer():
    app = api_app.app
    client = app.test_client()
    res = client.get("/admin/ping")
    assert res.status_code == 401


def test_auth_protected_endpoint_valid_token():
    app = api_app.app
    client = app.test_client()
    os.environ["JWT_SECRET"] = "s3cr3t"
    tok = _make_token({"sub": "u1", "exp": time.time() + 60}, os.environ["JWT_SECRET"])
    res = client.get("/admin/ping", headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 200
    assert res.get_json()["ok"] is True


def test_cors_preflight_and_headers():
    app = api_app.app
    client = app.test_client()
    res = client.options(
        "/admin/ping",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    # CORS preflight should 204 and echo headers
    assert res.status_code == 204
    assert res.headers.get("Access-Control-Allow-Origin") in ("http://example.com", None)
    # Follow-up GET should include CORS headers too
    res2 = client.get("/admin/ping")
    assert res2.headers.get("Access-Control-Allow-Credentials") == "true"
