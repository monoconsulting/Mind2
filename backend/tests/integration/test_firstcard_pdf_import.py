from __future__ import annotations

import base64
import json
from datetime import datetime

import pytest
from flask import Flask

from services.db.connection import db_cursor


@pytest.fixture()
def app() -> Flask:
    from api.app import app as flask_app
    return flask_app


def _cleanup_statement(statement_id: str):
    with db_cursor() as cur:
        cur.execute("DELETE FROM invoice_line_history WHERE invoice_line_id IN (SELECT id FROM invoice_lines WHERE invoice_id=%s)", (statement_id,))
        cur.execute("DELETE FROM invoice_lines WHERE invoice_id=%s", (statement_id,))
        cur.execute("DELETE FROM invoice_documents WHERE id=%s", (statement_id,))


def test_import_pdf_parses_transactions(app: Flask):
    client = app.test_client()
    statement_id = None

    try:
        fake_pdf_text = """
        Period: 2025-09-01 to 2025-09-30\n
        2025-09-05 Bundle Coffee 150.25\n        2025-09-12 Airport Taxi 320.00\n        """.strip()
        fake_pdf_bytes = fake_pdf_text.encode('utf-8')
        payload = {
            "pdf_base64": base64.b64encode(fake_pdf_bytes).decode('ascii'),
        }
        response = client.post('/reconciliation/firstcard/import', json=payload)
        assert response.status_code == 200
        body = response.get_json()
        statement_id = body['id']
        assert body['lines'] == 2

        with db_cursor() as cur:
            cur.execute("SELECT invoice_type, status, period_start, period_end FROM invoice_documents WHERE id=%s", (statement_id,))
            doc = cur.fetchone()
            assert doc is not None
            invoice_type, status, start, end = doc
            assert invoice_type == 'company_card'
            assert status == 'imported'
            assert str(start).startswith('2025-09-01')
            assert str(end).startswith('2025-09-30')

            cur.execute("SELECT transaction_date, amount, merchant_name FROM invoice_lines WHERE invoice_id=%s ORDER BY id ASC", (statement_id,))
            rows = cur.fetchall()
            assert len(rows) == 2
            assert str(rows[0][0]).startswith('2025-09-05')
            assert float(rows[0][1]) == 150.25
            assert rows[0][2] == 'Bundle Coffee'
    finally:
        if statement_id:
            _cleanup_statement(statement_id)
