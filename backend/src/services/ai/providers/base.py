from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ProviderResponse:
    """Structured response from an LLM provider."""

    raw: str
    parsed: Optional[Dict[str, Any]]


class BaseLLMProvider:
    """Minimal interface used by the AI service for LLM integrations."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name

    @property
    def provider_name(self) -> str:
        return self.__class__.__name__.replace("Provider", "").lower()

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError
