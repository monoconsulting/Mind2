import pytest


@pytest.fixture()
def task_module(monkeypatch):
    from services import tasks as tasks_module

    monkeypatch.setattr(tasks_module, "_history", lambda *args, **kwargs: None)
    return tasks_module


def test_process_invoice_document_updates_state_and_schedules(monkeypatch, task_module):
    recorded = {"processing": [], "document": [], "metadata": [], "scheduled": []}

    def fake_transition_processing_status(document_id, target, allowed):
        recorded["processing"].append((document_id, target, tuple(allowed)))
        if target == task_module.InvoiceProcessingStatus.AI_PROCESSING:
            return True
        if target == task_module.InvoiceProcessingStatus.READY_FOR_MATCHING:
            return True
        return False

    def fake_transition_document_status(document_id, target, allowed):
        recorded["document"].append((document_id, target, tuple(allowed)))
        return True

    monkeypatch.setattr(task_module, "transition_processing_status", fake_transition_processing_status)
    monkeypatch.setattr(task_module, "transition_document_status", fake_transition_document_status)
    monkeypatch.setattr(
        task_module,
        "_set_invoice_metadata_field",
        lambda document_id, key, value: recorded["metadata"].append((document_id, key, value)),
    )

    class StubTask:
        def delay(self, document_id):
            recorded["scheduled"].append(document_id)

        def run(self, document_id):
            recorded["scheduled"].append(document_id)

    monkeypatch.setattr(task_module, "process_invoice_matching", StubTask())

    result = task_module.process_invoice_document("doc-123")

    assert result["ok"] is True
    assert result["status"] == task_module.InvoiceProcessingStatus.READY_FOR_MATCHING.value
    assert [entry[1] for entry in recorded["processing"]] == [
        task_module.InvoiceProcessingStatus.AI_PROCESSING,
        task_module.InvoiceProcessingStatus.READY_FOR_MATCHING,
    ]
    assert recorded["metadata"] == [
        ("doc-123", "processing_status", task_module.InvoiceProcessingStatus.AI_PROCESSING.value),
        ("doc-123", "processing_status", task_module.InvoiceProcessingStatus.READY_FOR_MATCHING.value),
    ]
    assert recorded["document"] == [
        (
            "doc-123",
            task_module.InvoiceDocumentStatus.MATCHING,
            (task_module.InvoiceDocumentStatus.IMPORTED,),
        )
    ]
    assert recorded["scheduled"] == ["doc-123"]
