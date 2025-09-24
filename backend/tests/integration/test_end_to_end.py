import requests


def test_end_to_end_quickstart_flow(base_url):
    # 1) Submit a sample receipt (placeholder: expect 404/501 until implemented)
    # Assuming future upload endpoint /ingest/upload (not yet specified in contracts)
    upload_url = f"{base_url}/ingest/upload"
    r1 = requests.post(upload_url, timeout=5)
    assert r1.status_code == 200, f"Expected 200 from {upload_url}, got {r1.status_code}"

    # 2) Check status transitions (requires /receipts)
    list_url = f"{base_url}/receipts"
    r2 = requests.get(list_url, timeout=5)
    assert r2.status_code == 200

    # 3) Admin detail edit flow (requires /receipts/{id})
    # Placeholder: no id available yet, just assert endpoint exists semantics by 404 on fake id
    detail_url = f"{base_url}/receipts/TEST-ID"
    r3 = requests.get(detail_url, timeout=5)
    assert r3.status_code == 200

    # 4) Company card matching
    match_url = f"{base_url}/reconciliation/firstcard/match"
    r4 = requests.post(match_url, timeout=5)
    assert r4.status_code == 200

    # 5) SIE export
    export_url = f"{base_url}/export/sie?from=2025-08-01&to=2025-08-31"
    r5 = requests.get(export_url, timeout=5)
    assert r5.status_code == 200
