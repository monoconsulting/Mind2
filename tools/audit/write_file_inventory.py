#!/usr/bin/env python3
"""
tools/audit/write_file_inventory.py

Generates a flat file inventory for a given directory.

Usage:
  python tools/audit/write_file_inventory.py <root_dir> <output_file>

Output format (TSV):
  relative_path<TAB>size_bytes
"""

import os
import sys


def main() -> int:
    """Entry point."""
    if len(sys.argv) != 3:
        print("Usage: write_file_inventory.py <root_dir> <output_file>")
        return 2

    root_dir = os.path.abspath(sys.argv[1])
    out_path = os.path.abspath(sys.argv[2])

    rows = []
    for base, _, files in os.walk(root_dir):
        for fn in files:
            full = os.path.join(base, fn)
            rel = os.path.relpath(full, root_dir).replace("\\", "/")
            try:
                size = os.path.getsize(full)
            except OSError:
                size = -1
            rows.append((rel, size))

    rows.sort(key=lambda x: x[0].casefold())

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for rel, size in rows:
            f.write(f"{rel}\t{size}\n")

    print(f"Wrote inventory: {out_path} ({len(rows)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
