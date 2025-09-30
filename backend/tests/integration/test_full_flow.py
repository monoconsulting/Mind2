from __future__ import annotations

import io
import json
import os
from datetime import datetime, timezone

import pytest
from flask import Flask

from services.db.connection import db_cursor
from services.tasks import process_ai_pipeline


@pytest.fixture()
def app() -> Flask:
    from api.app import app as flask_app
    return flask_app


def test_full_flow_capture_to_export(app: Flask, tmp_path):
    """End-to-end test: capture->AI->review->approve->export"""
    client = app.test_client()

    # Set temp storage for this test
    os.environ['STORAGE_DIR'] = str(tmp_path)

    # 1. Capture: Upload an image with tags
    data = {
        'tags': (None, json.dumps(['travel', 'meal'])),
        'images': (io.BytesIO(b'fake_image_data'), 'receipt.jpg'),
    }
    resp = client.post('/capture/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body and body.get('ok') is True
    receipt_id = body['receipt_id']

    # 2. Review: Update receipt with manual edits (simulating reviewer corrections)
    today_iso = datetime.now(timezone.utc).date().isoformat()
    update_data = {
        'merchant_name': 'Coffee Shop',
        'gross_amount': 25.50,
        'net_amount': 25.50,
        'purchase_date': today_iso,
    }
    resp2 = client.patch(f'/receipts/{receipt_id}', json=update_data)
    assert resp2.status_code == 200

    # Run AI pipeline explicitly (normally Celery-driven)
    pipeline = process_ai_pipeline.run(receipt_id)  # type: ignore[attr-defined]
    assert set(pipeline['completed']) >= {'AI1', 'AI2', 'AI3', 'AI4'}
    if 'AI5' not in pipeline['completed']:
        assert any(err['stage'] == 'AI5' for err in pipeline['errors'])

    detail_resp = client.get(f'/receipts/{receipt_id}')
    assert detail_resp.status_code == 200
    detail = detail_resp.get_json()
    assert detail['ai_status'] == 'ai5_completed'

    with db_cursor() as cur:
        cur.execute(
            "SELECT account_code, debit, credit FROM ai_accounting_proposals WHERE receipt_id=%s ORDER BY id ASC",
            (receipt_id,),
        )
        proposals = cur.fetchall()
    assert proposals
    accounts = {row[0] for row in proposals}
    assert '5790' in accounts
    assert '2440' in accounts
    total_debit = sum(float(row[1] or 0) for row in proposals)
    total_credit = sum(float(row[2] or 0) for row in proposals)
    assert round(total_debit, 2) == 25.50
    assert round(total_credit, 2) == 25.50

    proposals_resp = client.get(f'/receipts/{receipt_id}/accounting/proposal')
    assert proposals_resp.status_code == 200
    proposal_payload = proposals_resp.get_json()
    assert proposal_payload['entries']
    updated_entries = proposal_payload['entries']
    updated_entries[0]['notes'] = 'Adjusted entry'
    put_resp = client.put(
        f'/receipts/{receipt_id}/accounting/proposal',
        json={'entries': updated_entries},
    )
    assert put_resp.status_code == 200
    proposal_after = client.get(f'/receipts/{receipt_id}/accounting/proposal').get_json()
    assert proposal_after['entries'][0]['notes'] == 'Adjusted entry'

    # Add line items during review
    line_items = [
        {'desc': 'Coffee', 'amount': 15.50, 'account': '5610'},
        {'desc': 'Pastry', 'amount': 10.00, 'account': '5610'}
    ]
    resp3 = client.put(f'/receipts/{receipt_id}/line-items', json=line_items)
    assert resp3.status_code == 200

    # 3. Approve: Mark receipt as completed
    approve_data = {'status': 'completed'}
    resp4 = client.patch(f'/receipts/{receipt_id}', json=approve_data)
    assert resp4.status_code == 200

    # 4. Export: Generate SIE file containing the approved entries
    resp5 = client.get('/export/sie?from=2025-01-01&to=2025-12-31')
    assert resp5.status_code == 200
    assert 'attachment' in resp5.headers.get('Content-Disposition', '')
    assert resp5.headers.get('X-Export-Job-Id')

    content = resp5.get_data(as_text=True)
    assert '#FLAGGA 0' in content
    assert '#VER' in content
    assert '#TRANS 5790' in content
    assert '#TRANS 2440' in content
    assert '-25.50' in content

    # 5. Verify line items persisted to file storage
    resp7 = client.get(f'/receipts/{receipt_id}/line-items')
    assert resp7.status_code == 200
    items = resp7.get_json()['line_items']
    assert len(items) == 2
    assert items[0]['desc'] == 'Coffee'

    # 6. Verify file was saved to storage
    receipt_dir = tmp_path / receipt_id
    assert receipt_dir.exists()
    saved_files = list(receipt_dir.glob('page-*'))
    assert len(saved_files) >= 1

    # 7. Verify line items file exists
    line_items_dir = tmp_path / 'line_items'
    assert line_items_dir.exists()
    line_items_file = line_items_dir / f'{receipt_id}.json'
    assert line_items_file.exists()



