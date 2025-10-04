import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from importlib import import_module  # noqa: E402

services_storage = import_module("services.storage")
FileStorage = services_storage.FileStorage


def test_file_storage_crud(tmp_path: Path):
    store = FileStorage(tmp_path)
    rid = "R123"
    name = "page1.png"
    data = b"hello"

    # save
    p = store.save(rid, name, data)
    assert p.exists()

    # list
    files = store.list(rid)
    assert files == [name]

    # load
    loaded = store.load(rid, name)
    assert loaded == data

    # delete
    assert store.delete(rid, name) is True
    assert store.list(rid) == []


def test_file_storage_protects_traversal(tmp_path: Path):
    store = FileStorage(tmp_path)
    rid = "R123"
    # attempt path traversal in filename
    try:
        store.save(rid, "../evil.txt", b"x")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_file_storage_adopt_is_idempotent(tmp_path: Path):
    store = FileStorage(tmp_path)
    rid = "R555"
    original = tmp_path / "temp_page.png"
    original.write_bytes(b"page-bytes")

    dest = store.adopt(rid, "page-0001.png", original)
    assert dest.exists()
    assert dest.read_bytes() == b"page-bytes"
    assert not original.exists()

    # Call again with the already-moved file to ensure the method is idempotent
    dest_again = store.adopt(rid, "page-0001.png", dest)
    assert dest_again == dest
    assert dest_again.exists()
