
from __future__ import annotations

import io
import json
import os
import uuid
import zipfile
from datetime import datetime

import pytest
from flask import Flask

from services.db.connection import db_cursor
from services.storage import FileStorage


@pytest.fixture()
def app(monkeypatch) -> Flask:
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    from api.app import app as flask_app
    return flask_app


def _seed_statement(tmp_path) -> tuple[str, int, str]:
    statement_id = str(uuid.uuid4())
    receipt_id = str(uuid.uuid4())
    company_id = f"test-company-{receipt_id[:8]}"
    line_amount = 150.25
    purchase_dt = datetime(2025, 9, 5, 10, 30, 0)

    storage = FileStorage(tmp_path)
    storage.save(receipt_id, "page-1.jpg", b"fake-receipt-image")

    with db_cursor() as cur:
        cur.execute("DELETE FROM invoice_line_history WHERE invoice_line_id IN (SELECT id FROM invoice_lines WHERE invoice_id=%s)", (statement_id,))
        cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (statement_id,))
        cur.execute("DELETE FROM invoice_documents WHERE id=%s", (statement_id,))
        cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (receipt_id,))
        cur.execute("DELETE FROM unified_files WHERE id=%s", (receipt_id,))
        cur.execute("DELETE FROM companies WHERE id=%s", (company_id,))

        # Create company first
        cur.execute(
            "INSERT INTO companies (id, name, orgnr) VALUES (%s, %s, %s)",
            (company_id, 'Bundle Coffee', '666666-6666'),
        )

        # Create receipt with company_id reference
        cur.execute(
            (
                "INSERT INTO unified_files (id, file_type, created_at, updated_at, company_id, purchase_datetime, "
                "gross_amount, net_amount, ai_status, ai_confidence, submitted_by) "
                "VALUES (%s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s)"
            ),
            (
                receipt_id,
                'receipt',
                company_id,
                purchase_dt,
                line_amount,
                line_amount,
                'completed',
                0.92,
                'tester',
            ),
        )
        cur.execute(
            (
                "INSERT INTO ai_accounting_proposals (receipt_id, account_code, debit, credit, vat_rate, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            ),
            (receipt_id, '5790', line_amount, 0, None, 'Coffee expense'),
        )
        cur.execute(
            (
                "INSERT INTO ai_accounting_proposals (receipt_id, account_code, debit, credit, vat_rate, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            ),
            (receipt_id, '2440', 0, line_amount, None, 'Liability'),
        )

        cur.execute(
            (
                "INSERT INTO invoice_documents (id, invoice_type, period_start, period_end, status, uploaded_at) "
                "VALUES (%s, 'company_card', %s, %s, %s, NOW())"
            ),
            (statement_id, datetime(2025, 9, 1), datetime(2025, 9, 30), 'imported'),
        )
        cur.execute(
            (
                "INSERT INTO invoice_lines (invoice_id, transaction_date, amount, merchant_name, description, match_status) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            ),
            (statement_id, purchase_dt.date(), line_amount, 'Bundle Coffee', 'Coffee run', 'unmatched'),
        )
        line_id = cur.lastrowid
    return statement_id, int(line_id), receipt_id


def test_manual_match_and_company_card_export(app: Flask, tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))

    statement_id, line_id, receipt_id = _seed_statement(storage_dir)
    client = app.test_client()

    # Manual match via API should update DB
    resp = client.put(f"/reconciliation/firstcard/lines/{line_id}", json={"matched_file_id": receipt_id})
    assert resp.status_code == 200

    with db_cursor() as cur:
        cur.execute("SELECT matched_file_id FROM invoice_lines WHERE id=%s", (line_id,))
        (matched_file_id,) = cur.fetchone()
        assert matched_file_id == receipt_id

    # Export bundle as ZIP
    export_resp = client.get(f"/export/company-card?statement_id={statement_id}")
    assert export_resp.status_code == 200
    assert export_resp.headers.get('Content-Type') == 'application/zip'

    bundle = zipfile.ZipFile(io.BytesIO(export_resp.data))
    names = bundle.namelist()
    assert 'statement.json' in names
    expected_asset = f'receipts/{receipt_id}/page-1.jpg'
    assert expected_asset in names

    statement_json = json.loads(bundle.read('statement.json').decode('utf-8'))
    assert statement_json['statement']['id'] == statement_id
    assert any(line['matched_file_id'] == receipt_id for line in statement_json['lines'])

    with db_cursor() as cur:
        cur.execute("DELETE FROM invoice_line_history WHERE invoice_line_id=%s", (line_id,))
        cur.execute("DELETE FROM invoice_lines WHERE id=%s", (line_id,))
        cur.execute("DELETE FROM invoice_documents WHERE id=%s", (statement_id,))
        cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (receipt_id,))
        cur.execute("DELETE FROM unified_files WHERE id=%s", (receipt_id,))
        # Cleanup company if created
        cur.execute("DELETE FROM companies WHERE id LIKE %s", (f"test-company-{receipt_id[:8]}",))
