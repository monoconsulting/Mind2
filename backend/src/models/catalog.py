from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Tag:
    id: Optional[str]
    name: str
    description: Optional[str] = None


@dataclass
class Company:
    orgnr: str
    legal_name: str
    source: Optional[str] = None
