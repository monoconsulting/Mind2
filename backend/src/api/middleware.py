from __future__ import annotations

import base64
import hmac
import json
import os
import time
from hashlib import sha256
from typing import Callable, Optional

from flask import Request, Response, jsonify, request


def _b64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _jwt_verify_hs256(token: str, secret: str) -> Optional[dict]:
    try:
        header_b64, payload_b64, sig_b64 = token.split('.')
    except ValueError:
        return None
    try:
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        signature = _b64url_decode(sig_b64)
        expected = hmac.new(secret.encode('utf-8'), signing_input, sha256).digest()
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode('utf-8'))
        # exp check if present
        exp = payload.get('exp')
        if exp is not None and time.time() > float(exp):
            return None
        return payload
    except Exception:
        return None


def auth_required(fn: Callable):
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({"error": "unauthorized"}), 401
        token = auth[len('Bearer '):].strip()
        secret = os.getenv('JWT_SECRET_KEY') or os.getenv('JWT_SECRET') or 'dev-secret'
        payload = _jwt_verify_hs256(token, secret)
        if payload is None:
            return jsonify({"error": "unauthorized"}), 401
        # Optionally, attach payload to request context if needed later
        request.jwt = payload  # type: ignore[attr-defined]
        return fn(*args, **kwargs)

    # Flask friendly wrapper metadata
    wrapper.__name__ = getattr(fn, "__name__", "auth_wrapped")
    return wrapper


def _allowed_origins() -> set[str]:
    raw = os.getenv('ALLOWED_ORIGINS', '*')
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    return set(parts)


def apply_cors(resp: Response) -> Response:
    origin = request.headers.get('Origin')
    allowed = _allowed_origins()
    if origin and ('*' in allowed or origin in allowed):
        resp.headers['Access-Control-Allow-Origin'] = origin
    resp.headers['Vary'] = 'Origin'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Headers'] = request.headers.get(
        'Access-Control-Request-Headers', 'Authorization, Content-Type'
    )
    resp.headers['Access-Control-Allow-Methods'] = request.headers.get(
        'Access-Control-Request-Method', 'GET, POST, PUT, DELETE, OPTIONS'
    )
    return resp


def handle_cors_preflight() -> Optional[Response]:
    if request.method == 'OPTIONS':
        # Return empty 204 with CORS headers
        resp: Response = jsonify({})
        resp.status_code = 204
        return apply_cors(resp)
    return None
