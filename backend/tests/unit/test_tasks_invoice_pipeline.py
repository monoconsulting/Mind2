import pytest

from services import tasks


class StubDelayTask:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def delay(self, identifier: str) -> None:
        self.calls.append(identifier)


def test_process_ocr_routes_invoice_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_ai = StubDelayTask()
    monkeypatch.setattr(tasks, "process_invoice_ai_extraction", stub_ai)

    class FailPipeline:
        def delay(self, *_args, **_kwargs):
            raise AssertionError("receipt pipeline should not be triggered for invoices")

    monkeypatch.setattr(tasks, "process_ai_pipeline", FailPipeline())
    monkeypatch.setattr(tasks, "_get_file_type", lambda fid: "invoice_page")
    monkeypatch.setattr(tasks, "_get_invoice_parent_id", lambda fid, ft: "inv-1")
    monkeypatch.setattr(tasks, "_update_file_fields", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_update_file_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_invoice_page_progress", lambda invoice_id: (1, 1))
    monkeypatch.setattr(tasks, "_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "transition_processing_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "transition_document_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "run_ocr", lambda fid, base: {"text": "hello"})

    result = tasks.process_ocr("page-1")

    assert result["invoice_id"] == "inv-1"
    assert result["pages_completed"] == 1
    assert result["pages_total"] == 1
    assert stub_ai.calls == ["inv-1"]


def test_process_ocr_receipt_still_triggers_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline_calls: list[str] = []

    class StubPipeline:
        def delay(self, file_id: str) -> None:
            pipeline_calls.append(file_id)

    monkeypatch.setattr(tasks, "process_ai_pipeline", StubPipeline())
    monkeypatch.setattr(tasks, "_get_file_type", lambda fid: "receipt")
    monkeypatch.setattr(tasks, "_get_invoice_parent_id", lambda fid, ft: None)
    monkeypatch.setattr(tasks, "_update_file_fields", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_update_file_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "run_ocr", lambda fid, base: {"text": "hello"})

    result = tasks.process_ocr("receipt-1")

    assert result["status"] == "ocr_done"
    assert pipeline_calls == ["receipt-1"]


def test_process_ocr_invoice_failure_marks_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    failure_calls: list[tuple[str, str | None]] = []

    def record_failure(invoice_id: str, error: str | None) -> None:
        failure_calls.append((invoice_id, error))

    monkeypatch.setattr(tasks, "_get_file_type", lambda fid: "invoice")
    monkeypatch.setattr(tasks, "_get_invoice_parent_id", lambda fid, ft: "inv-2")
    monkeypatch.setattr(tasks, "_update_file_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "_fail_invoice_processing", record_failure)
    monkeypatch.setattr(tasks, "transition_processing_status", lambda *args, **kwargs: True)

    def failing_run_ocr(_fid: str, _base: str) -> dict[str, str]:
        raise RuntimeError("ocr boom")

    monkeypatch.setattr(tasks, "run_ocr", failing_run_ocr)

    result = tasks.process_ocr("inv-2")

    assert result["ok"] is False
    assert failure_calls == [("inv-2", "RuntimeError: ocr boom")]


def test_get_invoice_parent_id_ignores_receipts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "db_cursor", None)

    assert tasks._get_invoice_parent_id("receipt-1", "receipt") is None
    assert tasks._get_invoice_parent_id("something", None) is None
