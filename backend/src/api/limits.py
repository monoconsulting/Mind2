from __future__ import annotations

import os

try:  # prefer real limiter when available
    from flask_limiter import Limiter  # type: ignore
    from flask_limiter.util import get_remote_address  # type: ignore

    # Storage can be overridden to Redis in the future via env, defaults to in-memory for dev
    _storage_uri = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")

    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=_storage_uri,
        default_limits=[],
    )
except Exception:  # pragma: no cover - test/dev fallback without dependency
    class _DummyLimiter:
        def init_app(self, _app):
            return None

        def limit(self, _rule: str):
            def _decorator(func):
                return func

            return _decorator

    limiter = _DummyLimiter()  # type: ignore
