from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all unified_files (receipts + fc-files + invoices + others). Default: receipts only.",
    )
    args = parser.parse_args()

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

    if args.all:
        query = """
        /* Receipts: keep full missing/warnings semantics from v_receipt_missing_status */
        SELECT
          v.file_id,
          v.file_name,
          v.currency,
          v.gross_amount_display,
          v.net_amount_display,
          v.missing_count,
          v.missing_fields,
          v.warnings,
          v.latest_workflow_status,
          v.latest_stage_name,
          v.latest_stage_status,
          v.ai_history_rows,
          uf.file_type,
          uf.workflow_type,
          c.name AS company_name
        FROM v_receipt_missing_status v
        JOIN unified_files uf ON uf.id = v.file_id
        LEFT JOIN companies c ON c.id = uf.company_id
        WHERE uf.deleted_at IS NULL

        UNION ALL

        /* Non-receipts: include all imported files with safe metadata (no guessing of required fields) */
        SELECT
          uf.id AS file_id,
          COALESCE(NULLIF(uf.original_filename, ''), NULLIF(uf.original_file_name, ''), uf.id) AS file_name,
          COALESCE(NULLIF(TRIM(uf.currency), ''), 'SEK') AS currency,
          COALESCE(uf.gross_amount_original, uf.gross_amount) AS gross_amount_display,
          COALESCE(uf.net_amount_original, uf.net_amount)     AS net_amount_display,
          0 AS missing_count,
          NULL AS missing_fields,
          NULL AS warnings,
          wr_latest.status AS latest_workflow_status,
          wsr_latest.stage_key AS latest_stage_name,
          wsr_latest.status AS latest_stage_status,
          COALESCE(ai_agg.ai_history_rows, 0) AS ai_history_rows,
          uf.file_type,
          uf.workflow_type,
          c.name AS company_name
        FROM unified_files uf
        LEFT JOIN companies c ON c.id = uf.company_id

        /* Latest workflow run per file: max(created_at), tie-break by max(id) */
        LEFT JOIN (
          SELECT w1.*
          FROM workflow_runs w1
          INNER JOIN (
            SELECT file_id, MAX(created_at) AS max_created_at
            FROM workflow_runs
            GROUP BY file_id
          ) w2
            ON w2.file_id = w1.file_id
           AND w2.max_created_at = w1.created_at
          INNER JOIN (
            SELECT file_id, created_at, MAX(id) AS max_id
            FROM workflow_runs
            GROUP BY file_id, created_at
          ) w3
            ON w3.file_id = w1.file_id
           AND w3.created_at = w1.created_at
           AND w3.max_id = w1.id
        ) wr_latest
          ON wr_latest.file_id = uf.id

        /* Latest stage run per workflow_run: max(started_at), tie-break by max(id) */
        LEFT JOIN (
          SELECT s1.*
          FROM workflow_stage_runs s1
          INNER JOIN (
            SELECT workflow_run_id, MAX(started_at) AS max_started_at
            FROM workflow_stage_runs
            GROUP BY workflow_run_id
          ) s2
            ON s2.workflow_run_id = s1.workflow_run_id
           AND s2.max_started_at = s1.started_at
          INNER JOIN (
            SELECT workflow_run_id, started_at, MAX(id) AS max_id
            FROM workflow_stage_runs
            GROUP BY workflow_run_id, started_at
          ) s3
            ON s3.workflow_run_id = s1.workflow_run_id
           AND s3.started_at = s1.started_at
           AND s3.max_id = s1.id
        ) wsr_latest
          ON wsr_latest.workflow_run_id = wr_latest.id

        /* AI history aggregate */
        LEFT JOIN (
          SELECT file_id, COUNT(*) AS ai_history_rows
          FROM ai_processing_history
          GROUP BY file_id
        ) ai_agg
          ON ai_agg.file_id = uf.id

        WHERE uf.deleted_at IS NULL
          AND (uf.file_type IS NULL OR uf.file_type <> 'receipt')

        ORDER BY file_id DESC
        """
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
            "file_type",
            "workflow_type",
            "company_name",
        ]
    else:
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

    with db_cursor(dictionary=True) as cur:
        cur.execute(query)
        rows = cur.fetchall() or []

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

