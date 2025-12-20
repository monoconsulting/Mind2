from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path


def _load_dotenv_if_present(repo_root: Path) -> None:
    env_path = repo_root / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        # Don't override explicit environment variables
        os.environ.setdefault(key, value.strip())


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    _load_dotenv_if_present(repo_root)

    # Import backend DB connection (mysql connector) without booting the API
    import sys

    sys.path.insert(0, str(repo_root / "backend" / "src"))
    from services.db.connection import db_cursor  # type: ignore

    out_dir = repo_root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = out_dir / f"missing_per_receipt_{ts}.csv"

    query = """
    SELECT
      file_id,
      file_name,
      currency,
      gross_amount_display,
      net_amount_display,
      missing_count,
      missing_fields,
      warnings,
      latest_workflow_status,
      latest_stage_name,
      latest_stage_status,
      ai_history_rows
    FROM v_receipt_missing_status
    ORDER BY
      (latest_workflow_status IN ('failed','error')) DESC,
      (latest_workflow_status IN ('running','queued')) DESC,
      missing_count DESC,
      latest_workflow_started_at DESC,
      file_id DESC
    """

    with db_cursor(dictionary=True) as cur:
        cur.execute(query)
        rows = cur.fetchall() or []

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        fieldnames = [
            "file_id",
            "file_name",
            "currency",
            "gross_amount_display",
            "net_amount_display",
            "missing_count",
            "missing_fields",
            "warnings",
            "latest_workflow_status",
            "latest_stage_name",
            "latest_stage_status",
            "ai_history_rows",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

