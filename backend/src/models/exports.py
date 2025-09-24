from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class ExportJob:
    id: Optional[str]
    from_date: date
    to_date: date
    created_by: str
    created_at: datetime
    sie_version: Optional[str] = None
    file_ref: Optional[str] = None
