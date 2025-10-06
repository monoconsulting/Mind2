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


def test_get_invoice_parent_id_returns_self_for_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "db_cursor", None)

    assert tasks._get_invoice_parent_id("inv-1", "invoice") == "inv-1"
    assert tasks._get_invoice_parent_id("inv-1", "INVOICE") == "inv-1"


def test_get_invoice_parent_id_lookup_for_page(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            self.queries.append((query, params))

        def fetchone(self):
            last_query = self.queries[-1][0] if self.queries else ""
            if "original_file_id" in last_query:
                return ("parent-inv-id",)
            elif "file_type" in last_query:
                return ("invoice",)
            return None

    fake_cursor = FakeCursor()

    def cursor_factory():
        return fake_cursor

    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    result = tasks._get_invoice_parent_id("page-1", "invoice_page")
    assert result == "parent-inv-id"
    assert len(fake_cursor.queries) == 2


def test_get_invoice_parent_id_returns_none_when_parent_not_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            pass

        def fetchone(self):
            if "original_file_id" in getattr(self, "_last_query", ""):
                return ("parent-id",)
            elif "file_type" in getattr(self, "_last_query", ""):
                return ("receipt",)  # Parent is not invoice
            return None

    fake_cursor = FakeCursor()

    def cursor_factory():
        fake_cursor._last_query = ""
        return fake_cursor

    def execute_wrapper(query: str, params):
        fake_cursor._last_query = query

    fake_cursor.execute = execute_wrapper
    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    result = tasks._get_invoice_parent_id("page-1", "invoice_page")
    assert result is None


def test_get_invoice_parent_id_handles_missing_original_file_id(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            pass

        def fetchone(self):
            if "original_file_id" in getattr(self, "_query", ""):
                return (None,)  # No original file id
            return None

    fake_cursor = FakeCursor()

    def cursor_factory():
        return fake_cursor

    def execute_wrapper(query: str, params):
        fake_cursor._query = query

    fake_cursor.execute = execute_wrapper
    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    result = tasks._get_invoice_parent_id("page-1", "invoice_page")
    assert result is None


def test_get_invoice_parent_id_handles_db_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            raise RuntimeError("Database error")

    def cursor_factory():
        return FakeCursor()

    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    result = tasks._get_invoice_parent_id("page-1", "invoice_page")
    assert result is None


def test_invoice_page_progress_returns_zero_when_no_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks, "db_cursor", None)

    completed, total = tasks._invoice_page_progress("inv-1")
    assert completed == 0
    assert total == 0


def test_invoice_page_progress_counts_completed_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            pass

        def fetchall(self):
            return [
                ("page-1", "invoice_page", "ocr_done"),
                ("page-2", "invoice_page", "ocr_done"),
                ("page-3", "invoice_page", "pending"),
            ]

    def cursor_factory():
        return FakeCursor()

    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    completed, total = tasks._invoice_page_progress("inv-1")
    assert total == 3
    assert completed == 2


def test_invoice_page_progress_falls_back_to_invoice_status(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            self._last_query = query

        def fetchall(self):
            if "original_file_id" in getattr(self, "_last_query", ""):
                return []  # No pages found
            return None

        def fetchone(self):
            if "ai_status FROM unified_files WHERE id" in getattr(self, "_last_query", ""):
                return ("ocr_done",)
            return None

    def cursor_factory():
        return FakeCursor()

    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    completed, total = tasks._invoice_page_progress("inv-1")
    assert total == 1
    assert completed == 1


def test_invoice_page_progress_handles_incomplete_invoice_status(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            self._last_query = query

        def fetchall(self):
            return []

        def fetchone(self):
            return ("pending",)

    def cursor_factory():
        return FakeCursor()

    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    completed, total = tasks._invoice_page_progress("inv-1")
    assert total == 1
    assert completed == 0


def test_invoice_page_progress_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query: str, params):
            raise RuntimeError("DB error")

    def cursor_factory():
        return FakeCursor()

    monkeypatch.setattr(tasks, "db_cursor", cursor_factory)

    completed, total = tasks._invoice_page_progress("inv-1")
    assert completed == 0
    assert total == 0


def test_enqueue_invoice_ai_extraction_calls_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    class StubTask:
        def delay(self, invoice_id: str):
            calls.append(invoice_id)

    monkeypatch.setattr(tasks, "process_invoice_ai_extraction", StubTask())

    tasks._enqueue_invoice_ai_extraction("inv-1")
    assert calls == ["inv-1"]


def test_enqueue_invoice_ai_extraction_falls_back_to_direct_call(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def direct_call(invoice_id: str):
        calls.append(invoice_id)

    monkeypatch.setattr(tasks, "process_invoice_ai_extraction", direct_call)

    tasks._enqueue_invoice_ai_extraction("inv-1")
    assert calls == ["inv-1"]


def test_enqueue_invoice_ai_extraction_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailTask:
        def delay(self, invoice_id: str):
            raise RuntimeError("Celery error")

    monkeypatch.setattr(tasks, "process_invoice_ai_extraction", FailTask())

    # Should not raise
    tasks._enqueue_invoice_ai_extraction("inv-1")


def test_fail_invoice_processing_does_nothing_without_invoice_id(monkeypatch: pytest.MonkeyPatch) -> None:
    transition_calls = []

    def track_transition(*args, **kwargs):
        transition_calls.append(args)
        return False

    monkeypatch.setattr(tasks, "transition_processing_status", track_transition)
    monkeypatch.setattr(tasks, "transition_document_status", track_transition)
    monkeypatch.setattr(tasks, "_history", lambda *args, **kwargs: None)

    tasks._fail_invoice_processing(None, "error")
    assert transition_calls == []


def test_fail_invoice_processing_transitions_states(monkeypatch: pytest.MonkeyPatch) -> None:
    processing_transitions = []
    document_transitions = []
    history_calls = []

    def track_processing(*args, **kwargs):
        processing_transitions.append(args)
        return True

    def track_document(*args, **kwargs):
        document_transitions.append(args)
        return True

    def track_history(*args, **kwargs):
        history_calls.append(kwargs)

    monkeypatch.setattr(tasks, "transition_processing_status", track_processing)
    monkeypatch.setattr(tasks, "transition_document_status", track_document)
    monkeypatch.setattr(tasks, "_history", track_history)

    tasks._fail_invoice_processing("inv-1", "OCR failed")

    assert len(processing_transitions) == 1
    assert len(document_transitions) == 1
    assert len(history_calls) == 1
    assert history_calls[0]["error_message"] == "OCR failed"


def test_fail_invoice_processing_only_logs_if_transition_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    document_transitions = []
    history_calls = []

    def track_processing(*args, **kwargs):
        return False  # Transition failed

    def track_document(*args, **kwargs):
        document_transitions.append(args)
        return True

    def track_history(*args, **kwargs):
        history_calls.append(kwargs)

    monkeypatch.setattr(tasks, "transition_processing_status", track_processing)
    monkeypatch.setattr(tasks, "transition_document_status", track_document)
    monkeypatch.setattr(tasks, "_history", track_history)

    tasks._fail_invoice_processing("inv-1", "error")

    assert len(document_transitions) == 0  # Should not transition document if processing transition failed
    assert len(history_calls) == 1  # Still logs history


def test_process_ocr_multi_page_invoice_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_ai = StubDelayTask()
    monkeypatch.setattr(tasks, "process_invoice_ai_extraction", stub_ai)
    monkeypatch.setattr(tasks, "process_ai_pipeline", StubDelayTask())
    monkeypatch.setattr(tasks, "_get_file_type", lambda fid: "invoice_page")
    monkeypatch.setattr(tasks, "_get_invoice_parent_id", lambda fid, ft: "inv-1")
    monkeypatch.setattr(tasks, "_update_file_fields", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_update_file_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_invoice_page_progress", lambda invoice_id: (2, 5))
    monkeypatch.setattr(tasks, "_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "transition_processing_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "transition_document_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "run_ocr", lambda fid, base: {"text": "page text"})

    result = tasks.process_ocr("page-2")

    assert result["invoice_id"] == "inv-1"
    assert result["pages_completed"] == 2
    assert result["pages_total"] == 5
    assert stub_ai.calls == []  # Should not enqueue AI extraction yet


def test_process_ocr_invoice_page_with_ocr_extras(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_ai = StubDelayTask()
    monkeypatch.setattr(tasks, "process_invoice_ai_extraction", stub_ai)
    monkeypatch.setattr(tasks, "process_ai_pipeline", StubDelayTask())
    monkeypatch.setattr(tasks, "_get_file_type", lambda fid: "invoice_page")
    monkeypatch.setattr(tasks, "_get_invoice_parent_id", lambda fid, ft: "inv-1")
    monkeypatch.setattr(tasks, "_update_file_fields", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_update_file_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "_invoice_page_progress", lambda invoice_id: (1, 1))
    monkeypatch.setattr(tasks, "_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(tasks, "transition_processing_status", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasks, "transition_document_status", lambda *args, **kwargs: True)

    def ocr_with_extras(fid, base):
        return {
            "text": "invoice text",
            "merchant_name": "Acme Corp",
            "gross_amount": 123.45,
            "purchase_datetime": "2025-10-01",
        }

    monkeypatch.setattr(tasks, "run_ocr", ocr_with_extras)

    result = tasks.process_ocr("page-1")

    assert result["invoice_id"] == "inv-1"
    assert result["ok"] is True
    assert stub_ai.calls == ["inv-1"]
