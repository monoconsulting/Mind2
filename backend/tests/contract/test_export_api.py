from __future__ import annotations

from datetime import datetime
import uuid

import pytest
from flask import Flask

from services.db.connection import db_cursor


@pytest.fixture()
def app() -> Flask:
    from api.app import app as flask_app
    return flask_app


def _seed_completed_receipt(account_total: float = 25.50) -> str:
    receipt_id = str(uuid.uuid4())
    purchase_dt = datetime(2025, 8, 15, 12, 0, 0)
    with db_cursor() as cur:
        cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (receipt_id,))
        cur.execute("DELETE FROM unified_files WHERE id=%s", (receipt_id,))
        cur.execute(
            (
                "INSERT INTO unified_files (id, file_type, created_at, updated_at, merchant_name, orgnr, "
                "purchase_datetime, gross_amount, net_amount, ai_status, ai_confidence, submitted_by) "
                "VALUES (%s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
            (
                receipt_id,
                'receipt',
                'Contract Test Merchant',
                None,
                purchase_dt,
                account_total,
                account_total,
                'completed',
                0.95,
                'contract-tester',
            ),
        )
        cur.execute(
            (
                "INSERT INTO ai_accounting_proposals (receipt_id, account_code, debit, credit, vat_rate, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            ),
            (receipt_id, '5790', account_total, 0, None, 'Expense account'),
        )
        cur.execute(
            (
                "INSERT INTO ai_accounting_proposals (receipt_id, account_code, debit, credit, vat_rate, notes) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            ),
            (receipt_id, '2440', 0, account_total, None, 'Liability account'),
        )
    return receipt_id


def test_export_sie_returns_valid_sie(app: Flask):
    receipt_id = _seed_completed_receipt()
    client = app.test_client()

    response = client.get("/export/sie?from=2025-08-01&to=2025-08-31")
    assert response.status_code == 200

    content = response.get_data(as_text=True)
    assert '#FLAGGA 0' in content
    assert '#SIETYP 4' in content
    assert '#VER' in content and receipt_id[:8] not in content  # ensure anonymized text but ver exists
    assert '#TRANS 5790' in content
    assert '#TRANS 2440' in content
    assert '-25.50' in content

    cd = response.headers.get('Content-Disposition', '')
    assert 'attachment' in cd and cd.endswith('.sie')

    with db_cursor() as cur:
        cur.execute("DELETE FROM ai_accounting_proposals WHERE receipt_id=%s", (receipt_id,))
        cur.execute("DELETE FROM unified_files WHERE id=%s", (receipt_id,))
