import importlib.util
from pathlib import Path


def test_history_wrapper_forwards_to_log_ai_call(monkeypatch):
    """Load tasks.history directly to avoid package import side effects."""
    history_path = Path("backend/src/services/tasks/history.py")
    spec = importlib.util.spec_from_file_location("tasks_history_module", history_path)
    history = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(history)  # type: ignore

    captured = {}

    def fake_log_ai_call(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(history, "log_ai_call", fake_log_ai_call)

    history._history(
        file_id="file-xyz",
        job="AI1",
        status="success",
        ai_stage_name="document_analysis",
        provider="openai",
        model_name="gpt-test",
    )

    assert captured["file_id"] == "file-xyz"
    assert captured["job"] == "AI1"
    assert captured["status"] == "success"
