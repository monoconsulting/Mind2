from backend.src.services.ai_logging import log_ai_call


class DummyCursor:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))


def test_log_ai_call_uses_provided_cursor():
    cursor = DummyCursor()

    result = log_ai_call(
        file_id="file-1",
        job="AI1",
        status="success",
        ai_stage_name="document_analysis",
        provider="openai",
        model_name="gpt-test",
        cursor=cursor,
    )

    assert result is True
    assert cursor.calls
    sql, params = cursor.calls[0]
    assert "ai_processing_history" in sql
    assert params[0] == "file-1"
    assert params[1] == "AI1"
    assert params[2] == "success"
    assert params[9] == "gpt-test"
