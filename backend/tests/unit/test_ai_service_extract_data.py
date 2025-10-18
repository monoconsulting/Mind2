from decimal import Decimal

import pytest

from backend.src.models.ai_processing import DataExtractionRequest
from backend.src.services.ai_service import AIService


@pytest.fixture(autouse=True)
def _stub_prompts(monkeypatch):
    """Avoid DB lookups when instantiating the AI service in tests."""

    def _noop(self):
        self.prompts = {"data_extraction": "prompt"}
        self.prompt_providers = {"data_extraction": None}
        self.prompt_provider_names = {"data_extraction": "none"}
        self.prompt_model_names = {"data_extraction": "none"}

    monkeypatch.setattr(AIService, "_load_prompts_and_providers", _noop)


def test_extract_data_includes_credit_card_fields(monkeypatch):
    """AIService.extract_data should map all credit card fields from LLM output."""

    def _fake_generate(self, prompt_key, payload):
        assert prompt_key == "data_extraction"
        return {
            "unified_file": {
                "orgnr": "556677-8899",
                "payment_type": "card",
                "gross_amount_original": "250.00",
                "net_amount_original": "200.00",
                "currency": "SEK",
                "credit_card_number": "**** **** **** 4242",
                "credit_card_last_4_digits": 4242,
                "credit_card_brand_full": "VISA",
                "credit_card_brand_short": "visa",
                "credit_card_payment_variant": "visa_applepay",
                "credit_card_type": "POS",
                "credit_card_token": "tok_abc123",
                "credit_card_entering_mode": "Contactless",
            },
            "company": {"name": "Test AB", "orgnr": "556677-8899"},
            "receipt_items": [],
            "confidence": 0.9,
        }

    monkeypatch.setattr(AIService, "_provider_generate", _fake_generate, raising=False)

    service = AIService()
    request = DataExtractionRequest(
        file_id="file-123",
        ocr_text="Some OCR text",
        document_type="receipt",
        expense_type="corporate",
    )

    response = service.extract_data(request)

    unified = response.unified_file
    assert unified.payment_type == "card"
    assert unified.credit_card_number == "**** **** **** 4242"
    assert unified.credit_card_last_4_digits == 4242
    assert unified.credit_card_brand_full == "VISA"
    assert unified.credit_card_brand_short == "visa"
    assert unified.credit_card_payment_variant == "visa_applepay"
    assert unified.credit_card_type == "POS"
    assert unified.credit_card_token == "tok_abc123"
    assert unified.credit_card_entering_mode == "Contactless"
    # Numeric values should be parsed into Decimals
    assert isinstance(unified.gross_amount_original, Decimal)
    assert isinstance(unified.net_amount_original, Decimal)


def test_extract_data_accepts_last4_alias(monkeypatch):
    """If the LLM returns credit_card_last_4 we still capture the digits."""

    def _fake_generate(self, prompt_key, payload):
        return {
            "unified_file": {
                "payment_type": "card",
                "credit_card_number": "**** **** **** 0000",
                "credit_card_last_4": "0000",
            },
            "company": {"name": "Test", "orgnr": "1"},
            "receipt_items": [],
            "confidence": 0.5,
        }

    monkeypatch.setattr(AIService, "_provider_generate", _fake_generate, raising=False)

    service = AIService()
    request = DataExtractionRequest(
        file_id="file-456",
        ocr_text="",
        document_type="receipt",
        expense_type="corporate",
    )

    response = service.extract_data(request)
    assert response.unified_file.credit_card_last_4_digits == 0
