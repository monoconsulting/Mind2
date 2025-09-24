from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional


class FileStorage:
    def __init__(self, base_dir: str | Path):
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, receipt_id: str, filename: str) -> Path:
        # Prevent traversal; only allow plain filenames (no separators, no '..', not absolute)
        fname_path = Path(filename)
        if fname_path.is_absolute() or len(fname_path.parts) != 1 or fname_path.name in {"", ".", ".."}:
            raise ValueError("Unsafe path detected")
        name = fname_path.name
        root = self.base / receipt_id
        root.mkdir(parents=True, exist_ok=True)
        p = (root / name).resolve()
        if not str(p).startswith(str(root.resolve())):
            raise ValueError("Unsafe path detected")
        return p

    def save(self, receipt_id: str, filename: str, data: bytes) -> Path:
        p = self._safe_path(receipt_id, filename)
        p.write_bytes(data)
        return p

    def load(self, receipt_id: str, filename: str) -> bytes:
        p = self._safe_path(receipt_id, filename)
        return p.read_bytes()

    def list(self, receipt_id: str) -> List[str]:
        root = (self.base / receipt_id)
        if not root.exists():
            return []
        return sorted([f.name for f in root.iterdir() if f.is_file()])

    def delete(self, receipt_id: str, filename: str) -> bool:
        p = self._safe_path(receipt_id, filename)
        if p.exists():
            p.unlink()
            return True
        return False
