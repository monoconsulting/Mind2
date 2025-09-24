import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

api_app = import_module("api.app")


def test_system_metrics_endpoint_exposes_prometheus_text():
    app = api_app.app
    client = app.test_client()
    res = client.get("/system/metrics")
    assert res.status_code == 200
    text = res.data.decode("utf-8")
    # Basic check for Prometheus exposition format
    assert "# HELP" in text and "mind_api_requests_total" in text
