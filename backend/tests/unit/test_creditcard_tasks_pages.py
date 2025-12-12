import os
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.tasks import creditcard_tasks as ct


def _make_page(idx: int, tmpdir: Path) -> SimpleNamespace:
    path = tmpdir / f"p{idx}.png"
    path.write_bytes(b"page-bytes")
    return SimpleNamespace(index=idx, bytes=b"page-bytes", path=path)


def test_ensure_creditcard_pages_adds_source_and_workflow(tmp_path):
    """
    Regression: PDF page creation must pass required 'source' and workflow_type to create_unified_file.
    """
    base = tmp_path
    originals = base / "originals"
    originals.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    original_name = f"{file_id}.pdf"
    (originals / original_name).write_bytes(b"pdf-bytes")

    # Patch FileStorage to point to our temp base and keep adopt as no-op.
    class FakeStorage:
        def __init__(self, *_):
            self.base = base

        def adopt(self, *_args, **_kwargs):
            return None

    created_calls = []

    def fake_create_unified_file(**kwargs):
        created_calls.append(kwargs)
        return MagicMock()

    with patch.object(ct, "FileStorage", FakeStorage), patch.object(
        ct, "pdf_to_png_pages", return_value=[_make_page(0, base)]
    ), patch.object(ct, "create_unified_file", side_effect=fake_create_unified_file):
        parent = {
            "file_type": "cc_pdf",
            "workflow_type": "creditcard_invoice",
            "mime_type": "application/pdf",
            "original_file_name": original_name,
            "other_data": {},
        }
        combined, other = ct._ensure_creditcard_pages_and_ocr(file_id, parent)

    # Ensure conversion succeeded and we produced a page entry
    assert created_calls, "create_unified_file should be called for generated pages"
    call_kwargs = created_calls[0]
    assert call_kwargs["source"] == "fc_pdf_split"
    assert call_kwargs["workflow_type"] == "creditcard_invoice"
    assert call_kwargs["file_type"] == "cc_image"
    assert "page_number" in call_kwargs["extra_metadata"]
    assert other.get("pages"), "pages metadata should be populated"

    # No OCR text provided in this stubbed path
    assert combined == ""
