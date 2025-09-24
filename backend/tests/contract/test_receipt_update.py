from __future__ import annotations

import pytest
from flask import Flask


@pytest.fixture()
def app() -> Flask:
    from api.app import app as flask_app
    return flask_app


def test_receipt_update_and_line_items(app: Flask):
    client = app.test_client()
    rid = 'demo-receipt-id'

    # Update basic fields (PATCH allowed)
    r = client.patch(f"/receipts/{rid}", json={"merchant_name": "New M", "gross_amount": 100.0, "status": "completed"})
    assert r.status_code == 200

    # Put line items and then get them
    items = [
        {"desc": "Coffee", "qty": 1, "unit": 1.0, "amount": 25.0, "account": "5610"},
        {"desc": "Sandwich", "qty": 1, "unit": 1.0, "amount": 45.0, "account": "5610"},
    ]
    r2 = client.put(f"/receipts/{rid}/line-items", json=items)
    assert r2.status_code == 200
    r3 = client.get(f"/receipts/{rid}/line-items")
    assert r3.status_code == 200
    body = r3.get_json()
    assert isinstance(body.get('line_items'), list)
