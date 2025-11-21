from __future__ import annotations

import json
import logging
import os
import requests
from typing import Any, Dict, Optional

from config import config
from services.ai.providers.base import BaseLLMProvider, ProviderResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """Adapter for OpenAI's Chat Completions API."""

    def __init__(self, model_name: Optional[str], api_key: Optional[str] = None):
        super().__init__(model_name)
        self.api_key = api_key or config.OPENAI_API_KEY

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        if not self.model_name:
            raise RuntimeError("OpenAI model name is not configured")

        url = "https://api.openai.com/v1/chat/completions"

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

        request_payload = {
            "model": self.model_name,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            timeout_seconds = config.OPENAI_TIMEOUT
            response = requests.post(url, json=request_payload, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

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
                logger.debug(f"Response is text, not JSON: {content[:100]}")
                return ProviderResponse(raw=content, parsed=None)

        except requests.exceptions.RequestException as exc:
            error_detail = str(exc)
            try:
                if hasattr(exc, 'response') and exc.response is not None:
                    error_body = exc.response.json()
                    error_detail = f"{exc} - Response: {error_body}"
            except:
                pass
            logger.error(f"OpenAI API error: {error_detail}")
            raise RuntimeError(f"OpenAI API call failed: {exc}")


class ResponsesApiOpenAIProvider(OpenAIProvider):
    """Adapter for OpenAI's new /v1/responses API."""

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        if not self.model_name:
            raise RuntimeError("OpenAI model name is not configured")

        url = "https://api.openai.com/v1/responses"

        input_messages = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": json.dumps(payload, ensure_ascii=False),
                    }
                ],
            },
        ]

        request_payload = {
            "model": self.model_name,
            "input": input_messages,
            "text": {
                "format": { "type": "json_object" }
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            timeout_seconds = config.OPENAI_TIMEOUT
            response = requests.post(url, json=request_payload, headers=headers, timeout=timeout_seconds)
            response.raise_for_status()

            result = response.json()
            content = ""

            # Prefer Responses API `output` field
            output_blocks = result.get("output") or []
            if output_blocks:
                first_block = output_blocks[0] or {}
                if first_block.get("type") == "message":
                    parts = first_block.get("content") or []
                    text_parts = [
                        part.get("text", "")
                        for part in parts
                        if isinstance(part, dict) and part.get("type") in ("output_text", "text")
                    ]
                    content = "\n".join(part for part in text_parts if part)

            if not content:
                ot = result.get("output_text")
                if isinstance(ot, str):
                    content = ot
                elif isinstance(ot, list):
                    content = "\n".join(part for part in ot if part)

            if not content:
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")

            if not content:
                return ProviderResponse(raw="", parsed=None)

            try:
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
                logger.debug(f"Response is text, not JSON: {content[:100]}")
                return ProviderResponse(raw=content, parsed=None)

        except requests.exceptions.RequestException as exc:
            error_detail = str(exc)
            try:
                if hasattr(exc, 'response') and exc.response is not None:
                    error_body = exc.response.json()
                    error_detail = f"{exc} - Response: {error_body}"
            except:
                pass
            logger.error(f"OpenAI API error: {error_detail}")
            raise RuntimeError(f"OpenAI API call failed: {exc}")


class AzureOpenAIProvider(BaseLLMProvider):
    """Adapter for Azure-hosted OpenAI deployments."""

    def __init__(self, model_name: Optional[str], api_key: Optional[str] = None, endpoint: Optional[str] = None):
        super().__init__(model_name)
        self.api_key = api_key or config.AZURE_OPENAI_API_KEY
        self.endpoint = endpoint or config.AZURE_OPENAI_ENDPOINT

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        if not self.api_key or not self.endpoint:
            raise RuntimeError("Azure OpenAI credentials are not configured")
        logger.warning("AzureOpenAIProvider invoked without concrete implementation")
        return ProviderResponse(raw="", parsed=None)
