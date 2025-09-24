import sys
from pathlib import Path
import statistics
import time

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

api_app = import_module("api.app")


def measure_latency(client, method: str, path: str, iterations: int = 50):
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            resp = client.post(path, json={})
        else:
            raise ValueError("Unsupported method")
        end = time.perf_counter()
        assert resp.status_code in (200, 204)
        latencies.append((end - start) * 1000.0)
    return latencies


def test_ingest_upload_p95_under_200ms():
    app = api_app.app
    client = app.test_client()

    latencies = measure_latency(client, "POST", "/ingest/upload", iterations=30)
    latencies.sort()
    # p95 index
    p95 = latencies[int(0.95 * len(latencies)) - 1]
    assert p95 < 200.0


def test_metrics_endpoint_fast():
    app = api_app.app
    client = app.test_client()

    latencies = measure_latency(client, "GET", "/system/metrics", iterations=10)
    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies)) - 1]
    assert p95 < 200.0
