from __future__ import annotations

import io
import json
import os
from typing import Any

import pytest
from flask import Flask


@pytest.fixture()
def app() -> Flask:
    from api.app import app as flask_app
    return flask_app


def test_capture_upload_saves_files_and_returns_id(app: Flask, tmp_path) -> None:
    client = app.test_client()
    # ensure storage dir temp
    os.environ['STORAGE_DIR'] = str(tmp_path)
    data: dict[str, Any] = {
        'tags': (None, json.dumps(['travel', 'food'])),
        'images': (io.BytesIO(b'abc'), 'one.jpg'),
    }
    resp = client.post('/capture/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200, resp.data
    body = resp.get_json()
    assert body and body.get('ok') is True
    rid = body['receipt_id']
    assert isinstance(rid, str) and len(rid) > 0
    # check file saved
    saved = body.get('saved') or []
    assert saved and isinstance(saved, list)
    # verify path exists
    for name in saved:
        p = tmp_path / rid / name
        assert p.exists()
