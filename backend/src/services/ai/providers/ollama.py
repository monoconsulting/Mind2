from __future__ import annotations

import json
import logging
import os
import requests
from typing import Any, Dict, Optional

from config import config
from services.ai.providers.base import BaseLLMProvider, ProviderResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Adapter for Ollama's native API (gpt-oss:20b)."""

    def __init__(self, model_name: Optional[str], endpoint: Optional[str] = None):
        super().__init__(model_name)
        self.endpoint = endpoint or config.OLLAMA_HOST

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        if not self.model_name:
            raise RuntimeError("Ollama model name is not configured")

        # Ollama uses /api/generate endpoint
        url = f"{self.endpoint}/api/generate"

        # Combine system prompt and payload into a single prompt
        full_prompt = f"{prompt}\n\nData to analyze:\n{json.dumps(payload, ensure_ascii=False)}\n\nProvide your response in JSON format:"

        request_payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False,
        }

        try:
            response = requests.post(url, json=request_payload, timeout=120)
            response.raise_for_status()

            result = response.json()
            content = result.get("response", "")

            if not content:
                return ProviderResponse(raw="", parsed=None)

            # Try to parse as JSON
            try:
                # Clean up markdown code blocks if present
                cleaned = content.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

                parsed = json.loads(cleaned)
                return ProviderResponse(raw=content, parsed=parsed)
            except json.JSONDecodeError as exc:
                # Log detailed error for debugging
                logger.error(f"Ollama JSON parse failed: {str(exc)[:100]}... Content length: {len(content)}, First 200 chars: {content[:200]}...")
                return ProviderResponse(raw=content, parsed=None)

        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Ollama API call failed: {exc}")
