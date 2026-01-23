import os
import time
from pathlib import Path

import mysql.connector
import pytest
import requests


ROOT = Path(__file__).resolve().parents[2]


def _load_env_file() -> dict[str, str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return {}
    data: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


_ENV_FILE = _load_env_file()


def _env(key: str, default: str) -> str:
    return os.getenv(key) or _ENV_FILE.get(key, default)


BASE_URL = _env("TEST_BASE_URL", "http://localhost:8008/ai/api")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "adminadmin")

DB_HOST = _env("DB_HOST", "127.0.0.1")
DB_PORT = int(_env("DB_PORT", "3310"))
DB_NAME = _env("DB_NAME", "mono_se_db_9")
DB_USER = _env("DB_USER", "minduser")
DB_PASS = _env("DB_PASS", "mind2password")

def _db_conn():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        autocommit=True,
    )


def _login_token() -> str:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": ADMIN_PASSWORD},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data["access_token"]


def _resume_file(file_id: str, token: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/ingest/process/{file_id}/resume",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _wait_for_stage(
    conn,
    workflow_run_id: int,
    stage_key: str,
    timeout_sec: int = 900,
) -> tuple[str, str]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            status, message = _stage_status(conn, workflow_run_id, stage_key)
            if status in ("succeeded", "failed", "skipped"):
                return status, message
        except AssertionError:
            pass
        time.sleep(5)
    raise AssertionError(f"Timeout waiting for {stage_key} in workflow_run_id={workflow_run_id}")


def _stage_status(conn, workflow_run_id: int, stage_key: str) -> tuple[str, str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT status, message
          FROM workflow_stage_runs
         WHERE workflow_run_id = %s AND stage_key = %s
         ORDER BY id DESC
         LIMIT 1
        """,
        (workflow_run_id, stage_key),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        raise AssertionError(f"Stage {stage_key} not found for workflow_run_id={workflow_run_id}")
    return row[0], row[1] or ""


def _combined_ocr_info(conn, file_id: str) -> tuple[int, str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            COALESCE(JSON_UNQUOTE(JSON_EXTRACT(other_data, '$.combined_ocr_text')), ''),
            COALESCE(ai_status, '')
          FROM unified_files
         WHERE id = %s
        """,
        (file_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        raise AssertionError(f"File {file_id} not found in unified_files")
    text, ai_status = row
    return len(text or ""), ai_status or ""


def _assert_merge_success(conn, workflow_run_id: int, file_id: str) -> None:
    status, message = _stage_status(conn, workflow_run_id, "merge_ocr")
    assert status == "succeeded", f"merge_ocr status={status} message={message}"

    combined_len, ai_status = _combined_ocr_info(conn, file_id)
    assert combined_len > 0, f"combined_ocr_text length={combined_len}"
    assert ai_status in {"ocr_done", "completed"}, f"ai_status={ai_status}"


def _pick_file_id(conn, pattern: str) -> str:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id
          FROM unified_files
         WHERE file_type = 'pdf'
           AND original_filename LIKE %s
         ORDER BY updated_at DESC
         LIMIT 1
        """,
        (pattern,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        raise AssertionError(f"No pdf file_id found for pattern {pattern}")
    return row[0]


def _pick_file_id_any(conn, patterns: list[str]) -> str:
    last_error = None
    for pattern in patterns:
        try:
            return _pick_file_id(conn, pattern)
        except AssertionError as exc:
            last_error = exc
    raise AssertionError(f"No pdf file_id found for patterns {patterns}") from last_error


def _find_recent_merge_fail_candidates(conn, limit: int = 1) -> list[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT wr.file_id
          FROM workflow_stage_runs wsr
          JOIN workflow_runs wr ON wr.id = wsr.workflow_run_id
          JOIN unified_files uf ON uf.id = wr.file_id
         WHERE wsr.stage_key = 'merge_ocr'
           AND wsr.status = 'failed'
           AND uf.file_type = 'pdf'
         ORDER BY wr.updated_at DESC
         LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall() or []
    cur.close()
    return [row[0] for row in rows]


def test_receipt_ocr_merge_swedish():
    conn = _db_conn()
    try:
        swedish_file_id = _pick_file_id_any(conn, ["kvitto-%", "receipt-%", "Faktura_%"])
        token = _login_token()
        resume = _resume_file(swedish_file_id, token)
        assert resume["workflow_key"] == "WF2_PDF_SPLIT", f"workflow_key={resume['workflow_key']}"
        workflow_run_id = int(resume["workflow_run_id"])
        status, message = _wait_for_stage(conn, workflow_run_id, "merge_ocr")
        assert status == "succeeded", f"merge_ocr status={status} message={message}"
        _assert_merge_success(conn, workflow_run_id, swedish_file_id)
    finally:
        conn.close()


def test_receipt_ocr_merge_english():
    conn = _db_conn()
    try:
        english_file_id = _pick_file_id(conn, "github-monoconsulting-receipt-%")
        token = _login_token()
        resume = _resume_file(english_file_id, token)
        assert resume["workflow_key"] == "WF2_PDF_SPLIT", f"workflow_key={resume['workflow_key']}"
        workflow_run_id = int(resume["workflow_run_id"])
        status, message = _wait_for_stage(conn, workflow_run_id, "merge_ocr")
        assert status == "succeeded", f"merge_ocr status={status} message={message}"
        _assert_merge_success(conn, workflow_run_id, english_file_id)
    finally:
        conn.close()


def test_receipt_ocr_merge_fails_when_no_usable_text():
    token = _login_token()
    conn = _db_conn()
    try:
        candidates = _find_recent_merge_fail_candidates(conn)
        if not candidates:
            pytest.skip("No recent merge_ocr failures found to validate negative case.")
        file_id = candidates[0]
        resume = _resume_file(file_id, token)
        if resume["workflow_key"] != "WF2_PDF_SPLIT":
            pytest.skip(f"Candidate {file_id} resumed as {resume['workflow_key']}, not WF2.")
        workflow_run_id = int(resume["workflow_run_id"])
        status, _ = _wait_for_stage(conn, workflow_run_id, "merge_ocr")
        if status == "failed":
            combined_len, ai_status = _combined_ocr_info(conn, file_id)
            assert combined_len == 0, f"combined_ocr_text length={combined_len}"
            assert ai_status == "ocr_failed", f"ai_status={ai_status}"
            return
    finally:
        conn.close()

    pytest.skip("No receipt still fails merge_ocr after OCR fixes.")
