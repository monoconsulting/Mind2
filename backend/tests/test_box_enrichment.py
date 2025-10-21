import json
import os
from pathlib import Path
import types

import pytest

import backend.src.services.box_enrichment as be


@pytest.fixture
def temp_storage(tmp_path: Path):
    # Create a fake receipt directory with minimal OCR boxes
    rid = "R-TEST-001"
    rdir = tmp_path / rid
    rdir.mkdir(parents=True)
    ocr_boxes = [
        {"x": 10, "y": 20, "w": 100, "h": 24, "field": "Acme AB", "confidence": 0.91},
        {"x": 12, "y": 56, "w": 90,  "h": 22, "field": "Org.nr 556677-8899", "confidence": 0.88},
        {"x": 15, "y": 98, "w": 80,  "h": 22, "field": "Total: 123,45 SEK", "confidence": 0.93},
        {"x": 16, "y": 140,"w": 70,  "h": 22, "field": "2025-10-01 12:34", "confidence": 0.85},
        {"x": 18, "y": 170,"w": 75,  "h": 22, "field": "Random note", "confidence": 0.50},
    ]
    (rdir / "ocr_boxes.json").write_text(json.dumps(ocr_boxes, ensure_ascii=False, indent=2), encoding="utf-8")
    return rid, tmp_path


def test_enrichment_maps_semantic_fields(monkeypatch: pytest.MonkeyPatch, temp_storage):
    rid, tmp_root = temp_storage

    # Monkeypatch data loaders to avoid DB
    def fake_load_receipt(_rid: str):
        assert _rid == rid
        return {
            "gross_amount": 123.45,
            "net_amount": 98.76,
            "currency": "SEK",
            "purchase_datetime": "2025-10-01T12:34:00",
            "payment_type": "card",
            "expense_type": "corporate",
            "receipt_number": "A-42",
            "total_vat_25": 24.69,
            "total_vat_12": None,
            "total_vat_6": None,
        }

    def fake_load_company(_rid: str):
        assert _rid == rid
        return {
            "name": "Acme AB",
            "orgnr": "556677-8899",
            "address": "Storgatan 1",
            "zip": "11122",
            "city": "Stockholm",
            "country": "SE",
            "phone": None,
            "www": None,
            "email": None,
        }

    monkeypatch.setattr(be, "_load_receipt", fake_load_receipt)
    monkeypatch.setattr(be, "_load_company", fake_load_company)

    stats = be.run_box_enrichment(receipt_id=rid, storage_dir=tmp_root)
    assert stats["success"] is True
    assert stats["total_boxes"] == 5
    assert stats["matched_boxes"] >= 3  # company name, orgnr, total/amount should match
    assert 0.0 <= stats["match_rate"] <= 1.0

    # Validate output file
    out = (tmp_root / rid / "boxes.json").read_text(encoding="utf-8")
    boxes = json.loads(out)
    assert isinstance(boxes, list) and len(boxes) == 5

    # Check some specific mappings
    fields = {b["field"] for b in boxes}
    assert "company.name" in fields
    assert "company.orgnr" in fields
    # Allow amount text to map to either gross or net depending on OCR text, but must be semantic if numeric overlap
    assert any(f.startswith("receipt.") for f in fields)

    # Ensure unmapped text remains unmapped with 0.0 confidence
    random_box = next(b for b in boxes if b["ocr_text"] == "Random note")
    assert random_box["field"] == "Random note"
    assert random_box["match_confidence"] == 0.0


def test_handles_missing_ocr_file_gracefully(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    rid = "R-NO-OCR"
    # No ocr_boxes.json written

    # Return some data (they should be ignored due to no OCR boxes)
    monkeypatch.setattr(be, "_load_receipt", lambda _rid: {"gross_amount": 10})
    monkeypatch.setattr(be, "_load_company", lambda _rid: {"name": "X"})

    stats = be.run_box_enrichment(receipt_id=rid, storage_dir=tmp_path)
    assert stats["success"] is True
    assert stats["total_boxes"] == 0
    assert stats["matched_boxes"] == 0
    assert stats["unmatched_boxes"] == 0
    assert stats["match_rate"] == 0.0


def test_invalid_ocr_json_is_reported(tmp_path: Path):
    rid = "R-BAD-JSON"
    rdir = tmp_path / rid
    rdir.mkdir(parents=True)
    (rdir / "ocr_boxes.json").write_text("{invalid json", encoding="utf-8")

    stats = be.run_box_enrichment(receipt_id=rid, storage_dir=tmp_path)
    assert stats["success"] is False
    assert stats["error"] == "read_error"
    assert stats["total_boxes"] == 0
