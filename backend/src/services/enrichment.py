from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol
import json
import os
from pathlib import Path

from models.catalog import Company
from models.receipts import Receipt


def normalize_orgnr(orgnr: str) -> Optional[str]:
    """Normalize Swedish orgnr to 10 digits, or return None if impossible.

    Rules:
    - Strip all non-digits
    - Accept 10 digits directly
    - Accept 12 digits (YYYY + 10 digits) → drop the first two digits to yield 10
    - Validate with Luhn checksum on the 10-digit number
    """
    digits = "".join(ch for ch in (orgnr or "") if ch.isdigit())
    if len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10:
        return None
    return digits if _luhn_valid(digits) else None


def _luhn_valid(d: str) -> bool:
    if len(d) != 10 or not d.isdigit():
        return False
    nums = [int(x) for x in d]
    checksum = nums[-1]
    total = 0
    # Luhn over first 9 digits
    for idx, n in enumerate(nums[:-1]):
        mul = 2 if idx % 2 == 0 else 1
        v = n * mul
        if v > 9:
            v -= 9
        total += v
    calc = (10 - (total % 10)) % 10
    return calc == checksum


class CompanyProvider(Protocol):
    def get_company(self, orgnr: str) -> Optional[Company]:
        ...


@dataclass
class DictCompanyProvider:
    mapping: dict[str, str]
    source: str = "dict"

    def get_company(self, orgnr: str) -> Optional[Company]:
        name = self.mapping.get(orgnr)
        if not name:
            return None
        return Company(orgnr=orgnr, legal_name=name, source=self.source)


@dataclass
class FileCompanyProvider:
    path: str
    source: str = "file"
    _cache: Optional[dict] = None

    def _load(self) -> dict:
        if self._cache is not None:
            return self._cache
        p = Path(self.path)
        if not p.exists():
            self._cache = {}
            return self._cache
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            # expected format: { "orgnr": "Legal Name", ... }
            if isinstance(data, dict):
                self._cache = data
            else:
                self._cache = {}
        except Exception:
            self._cache = {}
        return self._cache

    def get_company(self, orgnr: str) -> Optional[Company]:
        mapping = self._load()
        name = mapping.get(orgnr)
        if not name:
            return None
        return Company(orgnr=orgnr, legal_name=name, source=self.source)


def provider_from_env() -> CompanyProvider:
    kind = (os.getenv("ORG_PROVIDER", "file").strip().lower())
    if kind == "file":
        path = os.getenv("ORG_REGISTRY_FILE", "/data/storage/org_registry.json")
        return FileCompanyProvider(path=path)
    # fallback to empty dict provider
    return DictCompanyProvider(mapping={})


def enrich_receipt(receipt: Receipt, provider: CompanyProvider) -> Optional[Company]:
    """Enrich with company details if orgnr is present and valid.

    Does not mutate the receipt. Returns a Company or None.
    """
    if not receipt.orgnr:
        return None
    norm = normalize_orgnr(receipt.orgnr)
    if not norm:
        return None
    return provider.get_company(norm)
