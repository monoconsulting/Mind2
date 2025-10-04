import json

import pytest

from services import tasks
from services.invoice_status import InvoiceProcessingStatus


def test_get_invoice_parent_id_filters_non_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    info_map = {
        "receipt-1": {"id": "receipt-1", "file_type": "receipt", "original_file_id": "receipt-1", "other_data": {}},
        "page-1": {"id": "page-1", "file_type": "invoice_page", "original_file_id": "inv-1", "other_data": {}},
        "inv-1": {"id": "inv-1", "file_type": "invoice", "original_file_id": "inv-1", "other_data": {}},
    }

    monkeypatch.setattr(tasks, "_load_unified_file_info", lambda fid: info_map.get(fid))

    assert tasks._get_invoice_parent_id("receipt-1") is None
    assert tasks._get_invoice_parent_id("page-1") == "inv-1"
    assert tasks._get_invoice_parent_id("inv-1") == "inv-1"


def test_maybe_advance_invoice_tracks_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_store: dict[str, dict[str, object]] = {
        "inv-1": {
            "page_ids": ["page-1", "page-2"],
            "page_count": 2,
            "processing_status": "ocr_pending",
        }
    }
    info_map = {
        "page-1": {"id": "page-1", "file_type": "invoice_page", "original_file_id": "inv-1", "other_data": {}},
        "page-2": {"id": "page-2", "file_type": "invoice_page", "original_file_id": "inv-1", "other_data": {}},
    }
    transitions: list[tuple[str, InvoiceProcessingStatus, tuple[InvoiceProcessingStatus, ...]]] = []
    scheduled: list[str] = []

    def load_file(fid: str):
        return info_map.get(fid)

    def load_metadata(invoice_id: str):
        entry = metadata_store.get(invoice_id)
        return json.loads(json.dumps(entry)) if entry is not None else {}

    def update_metadata(invoice_id: str, metadata: dict[str, object]) -> bool:
        metadata_store[invoice_id] = json.loads(json.dumps(metadata))
        return True

    def set_field(invoice_id: str, field: str, value: object):
        metadata_store.setdefault(invoice_id, {})[field] = value
        return metadata_store[invoice_id]

    def enqueue(invoice_id: str) -> bool:
        scheduled.append(invoice_id)
        return True

    def transition(invoice_id: str, target: InvoiceProcessingStatus, allowed: tuple[InvoiceProcessingStatus, ...]) -> bool:
        transitions.append((invoice_id, target, allowed))
        return True

    monkeypatch.setattr(tasks, "_load_unified_file_info", load_file)
    monkeypatch.setattr(tasks, "_load_invoice_metadata", load_metadata)
    monkeypatch.setattr(tasks, "_update_invoice_metadata", update_metadata)
    monkeypatch.setattr(tasks, "_set_invoice_metadata_field", set_field)
    monkeypatch.setattr(tasks, "_enqueue_invoice_document", enqueue)
    monkeypatch.setattr(tasks, "transition_processing_status", transition)

    tasks._maybe_advance_invoice_from_file("page-1", success=True)

    meta_first = metadata_store["inv-1"]
    page_status_first = meta_first.get("page_status") or {}
    assert page_status_first.get("page-1") == "ocr_done"
    assert meta_first.get("ocr_completed_pages") == 1
    assert meta_first.get("processing_status") == InvoiceProcessingStatus.OCR_PENDING.value
    assert len(transitions) == 1
    assert transitions[0][1] == InvoiceProcessingStatus.OCR_PENDING
    assert scheduled == []

    tasks._maybe_advance_invoice_from_file("page-2", success=True)

    meta_second = metadata_store["inv-1"]
    assert meta_second.get("ocr_completed_pages") == 2
    assert meta_second.get("processing_status") == InvoiceProcessingStatus.OCR_DONE.value
    assert meta_second.get("invoice_document_scheduled") is True
    assert scheduled == ["inv-1"]
    assert transitions[-1][1] == InvoiceProcessingStatus.OCR_DONE
    allowed_states = transitions[-1][2]
    assert InvoiceProcessingStatus.OCR_DONE in allowed_states


def test_maybe_advance_invoice_failure_marks_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_store: dict[str, dict[str, object]] = {
        "inv-2": {
            "page_ids": ["page-x"],
            "page_count": 1,
        }
    }
    info_map = {
        "page-x": {"id": "page-x", "file_type": "invoice_page", "original_file_id": "inv-2", "other_data": {}},
    }
    transitions: list[InvoiceProcessingStatus] = []
    scheduled: list[str] = []

    def load_metadata(invoice_id: str):
        entry = metadata_store.get(invoice_id)
        return json.loads(json.dumps(entry)) if entry is not None else {}

    def update_metadata(invoice_id: str, metadata: dict[str, object]) -> bool:
        metadata_store[invoice_id] = json.loads(json.dumps(metadata))
        return True

    def set_field(invoice_id: str, field: str, value: object):
        metadata_store.setdefault(invoice_id, {})[field] = value
        return metadata_store[invoice_id]

    def enqueue(invoice_id: str) -> bool:
        scheduled.append(invoice_id)
        return True

    monkeypatch.setattr(tasks, "_load_unified_file_info", lambda fid: info_map.get(fid))
    monkeypatch.setattr(tasks, "_load_invoice_metadata", load_metadata)
    monkeypatch.setattr(tasks, "_update_invoice_metadata", update_metadata)
    monkeypatch.setattr(tasks, "_set_invoice_metadata_field", set_field)
    monkeypatch.setattr(tasks, "_enqueue_invoice_document", enqueue)

    def transition(invoice_id: str, target: InvoiceProcessingStatus, allowed: tuple[InvoiceProcessingStatus, ...]) -> bool:
        transitions.append(target)
        return True

    monkeypatch.setattr(tasks, "transition_processing_status", transition)

    tasks._maybe_advance_invoice_from_file("page-x", success=False)

    meta = metadata_store["inv-2"]
    page_status = meta.get("page_status") or {}
    assert page_status.get("page-x") == "ocr_failed"
    assert meta.get("processing_status") == InvoiceProcessingStatus.FAILED.value
    assert InvoiceProcessingStatus.FAILED in transitions
    assert scheduled == []
