from __future__ import annotations

import os
from pathlib import Path
from typing import List


def _ensure_category(root: Path, category: str) -> Path:
    target = root / category
    target.mkdir(parents=True, exist_ok=True)
    return target


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

    def save_in_category(self, category: str, filename: str, data: bytes) -> Path:
        if not filename or "/" in filename or ".." in filename:
            raise ValueError("Unsafe category filename")
        root = _ensure_category(self.base, category)
        path = (root / filename).resolve()
        if not str(path).startswith(str(root.resolve())):
            raise ValueError("Unsafe category path")
        path.write_bytes(data)
        return path

    def save_original(self, file_id: str, original_name: str, data: bytes) -> Path:
        ext = Path(original_name).suffix or ".bin"
        filename = f"{file_id}{ext if ext.startswith('.') else '.' + ext}"
        return self.save_in_category("originals", filename, data)

    def save_converted_page(self, file_id: str, page_number: int, data: bytes, ext: str = ".png") -> Path:
        suffix = ext if ext.startswith(".") else f".{ext}"
        filename = f"{file_id}_page_{page_number:04d}{suffix}"
        return self.save_in_category("converted", filename, data)

    def save_audio(self, file_id: str, original_name: str, data: bytes) -> Path:
        ext = Path(original_name).suffix or ".bin"
        filename = f"{file_id}{ext if ext.startswith('.') else '.' + ext}"
        return self.save_in_category("audio", filename, data)

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
