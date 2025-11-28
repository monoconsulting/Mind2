from types import SimpleNamespace

from services.ai.providers.base import ProviderResponse
from services.ai.providers.openai import OpenAIProvider


def test_openai_provider_parses_json(monkeypatch):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["url"] = url

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {"message": {"content": '{"key": "value"}'}}
                    ]
                }

        return FakeResponse()

    monkeypatch.setattr("services.ai.providers.openai.requests.post", fake_post)
    monkeypatch.setattr(
        "services.ai.providers.openai.config",
        SimpleNamespace(OPENAI_API_KEY="key", OPENAI_TIMEOUT=1),
    )

    provider = OpenAIProvider(model_name="gpt-test", api_key="key")
    result = provider.generate("system prompt", {"foo": "bar"})

    assert isinstance(result, ProviderResponse)
    assert result.parsed == {"key": "value"}
    assert captured["url"].endswith("/v1/chat/completions")
