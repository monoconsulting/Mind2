import requests
import yaml


def test_receipts_api_contract_list_exists(base_url):
    with open("specs/001-mind-system-receipt/contracts/receipts.yaml", "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    assert "/receipts" in spec["paths"], "OpenAPI must define /receipts"

    # This will fail until the service is implemented and running
    url = f"{base_url}/receipts"
    resp = requests.get(url, timeout=5)
    assert resp.status_code == 200, f"Expected 200 from {url}, got {resp.status_code}"
