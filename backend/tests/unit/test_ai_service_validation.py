import pytest

from backend.src.models.ai_processing import DataExtractionRequest
from backend.src.services.ai_service import AIService


@pytest.fixture(autouse=True)
def _stub_prompts(monkeypatch):
    """Prevent DB access during AIService init."""

    def _noop(self):
        self.prompts = {"data_extraction": "prompt"}
        self.prompt_providers = {"data_extraction": None}
        self.prompt_provider_names = {"data_extraction": "none"}
        self.prompt_model_names = {"data_extraction": "none"}

    monkeypatch.setattr(AIService, "_load_prompts_and_providers", _noop)


def test_ai3_invalid_receipt_item_fails_fast(monkeypatch):
    """Receipt items without names must raise instead of being silently skipped."""

    def _fake_generate(self, prompt_key, payload, file_id=None):
        assert file_id == "file-invalid"
        return {
            "unified_file": {
                "currency": "SEK",
            },
            "company": {"name": "Bad Co", "orgnr": "1"},
            "receipt_items": [
                {"main_id": "file-invalid", "name": "", "number": 1},
            ],
            "confidence": 0.4,
        }

    monkeypatch.setattr(AIService, "_provider_generate", _fake_generate, raising=False)

    service = AIService()
    request = DataExtractionRequest(
        file_id="file-invalid",
        ocr_text="text",
        document_type="receipt",
        expense_type="corporate",
    )

    with pytest.raises(ValueError):
        service.run_ai3_data_extraction(request)
