"""Shared helpers for obtaining MySQL connections/cursors."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector
from mysql.connector import errors as mysql_errors

DEFAULT_LOCK_WAIT_TIMEOUT = int(os.getenv("DB_LOCK_WAIT_TIMEOUT", "5"))
LOCK_ERROR_CODES = {1205, 1213}


class DBLockTimeout(RuntimeError):
    """Raised when a database statement times out waiting for a lock."""

    pass


def _env(name: str, default: str | None = None) -> str:
    """Read an environment variable or raise if missing."""

    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_connection():
    """Create and return a MySQL connection using environment variables.

    The connection parameters mirror production defaults so that the AI
    pipeline can run locally and in CI without manual configuration.

    Required environment variables (defaults shown in parentheses):
        - ``DB_HOST`` (``127.0.0.1``)
        - ``DB_PORT`` (``3310``)
        - ``DB_NAME`` (``mono_se_db_9``)
        - ``DB_USER`` (``mind``)
        - ``DB_PASS`` (``mind``)
    """

    return mysql.connector.connect(
        host=_env("DB_HOST", "127.0.0.1"),
        port=int(_env("DB_PORT", "3310")),
        database=_env("DB_NAME", "mono_se_db_9"),
        user=_env("DB_USER", "mind"),
        password=_env("DB_PASS", "mind"),
        autocommit=False,
        charset="utf8mb4",
        use_unicode=True,
    )


@contextmanager
def db_cursor(*, dictionary: bool = False, lock_timeout: int | None = None) -> Iterator[Any]:
    """Yield a cursor from a managed connection, closing both afterwards."""

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=dictionary)
        effective_timeout = lock_timeout if lock_timeout is not None else DEFAULT_LOCK_WAIT_TIMEOUT
        if effective_timeout is not None:
            try:
                cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", (int(effective_timeout),))
            except Exception:
                # Best-effort; continue even if server doesn't support this command
                pass
        yield cursor
        connection.commit()
    except Exception as exc:
        connection.rollback()
        if mysql_errors and isinstance(exc, mysql_errors.DatabaseError):
            errno = getattr(exc, "errno", None)
            if errno in LOCK_ERROR_CODES:
                raise DBLockTimeout(str(exc)) from exc
        raise
    finally:
        try:
            if cursor is not None:
                cursor.close()
        finally:
            connection.close()
