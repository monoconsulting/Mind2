import requests
import yaml


def test_firstcard_import_and_match_exists(base_url):
    with open(
        "specs/001-mind-system-receipt/contracts/reconciliation_firstcard.yaml",
        "r",
        encoding="utf-8",
    ) as f:
        spec = yaml.safe_load(f)
    assert "/reconciliation/firstcard/import" in spec["paths"]
    assert "/reconciliation/firstcard/match" in spec["paths"]

    # Calls expected to fail until implemented
    for path in [
        "/reconciliation/firstcard/import",
        "/reconciliation/firstcard/match",
    ]:
        url = f"{base_url}{path}"
        resp = requests.post(url, timeout=5)
        assert resp.status_code == 200, f"Expected 200 from {url}, got {resp.status_code}"
