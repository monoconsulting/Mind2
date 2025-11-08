from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _format_date_for_db(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Support ``date`` objects without importing separately
        return value.strftime("%Y-%m-%d")  # type: ignore[attr-defined]
    except Exception:
        try:
            return str(value)
        except Exception:
            return None


__all__ = ["_to_decimal", "_format_date_for_db"]
