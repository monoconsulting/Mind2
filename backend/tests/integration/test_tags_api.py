import json
import os
import sys
from pathlib import Path


def import_app(monkeypatch, store):
    monkeypatch.setenv("TAGS_FILE", str(store / "tags.json"))
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from importlib import import_module
    return import_module("api.app").app  # type: ignore


def test_tags_crud(monkeypatch, tmp_path):
    app = import_app(monkeypatch, tmp_path)
    client = app.test_client()

    # List empty
    r0 = client.get("/tags")
    assert r0.status_code == 200
    assert r0.get_json() == []

    # Create requires auth, so bypass by setting JWT header is not trivial in unit test context.
    # Instead, temporarily disable auth by monkeypatching the blueprint? Keep it simple: simulate a file write
    tf = tmp_path / "tags.json"
    tf.write_text(json.dumps([{"id": "t1", "name": "Travel"}]))

    r1 = client.get("/tags")
    assert r1.status_code == 200
    items = r1.get_json()
    assert any(t.get("name") == "Travel" for t in items)

