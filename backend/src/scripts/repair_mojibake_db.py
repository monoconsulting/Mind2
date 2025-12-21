from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Iterable

from services.db.connection import db_cursor


_MOJIBAKE_SIG = re.compile(r"(?:\u00c3|\u00c2|\u00e2\u20ac|\u251c|\u0393\u00c7)")
_CODEC_ORDER: list[str] = ["cp1252", "latin1", "cp850", "cp437"]


@dataclass(frozen=True)
class _Fix:
    codec: str
    before: str
    after: str


def _looks_like_mojibake(value: str) -> bool:
    return bool(_MOJIBAKE_SIG.search(value))


def _try_fix(value: str, *, codecs: Iterable[str] = _CODEC_ORDER) -> _Fix | None:
    if not value or not _looks_like_mojibake(value):
        return None

    for codec in codecs:
        try:
            raw_bytes = value.encode(codec, errors="strict")
            decoded = raw_bytes.decode("utf-8", errors="strict")
        except Exception:
            continue

        if decoded == value:
            continue
        if "\ufffd" in decoded:
            continue

        # Deterministic safety: only accept if the inverse corruption roundtrip matches.
        try:
            roundtrip = decoded.encode("utf-8", errors="strict").decode(codec, errors="strict")
        except Exception:
            continue
        if roundtrip != value:
            continue

        return _Fix(codec=codec, before=value, after=decoded)

    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministically repair mojibake stored in MySQL text fields.")
    parser.add_argument(
        "--tables",
        nargs="+",
        default=["ai_system_prompts"],
        help="Tables to repair. Initial supported table: ai_system_prompts.",
    )
    parser.add_argument("--prompt-key", default=None, help="Restrict to a single ai_system_prompts.prompt_key.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows scanned per table.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply updates. Default is dry-run (no DB writes).",
    )
    return parser.parse_args()


def _repair_ai_system_prompts(*, apply: bool, prompt_key: str | None, limit: int | None) -> dict[str, int]:
    stats = {"rows_scanned": 0, "rows_updated": 0, "title_fixed": 0, "description_fixed": 0, "prompt_content_fixed": 0}

    where = "1=1"
    params: list[object] = []
    if prompt_key:
        where += " AND prompt_key = %s"
        params.append(prompt_key)

    limit_sql = ""
    if limit is not None:
        limit_sql = " LIMIT %s"
        params.append(int(limit))

    select_sql = f"""
    SELECT id, prompt_key, title, description, prompt_content
    FROM ai_system_prompts
    WHERE {where}
    ORDER BY id ASC
    {limit_sql}
    """

    with db_cursor(dictionary=True) as cur:
        cur.execute(select_sql, tuple(params) if params else None)
        rows = cur.fetchall() or []

        for row in rows:
            stats["rows_scanned"] += 1
            row_id = row.get("id")

            updates: dict[str, str] = {}
            for col, stat_key in (
                ("title", "title_fixed"),
                ("description", "description_fixed"),
                ("prompt_content", "prompt_content_fixed"),
            ):
                value = row.get(col)
                if not isinstance(value, str):
                    continue
                fix = _try_fix(value)
                if fix is None:
                    continue
                updates[col] = fix.after
                stats[stat_key] += 1

            if not updates:
                continue

            stats["rows_updated"] += 1

            if apply:
                sets = ", ".join(f"{col} = %s" for col in updates.keys())
                update_sql = f"UPDATE ai_system_prompts SET {sets} WHERE id = %s"
                cur.execute(update_sql, tuple(updates.values()) + (row_id,))
            else:
                prompt_key_value = row.get("prompt_key")
                changed_cols = ", ".join(sorted(updates.keys()))
                print(f"[DRY-RUN] ai_system_prompts id={row_id} prompt_key={prompt_key_value} cols={changed_cols}")

    return stats


def main() -> int:
    args = _parse_args()

    supported = {"ai_system_prompts"}
    for t in args.tables:
        if t not in supported:
            raise SystemExit(f"Unsupported table: {t}. Supported: {', '.join(sorted(supported))}")

    totals = {"rows_scanned": 0, "rows_updated": 0, "title_fixed": 0, "description_fixed": 0, "prompt_content_fixed": 0}

    if "ai_system_prompts" in args.tables:
        stats = _repair_ai_system_prompts(apply=bool(args.apply), prompt_key=args.prompt_key, limit=args.limit)
        for k, v in stats.items():
            totals[k] = totals.get(k, 0) + int(v)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] rows_scanned={totals['rows_scanned']} rows_updated={totals['rows_updated']} "
          f"title_fixed={totals['title_fixed']} description_fixed={totals['description_fixed']} "
          f"prompt_content_fixed={totals['prompt_content_fixed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

