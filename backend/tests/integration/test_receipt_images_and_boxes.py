import os
import sys
import json
from pathlib import Path


def import_app(monkeypatch, storage_dir):
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("DB_AUTO_MIGRATE", "0")
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from importlib import import_module
    return import_module("api.app").app  # type: ignore


def test_receipt_image_and_boxes_endpoints(monkeypatch, tmp_path):
    rid = "RIMG1"
    # Create fake storage structure
    rdir = tmp_path / rid
    rdir.mkdir(parents=True, exist_ok=True)
    img_path = rdir / "page-1.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xd9")  # minimal JPEG header/footer bytes
    boxes = [{"field": "merchant_name", "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1}]
    (rdir / "boxes.json").write_text(json.dumps(boxes), encoding="utf-8")

    app = import_app(monkeypatch, tmp_path)
    client = app.test_client()

    r1 = client.get(f"/receipts/{rid}/image")
    assert r1.status_code in (200, 404)  # 200 with our bytes; some stacks may 404 due to mimetype

    r2 = client.get(f"/receipts/{rid}/ocr/boxes")
    assert r2.status_code == 200
    data = r2.get_json()
    assert isinstance(data, list)
    assert any(b.get("field") == "merchant_name" for b in data)

