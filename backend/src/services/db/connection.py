from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector


def _env(name: str, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


def get_connection():
    """Create and return a MySQL connection using env vars.

    Required env:
      - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
    """
    return mysql.connector.connect(
        host=_env("DB_HOST", "127.0.0.1"),
        port=int(_env("DB_PORT", "3310")),
        database=_env("DB_NAME", "mono_se_db_9"),
        user=_env("DB_USER", "mind"),
        password=_env("DB_PASS", "mind"),
        autocommit=True,
    )


@contextmanager
def db_cursor() -> Iterator[Any]:
    cnx = get_connection()
    cur = None
    try:
        cur = cnx.cursor()
        yield cur
    finally:
        try:
            if cur is not None:
                cur.close()
        except Exception:
            pass
        cnx.close()
