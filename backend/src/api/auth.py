from __future__ import annotations

import base64
import hmac
import json
import os
import time
from hashlib import sha256
from typing import Any

from flask import Blueprint, jsonify, request
import logging
from api.limits import limiter


auth_bp = Blueprint("auth", __name__)


def _b64url(data: bytes) -> str:
    b64 = base64.urlsafe_b64encode(data).decode("utf-8")
    return b64.rstrip("=")


def _issue_jwt(sub: str, role: str, hours: int = 12) -> str:
    secret = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET") or "dev-secret"
    now = int(time.time())
    exp = now + int(hours * 3600)
    header = {"alg": "HS256", "typ": "JWT"}
    payload: dict[str, Any] = {"sub": sub, "role": role, "iat": now, "exp": exp}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, sha256).digest()
    sig_b64 = _b64url(sig)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


@auth_bp.post("/auth/login")
@limiter.limit("10/minute")
def login():
    log = logging.getLogger("auth")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_password:
        log.warning("login_disabled")
        return jsonify({"error": "login_disabled"}), 503
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    password = str(data.get("password") or "")
    if not username or not password:
        log.info("login_invalid_inputs", extra={"username": username or "<empty>"})
        return jsonify({"error": "invalid_credentials"}), 401
    if not hmac.compare_digest(password, admin_password):
        log.info("login_invalid_password", extra={"username": username or "<empty>"})
        return jsonify({"error": "invalid_credentials"}), 401

    token = _issue_jwt(sub=username, role="admin", hours=int(data.get("hours") or 12))
    log.info("login_success", extra={"username": username})
    return jsonify({"access_token": token, "token_type": "bearer", "expires_in": 3600 * int(data.get("hours") or 12)}), 200
