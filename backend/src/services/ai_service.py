"""AI Service for processing receipts and documents."""
from __future__ import annotations

import json
import logging
import os
import re
import requests
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Tuple

from models.ai_processing import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    ExpenseClassificationRequest,
    ExpenseClassificationResponse,
    DataExtractionRequest,
    DataExtractionResponse,
    AccountingClassificationRequest,
    AccountingClassificationResponse,
    CreditCardMatchRequest,
    CreditCardMatchResponse,
    UnifiedFileBase,
    ReceiptItem,
    Company,
    AccountingProposal,
)
from services.db.connection import db_cursor


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


class OpenAIProvider(BaseLLMProvider):
    """Adapter for OpenAI's Chat Completions API."""

    def __init__(self, model_name: Optional[str], api_key: Optional[str] = None):
        super().__init__(model_name)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        if not self.model_name:
            raise RuntimeError("OpenAI model name is not configured")

        url = "https://api.openai.com/v1/chat/completions"

        # Build the request payload
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
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
            response = requests.post(url, json=request_payload, headers=headers, timeout=180)
            response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

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
                # If not JSON, treat as raw text response (for simple prompts like AI1/AI2)
                # Don't log as error - some prompts expect text responses
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
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        if not self.api_key or not self.endpoint:
            raise RuntimeError("Azure OpenAI credentials are not configured")
        logger.warning("AzureOpenAIProvider invoked without concrete implementation")
        return ProviderResponse(raw="", parsed=None)


class OllamaProvider(BaseLLMProvider):
    """Adapter for Ollama's native API (gpt-oss:20b)."""

    def __init__(self, model_name: Optional[str], endpoint: Optional[str] = None):
        super().__init__(model_name)
        self.endpoint = endpoint or os.getenv("OLLAMA_HOST", "http://localhost:11435")

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


logger = logging.getLogger(__name__)

ACCOUNT_CODE_KEYS = ("account_code", "account", "accountCode", "account_number")
DEBIT_KEYS = ("debit", "debit_amount")
CREDIT_KEYS = ("credit", "credit_amount")
VAT_KEYS = ("vat_rate", "vat", "vat_rate_percent", "vatPercent")
NOTES_KEYS = ("notes", "note", "memo", "description")
ITEM_ID_KEYS = ("item_id", "line_id", "line_item_id", "entry_id")
TWO_DECIMAL_PLACES = Decimal("0.01")
ZERO_DECIMAL = Decimal("0.00")


class AccountingProposalValidationError(ValueError):
    """Raised when AI4 accounting proposals fail validation."""


def _quantize_two_decimals(value: Decimal) -> Decimal:
    return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def _deep_clean_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively clean dictionary, converting empty strings to None."""
    for key, value in d.items():
        if isinstance(value, dict):
            _deep_clean_dict(value)
        elif isinstance(value, str) and not value.strip():
            d[key] = None
    return d


def _ensure_decimal(
    raw_value: Any,
    field: str,
    *,
    allow_zero: bool = True,
    allow_negative: bool = False,
) -> Decimal:
    """Normalize various numeric representations to Decimal with two decimals."""

    if raw_value is None:
        raise AccountingProposalValidationError(f"{field} is missing")

    if isinstance(raw_value, Decimal):
        value = raw_value
    elif isinstance(raw_value, (int, float)):
        value = Decimal(str(raw_value))
    elif isinstance(raw_value, str):
        cleaned = raw_value.strip()
        if not cleaned:
            raise AccountingProposalValidationError(f"{field} is empty")
        cleaned = cleaned.replace(" ", "")
        cleaned = cleaned.replace(",", ".")
        cleaned = cleaned.replace("%", "")
        cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
        if cleaned.count(".") > 1:
            parts = cleaned.split(".")
            cleaned = "".join(parts[:-1]) + "." + parts[-1]
        try:
            value = Decimal(cleaned)
        except InvalidOperation as exc:  # pragma: no cover - defensive branch
            raise AccountingProposalValidationError(
                f"{field} has invalid numeric value: {raw_value!r}"
            ) from exc
    else:
        raise AccountingProposalValidationError(
            f"{field} has unsupported type: {type(raw_value).__name__}"
        )

    if not allow_negative and value < 0:
        raise AccountingProposalValidationError(f"{field} must be non-negative")
    if not allow_zero and value == 0:
        raise AccountingProposalValidationError(f"{field} must be greater than zero")

    return _quantize_two_decimals(value)


def _first_present(data: Dict[str, Any], keys: Iterable[str], field: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    raise AccountingProposalValidationError(f"{field} is missing")


def _extract_account_code(entry: Dict[str, Any]) -> str:
    for key in ACCOUNT_CODE_KEYS:
        value = entry.get(key)
        if value is None:
            continue
        code = str(value).strip()
        if not code:
            continue
        if len(code) > 32:
            raise AccountingProposalValidationError("account_code exceeds 32 characters")
        return code
    raise AccountingProposalValidationError("account_code is missing")


def _coerce_item_id(raw_value: Any, context: str) -> int:
    if raw_value is None:
        raise AccountingProposalValidationError(f"{context} is missing")
    try:
        item_id = int(str(raw_value))
    except (TypeError, ValueError) as exc:
        raise AccountingProposalValidationError(f"{context} must be an integer") from exc
    if item_id <= 0:
        raise AccountingProposalValidationError(f"{context} must be a positive integer")
    return item_id


def _extract_vat_rate(entry: Dict[str, Any]) -> Optional[Decimal]:
    for key in VAT_KEYS:
        if key in entry and entry[key] not in (None, ""):
            rate = _ensure_decimal(entry[key], "vat_rate")
            if rate < 0 or rate > 100:
                raise AccountingProposalValidationError("vat_rate must be between 0 and 100")
            return rate
    return None


def _extract_notes(entry: Dict[str, Any]) -> Optional[str]:
    for key in NOTES_KEYS:
        if key in entry and entry[key] is not None:
            text = str(entry[key]).strip()
            if not text:
                return None
            if len(text) > 255:
                logger.warning("AI4 note truncated to 255 characters: %s...", text[:32])
                return text[:255]
            return text
    return None


def _build_accounting_proposal(
    entry: Dict[str, Any],
    expected_receipt_id: str,
    *,
    context: str,
) -> AccountingProposal:
    receipt_id = str(entry.get("receipt_id") or "").strip()
    if not receipt_id:
        receipt_id = expected_receipt_id
    if receipt_id != expected_receipt_id:
        raise AccountingProposalValidationError(
            f"receipt_id mismatch (expected {expected_receipt_id}, got {receipt_id})"
        )

    raw_item_id = entry.get("item_id")
    if raw_item_id is None:
        raise AccountingProposalValidationError(f"{context}.item_id is missing")
    item_id = _coerce_item_id(raw_item_id, f"{context}.item_id")

    account_code = _extract_account_code(entry)
    debit_raw = _first_present(entry, DEBIT_KEYS, "debit")
    credit_raw = _first_present(entry, CREDIT_KEYS, "credit")
    debit = _ensure_decimal(debit_raw, "debit")
    credit = _ensure_decimal(credit_raw, "credit")

    if debit > 0 and credit > 0:
        raise AccountingProposalValidationError("debit and credit cannot both be greater than zero")
    if debit == 0 and credit == 0:
        raise AccountingProposalValidationError("debit and credit cannot both be zero")

    vat_rate = _extract_vat_rate(entry)
    notes = _extract_notes(entry)

    return AccountingProposal(
        receipt_id=expected_receipt_id,
        item_id=item_id,
        account_code=account_code,
        debit=_quantize_two_decimals(debit if debit > 0 else ZERO_DECIMAL),
        credit=_quantize_two_decimals(credit if credit > 0 else ZERO_DECIMAL),
        vat_rate=_quantize_two_decimals(vat_rate) if vat_rate is not None else None,
        notes=notes,
    )


def parse_accounting_proposals(payload: Dict[str, Any], fallback_receipt_id: str) -> List[AccountingProposal]:
    """Parse and validate AI4 payload into accounting proposals."""

    if not isinstance(payload, dict):
        raise AccountingProposalValidationError("LLM response must be a JSON object")

    receipt_id = str(payload.get("receipt_id") or fallback_receipt_id or "").strip()
    if not receipt_id:
        raise AccountingProposalValidationError("receipt_id is missing from payload")

    raw_entries: List[Tuple[Dict[str, Any], str]] = []

    if payload.get("items") is not None:
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise AccountingProposalValidationError("items must be a non-empty array")
        for item_index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                raise AccountingProposalValidationError(
                    f"items[{item_index}] must be an object"
                )
            raw_item_id = None
            for key in ITEM_ID_KEYS:
                if key in item and item[key] not in (None, ""):
                    raw_item_id = item[key]
                    break
            if raw_item_id is None:
                raise AccountingProposalValidationError(
                    f"items[{item_index}] is missing item_id"
                )
            entries = item.get("entries")
            if not isinstance(entries, list) or not entries:
                raise AccountingProposalValidationError(
                    f"items[{item_index}].entries must be a non-empty array"
                )
            for entry_index, entry in enumerate(entries, start=1):
                if not isinstance(entry, dict):
                    raise AccountingProposalValidationError(
                        f"items[{item_index}].entries[{entry_index}] must be an object"
                    )
                normalized = dict(entry)
                normalized.setdefault("item_id", raw_item_id)
                normalized.setdefault("receipt_id", receipt_id)
                raw_entries.append((normalized, f"items[{item_index}].entries[{entry_index}]"))
    elif payload.get("proposals") is not None:
        proposals = payload.get("proposals")
        if not isinstance(proposals, list) or not proposals:
            raise AccountingProposalValidationError("proposals must be a non-empty array")
        for idx, entry in enumerate(proposals, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"proposals[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"proposals[{idx}]"))
    elif payload.get("entries") is not None:
        # Accept 'entries' as an alias for 'proposals' (common LLM output format)
        entries = payload.get("entries")
        if not isinstance(entries, list) or not entries:
            raise AccountingProposalValidationError("entries must be a non-empty array")
        for idx, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"entries[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"entries[{idx}]"))
    elif payload.get("accounting_entries") is not None:
        # Accept 'accounting_entries' as an alias for 'proposals' (common LLM output format)
        accounting_entries = payload.get("accounting_entries")
        if not isinstance(accounting_entries, list) or not accounting_entries:
            raise AccountingProposalValidationError("accounting_entries must be a non-empty array")
        for idx, entry in enumerate(accounting_entries, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"accounting_entries[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"accounting_entries[{idx}]"))
    else:
        raise AccountingProposalValidationError(
            "Payload must include either 'items', 'proposals', 'entries', or 'accounting_entries'"
        )

    parsed: List[AccountingProposal] = []
    for entry, context in raw_entries:
        parsed.append(_build_accounting_proposal(entry, receipt_id, context=context))

    if not parsed:
        raise AccountingProposalValidationError("No accounting proposals generated from payload")

    return parsed

ORGNR_PATTERN = re.compile(r"\b\d{6}[- ]?\d{4}\b")
ISO_CURRENCY_PATTERN = re.compile(r"\b(USD|EUR|SEK|NOK|DKK|GBP)\b", re.IGNORECASE)
RECEIPT_NO_PATTERN = re.compile(r"(?:receipt|kvitto|nr|#)[:\s]*([A-Z0-9-]{3,})", re.IGNORECASE)
DATE_PATTERNS = [
    re.compile(r"(20\d{2}[-/](?:0\d|1[0-2])[-/](?:0\d|[12]\d|3[01]))[ T]*(\d{2}:\d{2})?"),
    re.compile(r"((?:0\d|[12]\d|3[01])[./](?:0\d|1[0-2])[./]20\d{2})"),
]


def _normalize_amount(token: str) -> Optional[Decimal]:
    cleaned = token.strip().replace(" ", "")
    cleaned = cleaned.replace(" ", "").replace("'", "")
    cleaned = cleaned.replace(",", ".")
    if cleaned.count(".") > 1:
        # assume thousands separators
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _find_amounts(line: str) -> List[Decimal]:
    amounts: List[Decimal] = []
    for candidate in re.findall(r"\d+[\s.,]\d{2}", line):
        value = _normalize_amount(candidate)
        if value is not None:
            amounts.append(value)
    return amounts


# NOTE: Rule-based extraction functions removed - AI3 uses ONLY LLM for data extraction
# No OCR-based parsing of business data allowed per MIND_WORKFLOW.md


class AIService:
    """Service for deterministic extraction and classification.

    The service consumes OCR text and uses rule-based parsing so that results
    are derived from the provided document data instead of hard-coded values.
    This respects the repository rule that mock data must not be injected.
    """

    def __init__(self) -> None:
        self.prompts: Dict[str, str] = {}
        self.prompt_providers: Dict[str, Optional[BaseLLMProvider]] = {}
        self.prompt_provider_names: Dict[str, str] = {}
        self.prompt_model_names: Dict[str, str] = {}
        self._load_prompts_and_providers()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _load_prompts_and_providers(self) -> None:
        """Load prompts and their selected models from database."""
        try:
            with db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT sp.prompt_key, COALESCE(sp.prompt_content, ''),
                           sp.selected_model_id, l.provider_name, m.model_name, l.api_key, l.endpoint_url
                    FROM ai_system_prompts sp
                    LEFT JOIN ai_llm_model m ON sp.selected_model_id = m.id
                    LEFT JOIN ai_llm l ON m.llm_id = l.id
                    """
                )
                for key, content, model_id, provider_name, model_name, api_key, endpoint_url in cursor.fetchall():
                    self.prompts[key] = content or ""

                    # Initialize provider for this prompt if model is selected
                    if model_id and provider_name and model_name:
                        try:
                            provider_adapter = self._init_provider(provider_name, model_name, api_key, endpoint_url)
                            self.prompt_providers[key] = provider_adapter
                            self.prompt_provider_names[key] = provider_name
                            self.prompt_model_names[key] = model_name
                            logger.info(f"Loaded model for {key}: {provider_name}/{model_name}")
                        except Exception as exc:
                            logger.warning(f"Failed to init provider for {key}: {exc}")
                            self.prompt_providers[key] = None
                            self.prompt_provider_names[key] = "error"
                            self.prompt_model_names[key] = "error"
                    else:
                        self.prompt_providers[key] = None
                        self.prompt_provider_names[key] = "none"
                        self.prompt_model_names[key] = "none"
                        logger.warning(f"No model selected for {key}")

        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load AI system prompts: %s", exc)

    def _load_prompts(self) -> Dict[str, str]:
        """Legacy method for backward compatibility."""
        prompts: Dict[str, str] = {}
        try:
            with db_cursor() as cursor:
                cursor.execute(
                    "SELECT prompt_key, COALESCE(prompt_content, '') FROM ai_system_prompts"
                )
                for key, content in cursor.fetchall():
                    prompts[key] = content or ""
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load AI system prompts: %s", exc)
        return prompts


    def _init_provider(
        self, provider_from_db: Optional[str], model_from_db: Optional[str],
        api_key_from_db: Optional[str] = None, endpoint_from_db: Optional[str] = None
    ) -> Optional[BaseLLMProvider]:
        configured = os.getenv("AI_PROVIDER") or (provider_from_db or "")
        configured = configured.lower().strip()
        model = os.getenv("AI_MODEL_NAME") or model_from_db

        if not configured:
            return None

        try:
            if configured == "openai":
                return OpenAIProvider(model, api_key_from_db)
            if configured in {"azure", "azure_openai", "azure-openai"}:
                return AzureOpenAIProvider(model, api_key_from_db, endpoint_from_db)
            if configured == "ollama":
                return OllamaProvider(model, endpoint_from_db)
        except Exception as exc:  # pragma: no cover - configuration errors
            logger.warning("Failed to initialise LLM provider %s: %s", configured, exc)
            return None

        logger.warning("Unknown AI provider '%s'; falling back to rule-based mode", configured)
        return None

    def _provider_generate(
        self, stage_key: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        # ONLY use the prompt-specific provider - NO fallback
        provider = self.prompt_providers.get(stage_key)
        provider_name = self.prompt_provider_names.get(stage_key, "unknown")
        model_name = self.prompt_model_names.get(stage_key, "unknown")

        if not provider:
            logger.error(
                f"No provider configured for {stage_key}. "
                f"Provider: {provider_name}, Model: {model_name}. "
                f"Please select a model for this prompt in the database."
            )
            return None

        prompt = self.prompts.get(stage_key, "")
        try:
            logger.debug(f"Calling {stage_key} with provider={provider_name}, model={model_name}")
            response = provider.generate(prompt=prompt, payload=payload)

            # Log raw response for AI4 debugging
            if stage_key == "accounting_classification":
                logger.info(
                    "AI4 raw LLM response - provider=%s, model=%s, parsed: %s, raw: %s",
                    provider_name,
                    model_name,
                    json.dumps(response.parsed, ensure_ascii=False)[:300] if response.parsed else "None",
                    response.raw[:300] if response.raw else "None"
                )

            if not response.raw and response.parsed is None:
                logger.warning(f"Provider {provider_name}/{model_name} returned empty response for {stage_key}")
                return None
            if response.parsed is not None:
                return response.parsed

            # Handle raw text responses (wrap simple text in JSON for AI1/AI2)
            try:
                return json.loads(response.raw)
            except json.JSONDecodeError:
                raw_text = response.raw.strip()
                if stage_key == "document_analysis":
                    return {"document_type": raw_text, "confidence": 0.8}
                elif stage_key == "expense_classification":
                    return {"expense_type": raw_text, "confidence": 0.8}
                else:
                    logger.warning(f"Provider {provider_name}/{model_name} returned raw text for {stage_key}, expected JSON: {raw_text[:100]}")
                    return None
        except Exception as exc:  # pragma: no cover - network/parse errors
            logger.error("Provider call for %s failed (provider=%s, model=%s): %s", stage_key, provider_name, model_name, exc, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # AI1 - Document classification
    # ------------------------------------------------------------------
    def classify_document(self, request: DocumentClassificationRequest) -> DocumentClassificationResponse:
        text = (request.ocr_text or "").lower()
        logger.info("Classifying document %s", request.file_id)

        doc_type = "Manual Review"
        confidence = 0.0
        reasoning_parts: List[str] = []

        receipt_tokens = ["kvitto", "receipt", "summa", "moms", "butik", "kundens kvitto"]
        invoice_tokens = ["invoice", "faktura", "förfallodatum", "ocr", "betalning"]

        receipt_hits = sum(token in text for token in receipt_tokens)
        invoice_hits = sum(token in text for token in invoice_tokens)

        llm_result = self._provider_generate(
            "document_analysis", {"ocr_text": request.ocr_text or ""}
        )
        if llm_result:
            doc_type = llm_result.get("document_type", doc_type)
            confidence = float(llm_result.get("confidence", confidence))
            reasoning_parts.append("LLM-assisted classification")

        if receipt_hits and receipt_hits >= invoice_hits:
            doc_type = "receipt"
            confidence = min(0.95, 0.4 + 0.1 * receipt_hits)
            reasoning_parts.append("Receipt keywords detected")
        elif invoice_hits:
            doc_type = "invoice"
            confidence = min(0.9, 0.35 + 0.1 * invoice_hits)
            reasoning_parts.append("Invoice keywords detected")
        elif text:
            doc_type = "other"
            confidence = 0.5
            reasoning_parts.append("Generic document with limited keywords")

        prompt_hint = self.prompts.get("document_analysis")
        if prompt_hint:
            reasoning_parts.append(f"Prompt hint provided: {prompt_hint}")

        return DocumentClassificationResponse(
            file_id=request.file_id,
            document_type=doc_type,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts) or None,
        )

    # ------------------------------------------------------------------
    # AI2 - Expense classification
    # ------------------------------------------------------------------
    def classify_expense(self, request: ExpenseClassificationRequest) -> ExpenseClassificationResponse:
        text = (request.ocr_text or "").lower()
        logger.info("Classifying expense for %s", request.file_id)

        card_patterns = ["visa", "mastercard", "first card", "corporate", "företagskort", "card number"]
        cash_patterns = ["kontant", "cash"]

        expense_type = "personal"
        confidence = 0.6
        reasoning_parts: List[str] = []
        card_identifier: Optional[str] = None

        for pattern in card_patterns:
            if pattern in text:
                expense_type = "corporate"
                confidence = 0.85
                card_identifier = pattern
                reasoning_parts.append(f"Detected card keyword '{pattern}'")
                break

        llm_result = self._provider_generate(
            "expense_classification",
            {"ocr_text": request.ocr_text or "", "document_type": request.document_type},
        )
        if llm_result:
            expense_type = llm_result.get("expense_type", expense_type)
            confidence = float(llm_result.get("confidence", confidence))
            if llm_result.get("card_identifier"):
                card_identifier = llm_result["card_identifier"]
            reasoning_parts.append("LLM-assisted expense classification")

        if expense_type == "personal":
            if any(pattern in text for pattern in cash_patterns):
                confidence = 0.7
                reasoning_parts.append("Cash keyword detected")
            else:
                confidence = 0.65
                reasoning_parts.append("Defaulting to personal expense")

        prompt_hint = self.prompts.get("expense_classification")
        if prompt_hint:
            reasoning_parts.append(f"Prompt hint provided: {prompt_hint}")

        return ExpenseClassificationResponse(
            file_id=request.file_id,
            expense_type=expense_type,
            confidence=confidence,
            card_identifier=card_identifier,
            reasoning="; ".join(reasoning_parts) or None,
        )

    # ------------------------------------------------------------------
    # AI3 - Data extraction
    # ------------------------------------------------------------------
    def extract_data(self, request: DataExtractionRequest) -> DataExtractionResponse:
        """
        AI3 - Extract ALL business data from OCR text using LLM.
        NO rule-based extraction allowed - only LLM extracts business data!
        """
        ocr_text = request.ocr_text or ""
        logger.info("Extracting structured data via LLM for %s", request.file_id)

        # ONLY LLM extracts data - call LLM provider
        llm_result = self._provider_generate(
            "data_extraction",
            {
                "ocr_text": ocr_text,
                "document_type": request.document_type,
                "expense_type": request.expense_type,
            },
        )

        if not llm_result:
            error_details = (
                f"file_id={request.file_id}, "
                f"provider={self.provider_name}, "
                f"model={self.model_name}, "
                f"prompt_length={len(self.prompts.get('data_extraction', ''))}, "
                f"ocr_length={len(ocr_text)}"
            )
            logger.error(f"AI3 data extraction failed: {error_details}")
            raise ValueError(f"LLM data extraction failed - {error_details}")

        # Deep clean the dictionary from LLM
        llm_result = _deep_clean_dict(llm_result)

        # Extract data from LLM response
        confidence = 0.5
        if "confidence" in llm_result:
            try:
                confidence = float(llm_result["confidence"])
            except (TypeError, ValueError):
                pass

        # Extract unified_file data from LLM
        unified_data = llm_result.get("unified_file", {})

        # Serialize other_data if it's a dict
        other_data_value = unified_data.get("other_data")
        if isinstance(other_data_value, dict):
            other_data_value = json.dumps(other_data_value, ensure_ascii=False)

        unified_file = UnifiedFileBase(
            file_type=request.document_type,
            orgnr=unified_data.get("orgnr"),
            payment_type=unified_data.get("payment_type"),
            purchase_datetime=unified_data.get("purchase_datetime"),
            expense_type=request.expense_type if request.expense_type in {"personal", "corporate"} else None,
            gross_amount_original=unified_data.get("gross_amount_original"),
            net_amount_original=unified_data.get("net_amount_original"),
            exchange_rate=unified_data.get("exchange_rate"),
            currency=unified_data.get("currency"),  # NO DEFAULT - LLM must provide
            gross_amount_sek=unified_data.get("gross_amount_sek"),
            net_amount_sek=unified_data.get("net_amount_sek"),
            receipt_number=unified_data.get("receipt_number"),
            other_data=other_data_value,
            ocr_raw=ocr_text,
        )

        # Extract company data from LLM
        company_data = llm_result.get("company", {})
        company = Company(
            name=company_data.get("name") or "",  # Required by schema but may be empty
            orgnr=company_data.get("orgnr") or "",  # Required by schema but may be empty
            address=company_data.get("address"),
            address2=company_data.get("address2"),
            zip=company_data.get("zip"),
            city=company_data.get("city"),
            country=company_data.get("country"),
            phone=company_data.get("phone"),
            www=company_data.get("www"),
        )

        # Extract receipt items from LLM
        receipt_items: List[ReceiptItem] = []
        llm_items_raw = llm_result.get("receipt_items")

        if llm_items_raw:
            logger.info(
                "AI3 LLM returned %d raw receipt_items for file_id=%s",
                len(llm_items_raw) if isinstance(llm_items_raw, list) else 0,
                request.file_id
            )
            try:
                for idx, item_dict in enumerate(llm_items_raw, 1):
                    try:
                        # Validate and fix main_id
                        item_main_id = item_dict.get("main_id")
                        if not item_main_id or item_main_id != request.file_id:
                            if item_main_id:
                                logger.warning(
                                    "AI3 receipt_items[%d] has main_id='%s' but file_id='%s' - correcting",
                                    idx, item_main_id, request.file_id
                                )
                            item_dict["main_id"] = request.file_id

                        # Convert None to empty string for article_id
                        if item_dict.get("article_id") is None:
                            item_dict["article_id"] = ""

                        # Validate name is not None - SKIP items without name (no mock data allowed!)
                        if not item_dict.get("name"):
                            logger.error(
                                "AI3 receipt_items[%d] has empty/null name - SKIPPING this item (no mock data allowed)",
                                idx
                            )
                            continue

                        # Ensure number has a default
                        if not item_dict.get("number"):
                            item_dict["number"] = 1

                        parsed_item = ReceiptItem(**item_dict)
                        receipt_items.append(parsed_item)
                        logger.debug(
                            "AI3 parsed receipt_items[%d]: name='%s', qty=%d, article_id='%s', total_inc_vat=%s",
                            idx, parsed_item.name, parsed_item.number,
                            parsed_item.article_id or 'N/A', parsed_item.item_total_price_inc_vat
                        )
                    except Exception as item_exc:
                        logger.error(
                            "AI3 failed to parse receipt_items[%d] for file_id=%s: %s. Raw data: %s",
                            idx, request.file_id, item_exc, item_dict
                        )
            except Exception as exc:
                logger.error(
                    "AI3 failed to parse LLM receipt_items for file_id=%s: %s. Full raw data: %s",
                    request.file_id, exc, llm_items_raw
                )
                # Continue with empty items rather than failing completely
        else:
            logger.warning(
                "AI3 LLM returned NO receipt_items for file_id=%s (this may be legitimate for some documents)",
                request.file_id
            )

        logger.info(
            "LLM extracted: company='%s', orgnr='%s', gross=%s, items=%d, confidence=%.2f",
            company.name,
            company.orgnr,
            unified_file.gross_amount_original,
            len(receipt_items),
            confidence,
        )

        return DataExtractionResponse(
            file_id=request.file_id,
            unified_file=unified_file,
            receipt_items=receipt_items,
            company=company,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # AI4 - Accounting classification
    # ------------------------------------------------------------------
    def classify_accounting(
        self,
        request: AccountingClassificationRequest,
        chart_of_accounts: List[Tuple[Any, ...]],
    ) -> AccountingClassificationResponse:
        logger.info("Classifying accounting for %s", request.file_id)

        proposals: List[AccountingProposal] = []
        confidence = 0.0

        # Serialize receipt_items for AI
        items_data = []
        for item in request.receipt_items:
            items_data.append({
                "id": item.id,
                "name": item.name,
                "article_id": item.article_id,
                "number": item.number,
                "item_price_ex_vat": str(item.item_price_ex_vat),
                "item_price_inc_vat": str(item.item_price_inc_vat),
                "item_total_price_ex_vat": str(item.item_total_price_ex_vat),
                "item_total_price_inc_vat": str(item.item_total_price_inc_vat),
                "vat": str(item.vat),
                "vat_percentage": str(item.vat_percentage),
                "currency": item.currency,
            })

        # Log receipt items count for debugging
        logger.info(
            "AI4 input for %s: %d receipt_items, vendor='%s', gross=%s, net=%s",
            request.file_id,
            len(items_data),
            request.vendor_name,
            request.gross_amount,
            request.net_amount
        )

        llm_result = self._provider_generate(
            "accounting_classification",
            {
                "receipt_id": request.file_id,
                "gross_amount": str(request.gross_amount),
                "net_amount": str(request.net_amount) if request.net_amount is not None else None,
                "vat_amount": str(request.vat_amount) if request.vat_amount is not None else None,
                "vendor_name": request.vendor_name,
                "receipt_items": items_data,
                "document_type": request.document_type,
                "expense_type": request.expense_type,
            },
        )

        # Detailed logging for debugging
        logger.info(
            "AI4 LLM response for %s: %s",
            request.file_id,
            json.dumps(llm_result, ensure_ascii=False)[:500] if llm_result else "None"
        )

        if not llm_result:
            raise AccountingProposalValidationError("LLM returned no data for accounting classification")

        try:
            proposals = parse_accounting_proposals(llm_result, request.file_id)
        except AccountingProposalValidationError as exc:
            logger.error(
                "Invalid AI4 payload for %s: %s. Full payload: %s",
                request.file_id,
                exc,
                json.dumps(llm_result, ensure_ascii=False)
            )
            raise

        if "confidence" in llm_result:
            try:
                confidence = float(llm_result["confidence"])
            except (TypeError, ValueError):  # pragma: no cover
                pass

        return AccountingClassificationResponse(
            file_id=request.file_id,
            proposals=proposals,
            confidence=confidence,
            based_on_bas2025=True,
        )

    # ------------------------------------------------------------------
    # AI5 - Credit card matching
    # ------------------------------------------------------------------
    def match_credit_card(
        self,
        request: CreditCardMatchRequest,
        potential_matches: List[Tuple[Any, ...]],
    ) -> CreditCardMatchResponse:
        logger.info("Matching credit card items for %s", request.file_id)

        best_match: Optional[Tuple[Any, ...]] = None
        for candidate in potential_matches:
            candidate_id, merchant_name, amount_sek = candidate
            if request.amount is not None and amount_sek is not None:
                diff = abs(Decimal(str(amount_sek)) - Decimal(str(request.amount)))
                if diff > Decimal("5.00"):
                    continue
            if request.merchant_name and merchant_name:
                if request.merchant_name.lower() not in merchant_name.lower():
                    continue
            best_match = candidate
            break

        if best_match:
            match_details = {
                "matched_merchant": best_match[1],
                "matched_amount": float(best_match[2]) if best_match[2] is not None else None,
            }
            llm_result = self._provider_generate(
                "credit_card_match",
                {
                    "receipt_amount": float(request.amount) if request.amount is not None else None,
                    "merchant_name": request.merchant_name,
                    "candidate": {
                        "merchant": best_match[1],
                        "amount": float(best_match[2]) if best_match[2] is not None else None,
                    },
                },
            )
            confidence_override: Optional[float] = None
            if llm_result:
                match_details.update(llm_result.get("overrides", {}))
                if "confidence" in llm_result:
                    try:
                        confidence_override = float(llm_result["confidence"])
                    except (TypeError, ValueError):  # pragma: no cover
                        confidence_override = None

            return CreditCardMatchResponse(
                file_id=request.file_id,
                matched=True,
                credit_card_invoice_item_id=best_match[0],
                confidence=confidence_override if confidence_override is not None else 0.9,
                match_details=match_details,
            )

        return CreditCardMatchResponse(
            file_id=request.file_id,
            matched=False,
            credit_card_invoice_item_id=None,
            confidence=0.45,
            match_details={"reason": "No transaction met the criteria"},
        )
