"""AI Service for processing receipts and documents."""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import ValidationError

from models.ai_processing import (
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    CreditCardInvoiceExtractionRequest,
    CreditCardInvoiceExtractionResponse,
    CreditCardInvoiceHeader,
    CreditCardInvoiceLine,
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
from services.ai.providers import (
    BaseLLMProvider,
    ProviderResponse,
    OpenAIProvider,
    ResponsesApiOpenAIProvider,
    AzureOpenAIProvider,
    OllamaProvider,
)
from services.doc_type_rules import detect_deterministic_doc_type
from services.ai_logging import log_ai_call
from services.db.connection import db_cursor
from services.invoice_parser import parse_credit_card_statement


# Provider implementations moved to services.ai.providers to keep ai_service orchestration-only.
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


class AiProviderError(RuntimeError):
    """Raised when an upstream AI provider fails hard (e.g., HTTP 5xx)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


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


def _extract_account_code(entry: Dict[str, Any]) -> Optional[str]:
    """Extract account_code from entry. Returns None if not found (for filtering)."""
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
    return None  # Let caller decide whether to skip or raise


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
) -> Optional[AccountingProposal]:
    """Build an AccountingProposal from entry. Returns None if account_code is missing."""
    receipt_id = str(entry.get("receipt_id") or "").strip()
    if not receipt_id:
        receipt_id = expected_receipt_id
    if receipt_id != expected_receipt_id:
        raise AccountingProposalValidationError(
            f"receipt_id mismatch (expected {expected_receipt_id}, got {receipt_id})"
        )

    # item_id is optional - settlement/balancing lines may have null item_id
    raw_item_id = entry.get("item_id")
    item_id: Optional[int] = None
    if raw_item_id is not None:
        item_id = _coerce_item_id(raw_item_id, f"{context}.item_id")

    account_code = _extract_account_code(entry)
    if account_code is None:
        # LLM couldn't determine account - skip this entry with warning
        notes = entry.get("notes") or ""
        logger.warning(
            "AI4 skipped proposal %s: account_code is null. Notes: %s",
            context, notes[:100]
        )
        return None

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


def _looks_like_single_proposal_object(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    has_account = any(key in payload and payload.get(key) not in (None, "") for key in ACCOUNT_CODE_KEYS)
    has_debit = any(key in payload and payload.get(key) not in (None, "") for key in DEBIT_KEYS)
    has_credit = any(key in payload and payload.get(key) not in (None, "") for key in CREDIT_KEYS)
    return bool(has_account and (has_debit or has_credit))


def parse_accounting_proposals(payload: Any, fallback_receipt_id: str) -> List[AccountingProposal]:
    """Parse and validate AI4 payload into accounting proposals."""

    # Some prompts instruct the model to return a JSON array; some providers enforce json_object.
    # Accept list payloads by treating them as a proposals array.
    if isinstance(payload, list):
        payload = {"proposals": payload, "receipt_id": fallback_receipt_id}

    if not isinstance(payload, dict):
        raise AccountingProposalValidationError("LLM response must be a JSON object")

    receipt_id = str(payload.get("receipt_id") or fallback_receipt_id or "").strip()
    if not receipt_id:
        raise AccountingProposalValidationError("receipt_id is missing from payload")

    raw_entries: List[Tuple[Dict[str, Any], str]] = []

    # If the model returned a single proposal object at top-level (common when json_object is enforced),
    # normalize it into proposals=[...].
    if _looks_like_single_proposal_object(payload):
        payload = {"proposals": [payload], "receipt_id": receipt_id}

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
    elif payload.get("accounting_proposals") is not None:
        accounting_proposals = payload.get("accounting_proposals")
        if isinstance(accounting_proposals, dict):
            accounting_proposals = [accounting_proposals]
        if not isinstance(accounting_proposals, list) or not accounting_proposals:
            raise AccountingProposalValidationError("accounting_proposals must be a non-empty array")
        for idx, entry in enumerate(accounting_proposals, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"accounting_proposals[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"accounting_proposals[{idx}]"))
    elif payload.get("proposal") is not None:
        proposal = payload.get("proposal")
        if isinstance(proposal, dict):
            proposal = [proposal]
        if not isinstance(proposal, list) or not proposal:
            raise AccountingProposalValidationError("proposal must be a non-empty array")
        for idx, entry in enumerate(proposal, start=1):
            if not isinstance(entry, dict):
                raise AccountingProposalValidationError(f"proposal[{idx}] must be an object")
            normalized = dict(entry)
            normalized.setdefault("receipt_id", receipt_id)
            raw_entries.append((normalized, f"proposal[{idx}]"))
    else:
        raise AccountingProposalValidationError(
            "Payload must include either 'items', 'proposals', 'entries', or 'accounting_entries'"
        )

    parsed: List[AccountingProposal] = []
    skipped = 0
    for entry, context in raw_entries:
        proposal = _build_accounting_proposal(entry, receipt_id, context=context)
        if proposal is not None:
            parsed.append(proposal)
        else:
            skipped += 1

    if skipped > 0:
        logger.info("AI4 skipped %d proposals with missing account_code", skipped)

    if not parsed:
        raise AccountingProposalValidationError("No valid accounting proposals generated from payload")

    return parsed


def _normalize_optional_decimal(value: Any, field: str) -> Optional[Decimal]:
    if value is None:
        return None
    return _ensure_decimal(value, field)


def _validate_accounting_proposals(
    proposals: List[AccountingProposal],
    *,
    gross_amount: Any,
    net_amount: Any,
    vat_amount: Any,
    chart_of_accounts: List[Tuple[Any, ...]],
) -> None:
    if chart_of_accounts:
        valid_codes = {
            str(row[0]).strip()
            for row in chart_of_accounts
            if row and row[0] not in (None, "")
        }
        invalid_codes = sorted(
            {p.account_code for p in proposals if p.account_code not in valid_codes}
        )
        if invalid_codes:
            raise AccountingProposalValidationError(
                f"Unknown account_code(s): {', '.join(invalid_codes)}"
            )

    debit_total = sum((p.debit or ZERO_DECIMAL) for p in proposals)
    credit_total = sum((p.credit or ZERO_DECIMAL) for p in proposals)

    if (debit_total - credit_total).copy_abs() > TWO_DECIMAL_PLACES:
        raise AccountingProposalValidationError(
            f"Accounting proposals not balanced (debit={debit_total}, credit={credit_total})"
        )

    gross = _normalize_optional_decimal(gross_amount, "gross_amount")
    net = _normalize_optional_decimal(net_amount, "net_amount")
    vat = _normalize_optional_decimal(vat_amount, "vat_amount")

    if gross is not None:
        if (debit_total - gross).copy_abs() > TWO_DECIMAL_PLACES:
            raise AccountingProposalValidationError(
                f"Debit total {debit_total} does not match gross {gross}"
            )
        if (credit_total - gross).copy_abs() > TWO_DECIMAL_PLACES:
            raise AccountingProposalValidationError(
                f"Credit total {credit_total} does not match gross {gross}"
            )

    if gross is not None and net is not None and vat is not None:
        expected_gross = _quantize_two_decimals(net + vat)
        if (gross - expected_gross).copy_abs() > TWO_DECIMAL_PLACES:
            raise AccountingProposalValidationError(
                f"Gross {gross} does not match net+vat {expected_gross}"
            )

ORGNR_PATTERN = re.compile(r"\b\d{6}[- ]?\d{4}\b")
ISO_CURRENCY_PATTERN = re.compile(r"\b(USD|EUR|SEK|NOK|DKK|GBP)\b", re.IGNORECASE)
RECEIPT_NO_PATTERN = re.compile(r"(?:receipt|kvitto|nr|#)[:\s]*([A-Z0-9-]{3,})", re.IGNORECASE)
DATE_PATTERNS = [
    re.compile(r"(20\d{2}[-/](?:0\d|1[0-2])[-/](?:0\d|[12]\d|3[01]))[ T]*(\d{2}:\d{2})?"),
    re.compile(r"((?:0\d|[12]\d|3[01])[./](?:0\d|1[0-2])[./]20\d{2})"),
]


def _normalize_amount(token: str) -> Optional[Decimal]:
    cleaned = token.strip()
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace("\u00A0", "")  # NBSP
    cleaned = cleaned.replace("\u202F", "")  # Narrow NBSP
    cleaned = cleaned.replace("'", "")
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
        self.last_raw_response: Optional[str] = None
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
                            provider_adapter, resolved_name, resolved_model = self._init_provider(
                                provider_name,
                                model_name,
                                api_key,
                                endpoint_url,
                            )
                            self.prompt_providers[key] = provider_adapter
                            provider_label = resolved_name or provider_name or "none"
                            model_label = resolved_model or model_name or "none"
                            self.prompt_provider_names[key] = provider_label
                            self.prompt_model_names[key] = model_label
                            if provider_adapter:
                                logger.info(
                                    f"Loaded model for {key}: {provider_label}/{model_label}"
                                )
                            else:
                                logger.warning(
                                    f"No provider instance initialised for {key}; resolved provider/model="
                                    f"{provider_label}/{model_label}"
                                )
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
        self,
        provider_from_db: Optional[str],
        model_from_db: Optional[str],
        api_key_from_db: Optional[str] = None,
        endpoint_from_db: Optional[str] = None,
    ) -> tuple[Optional[BaseLLMProvider], str, str]:
        """Resolve the provider/model for a prompt using database configuration only.

        Returns a tuple of (provider_instance, resolved_provider_name, resolved_model_name).
        """
        resolved_provider_name = (provider_from_db or "").strip()
        resolved_model_name = (model_from_db or "").strip()
        endpoint = (endpoint_from_db or "").strip()

        if not resolved_provider_name:
            logger.error("No provider configured in database for selected model.")
            return None, "", resolved_model_name

        provider_key = resolved_provider_name.lower()

        if not resolved_model_name:
            logger.error("No model name configured in database for provider '%s'.", resolved_provider_name)
            return None, resolved_provider_name, ""

        try:
            if provider_key == "openai":
                return OpenAIProvider(resolved_model_name, api_key_from_db), resolved_provider_name, resolved_model_name
            if provider_key == "openai-responses-api":
                return ResponsesApiOpenAIProvider(resolved_model_name, api_key_from_db), resolved_provider_name, resolved_model_name
            if provider_key in {"azure", "azure_openai", "azure-openai"}:
                return (
                    AzureOpenAIProvider(resolved_model_name, api_key_from_db, endpoint or None),
                    resolved_provider_name,
                    resolved_model_name,
                )
            if provider_key == "ollama":
                if not endpoint:
                    logger.error("Ollama provider '%s' missing endpoint_url in ai_llm.", resolved_provider_name)
                    return None, resolved_provider_name, resolved_model_name
                return OllamaProvider(resolved_model_name, endpoint), resolved_provider_name, resolved_model_name
        except Exception as exc:  # pragma: no cover - configuration errors
            logger.warning("Failed to initialise LLM provider %s: %s", resolved_provider_name, exc)
            return None, resolved_provider_name, resolved_model_name

        logger.warning("Unknown AI provider '%s'; falling back to rule-based mode", resolved_provider_name)
        return None, resolved_provider_name, resolved_model_name

    def _provider_generate(
        self, stage_key: str, payload: Dict[str, Any], *, file_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        # ONLY use the prompt-specific provider - NO fallback
        provider = self.prompt_providers.get(stage_key)
        provider_name = self.prompt_provider_names.get(stage_key, "unknown")
        model_name = self.prompt_model_names.get(stage_key, "unknown")
        target_file_id = file_id or str(
            payload.get("file_id")
            or payload.get("invoice_id")
            or payload.get("receipt_id")
            or ""
        )

        if not provider:
            logger.error(
                f"No provider configured for {stage_key}. "
                f"Provider: {provider_name}, Model: {model_name}. "
                f"Please select a model for this prompt in the database."
            )
            if target_file_id:
                log_ai_call(
                    file_id=target_file_id,
                    job=stage_key,
                    status="error",
                    ai_stage_name=stage_key,
                    error_message="provider_not_configured",
                    provider=provider_name,
                    model_name=model_name,
                )
            return None

        prompt = self.prompts.get(stage_key, "")
        try:
            logger.debug(f"Calling {stage_key} with provider={provider_name}, model={model_name}")
            response = provider.generate(prompt=prompt, payload=payload)
            self.last_raw_response = response.raw

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
                if target_file_id:
                    log_ai_call(
                        file_id=target_file_id,
                        job=stage_key,
                        status="error",
                        ai_stage_name=stage_key,
                        error_message="empty_response",
                        provider=provider_name,
                        model_name=model_name,
                    )
                return None
            if response.parsed is not None:
                if target_file_id:
                    log_ai_call(
                        file_id=target_file_id,
                        job=stage_key,
                        status="success",
                        ai_stage_name=stage_key,
                        provider=provider_name,
                        model_name=model_name,
                    )
                return response.parsed

            # Handle raw text responses (wrap simple text in JSON for AI1/AI2)
            try:
                parsed_raw = json.loads(response.raw)
                if target_file_id:
                    log_ai_call(
                        file_id=target_file_id,
                        job=stage_key,
                        status="success",
                        ai_stage_name=stage_key,
                        provider=provider_name,
                        model_name=model_name,
                    )
                return parsed_raw
            except json.JSONDecodeError:
                raw_text = response.raw.strip()
                if stage_key == "document_analysis":
                    if target_file_id:
                        log_ai_call(
                            file_id=target_file_id,
                            job=stage_key,
                            status="success",
                            ai_stage_name=stage_key,
                            provider=provider_name,
                            model_name=model_name,
                        )
                    return {"document_type": raw_text, "confidence": 0.8}
                elif stage_key == "expense_classification":
                    if target_file_id:
                        log_ai_call(
                            file_id=target_file_id,
                            job=stage_key,
                            status="success",
                            ai_stage_name=stage_key,
                            provider=provider_name,
                            model_name=model_name,
                        )
                    return {"expense_type": raw_text, "confidence": 0.8}
                else:
                    logger.warning(f"Provider {provider_name}/{model_name} returned raw text for {stage_key}, expected JSON: {raw_text[:100]}")
                    return None
        except Exception as exc:  # pragma: no cover - network/parse errors
            logger.error("Provider call for %s failed (provider=%s, model=%s): %s", stage_key, provider_name, model_name, exc, exc_info=True)
            if target_file_id:
                log_ai_call(
                    file_id=target_file_id,
                    job=stage_key,
                    status="error",
                    ai_stage_name=stage_key,
                    error_message=str(exc),
                    provider=provider_name,
                    model_name=model_name,
                )
            raise AiProviderError("provider_failed", str(exc))

    # ------------------------------------------------------------------
    # AI1 - Document classification
    # ------------------------------------------------------------------
    def run_ai1_document_classification(self, request: DocumentClassificationRequest) -> DocumentClassificationResponse:
        text = (request.ocr_text or "").lower()
        logger.info("Classifying document %s", request.file_id)

        doc_type = "Manual Review"
        confidence = 0.0
        reasoning_parts: List[str] = []

        deterministic_doc_type, deterministic_reason = detect_deterministic_doc_type(text)
        deterministic_override = deterministic_doc_type is not None

        receipt_tokens = ["kvitto", "receipt", "summa", "moms", "butik", "kundens kvitto"]
        invoice_tokens = ["invoice", "faktura", "förfallodatum", "ocr", "betalning"]
        fc_tokens = ["firstcard", "first card", "kortmatchning", "kontoutdrag", "firstcard company", "kortfaktura"]

        receipt_hits = sum(token in text for token in receipt_tokens)
        invoice_hits = sum(token in text for token in invoice_tokens)
        fc_hits = sum(token in text for token in fc_tokens)

        if not deterministic_override:
            llm_result = self._provider_generate(
                "document_analysis", {"ocr_text": request.ocr_text or ""}, file_id=request.file_id
            )
            if llm_result:
                doc_type = llm_result.get("document_type", doc_type)
                confidence = float(llm_result.get("confidence", confidence))
                reasoning_parts.append("LLM-assisted classification")

        if fc_hits:
            doc_type = "fc_invoice"
            confidence = min(0.98, 0.5 + 0.1 * fc_hits)
            reasoning_parts.append("FirstCard invoice keywords detected")
        elif receipt_hits and receipt_hits >= invoice_hits:
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

        if deterministic_override:
            doc_type = deterministic_doc_type or doc_type
            confidence = max(confidence, 0.95)
            reasoning_parts.append(f"Deterministic rule: {deterministic_reason}")

        prompt_hint = self.prompts.get("document_analysis")
        if prompt_hint:
            reasoning_parts.append(f"Prompt hint provided: {prompt_hint}")

        return DocumentClassificationResponse(
            file_id=request.file_id,
            document_type=doc_type,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts) or None,
        )

    def classify_document(self, request: DocumentClassificationRequest) -> DocumentClassificationResponse:
        """Backward-compatible wrapper. Prefer run_ai1_document_classification."""
        return self.run_ai1_document_classification(request)

    # ------------------------------------------------------------------
    # AI2 - Expense classification
    # ------------------------------------------------------------------
    def run_ai2_expense_classification(self, request: ExpenseClassificationRequest) -> ExpenseClassificationResponse:
        text = (request.ocr_text or "").lower()
        logger.info("Classifying expense for %s", request.file_id)

        expense_type = "personal"
        confidence = 0.60
        reasoning_parts: List[str] = []
        card_identifier: Optional[str] = None

        def _extract_last4(ocr_text: str) -> Optional[str]:
            patterns = [
                r"(?:\*{2,}|x{2,}|#){2,}\s*([0-9]{4})",
                r"(?:kort|card)\s*(?:nr|no|number)?\s*[:\-]?\s*.*?([0-9]{4})\b",
                r"\b([0-9]{4})\b\s*(?:contactless|blipp|tap)?\b",
            ]
            for pat in patterns:
                match = re.search(pat, ocr_text, flags=re.IGNORECASE | re.DOTALL)
                if match:
                    return match.group(1)
            return None

        is_cash = any(token in text for token in ("kontant", "cash"))
        is_swish = "swish" in text
        is_visa = "visa" in text
        is_mastercard = "mastercard" in text or "master card" in text

        if is_cash or is_swish:
            expense_type = "personal"
            confidence = 0.95
            reasoning_parts.append("Detected swish/cash indicator")
        elif is_visa:
            expense_type = "personal"
            confidence = 0.90
            card_identifier = "VISA"
            reasoning_parts.append("Detected VISA indicator")
        elif is_mastercard:
            last4 = _extract_last4(text)
            if last4:
                card_identifier = f"MC-{last4}"
                if last4 == "9995":
                    expense_type = "personal"
                    confidence = 0.95
                    reasoning_parts.append("MasterCard last4=9995 => personal")
                elif last4 in ("6779", "4668"):
                    expense_type = "corporate"
                    confidence = 0.95
                    reasoning_parts.append(f"MasterCard last4={last4} => corporate")
                else:
                    expense_type = "personal"
                    confidence = 0.70
                    reasoning_parts.append(f"MasterCard last4={last4} not in corporate set => personal")
            else:
                expense_type = "personal"
                confidence = 0.65
                reasoning_parts.append("MasterCard indicator but last4 not extracted => personal")
        else:
            expense_type = "personal"
            confidence = 0.65
            reasoning_parts.append("Defaulting to personal expense")

        llm_result = self._provider_generate(
            "expense_classification",
            {"ocr_text": request.ocr_text or "", "document_type": request.document_type},
            file_id=request.file_id,
        )
        if llm_result:
            llm_expense_type = llm_result.get("expense_type")
            llm_confidence = float(llm_result.get("confidence", confidence))
            if llm_expense_type and llm_expense_type == expense_type:
                confidence = max(confidence, llm_confidence)
                reasoning_parts.append("LLM confirmed deterministic expense classification")
            else:
                reasoning_parts.append("LLM suggestion ignored due to deterministic rules")
            if not card_identifier and llm_result.get("card_identifier"):
                card_identifier = llm_result["card_identifier"]

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

    def classify_expense(self, request: ExpenseClassificationRequest) -> ExpenseClassificationResponse:
        """Backward-compatible wrapper. Prefer run_ai2_expense_classification."""
        return self.run_ai2_expense_classification(request)

    # ------------------------------------------------------------------
    # AI3 - Data extraction
    # ------------------------------------------------------------------
    def run_ai3_data_extraction(self, request: DataExtractionRequest) -> DataExtractionResponse:
        """
        AI3 - Extract ALL business data from OCR text using LLM.
        NO rule-based extraction allowed - only LLM extracts business data!
        """
        ocr_text = request.ocr_text or ""
        logger.info("Extracting structured data via LLM for %s", request.file_id)

        def _parse_purchase_datetime(raw_value: Any) -> Optional[datetime]:
            """Normalise purchase_datetime to a datetime object in YYYY-MM-DD HH:MM:SS."""
            if raw_value in (None, "", False):
                return None
            if isinstance(raw_value, datetime):
                return raw_value
            if isinstance(raw_value, date):
                return datetime.combine(raw_value, datetime.min.time())
            if isinstance(raw_value, str):
                text = raw_value.strip().replace("T", " ")
                if not text:
                    return None
                # Try strict formats first
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        parsed = datetime.strptime(text, fmt)
                        if fmt == "%Y-%m-%d":
                            parsed = datetime.combine(parsed.date(), datetime.min.time())
                        return parsed
                    except ValueError:
                        continue
                try:
                    return datetime.fromisoformat(text)
                except Exception as exc:  # pragma: no cover - defensive
                    raise ValueError(f"Invalid purchase_datetime format: {raw_value!r}") from exc
            raise ValueError(f"Unsupported purchase_datetime type: {type(raw_value).__name__}")

        # ONLY LLM extracts data - call LLM provider
        llm_result = self._provider_generate(
            "data_extraction",
            {
                "file_id": request.file_id,
                "ocr_text": ocr_text,
                "document_type": request.document_type,
                "expense_type": request.expense_type,
            },
            file_id=request.file_id,
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

        required_keys = ["company", "unified_file", "receipt_items", "company_match_type", "company_create_needed"]
        missing_keys = [k for k in required_keys if k not in llm_result]
        if missing_keys:
            raise ValueError(f"AI3 response missing required fields: {', '.join(missing_keys)}")

        # Extract data from LLM response
        confidence = 0.5
        if "confidence" in llm_result:
            try:
                confidence = float(llm_result["confidence"])
            except (TypeError, ValueError):
                pass

        # Extract unified_file data from LLM
        unified_data = llm_result.get("unified_file", {}) or {}
        if unified_data in (None, {}):
            raise ValueError("AI3 response missing unified_file payload")

        # Serialize other_data if it's a dict
        other_data_value = unified_data.get("other_data")
        if isinstance(other_data_value, dict):
            other_data_value = json.dumps(other_data_value, ensure_ascii=False)
        elif isinstance(other_data_value, str):
            try:
                json.loads(other_data_value)
            except Exception:
                # Wrap arbitrary string as JSON string to satisfy storage expectations
                other_data_value = json.dumps({"raw_other_data": other_data_value}, ensure_ascii=False)
        elif other_data_value is None:
            other_data_value = "{}"
        else:
            # Fallback to JSON-serialise any other type
            other_data_value = json.dumps(other_data_value, ensure_ascii=False)

        # Handle common aliases for last four digits
        card_last_4 = unified_data.get("credit_card_last_4_digits")
        if card_last_4 in (None, "", 0):
            card_last_4 = unified_data.get("credit_card_last_4")
        # Let Pydantic coerce to int; just ensure empty strings become None
        if isinstance(card_last_4, str) and not card_last_4.strip():
            card_last_4 = None

        unified_file = UnifiedFileBase(
            file_type=request.document_type,
            vat=unified_data.get("vat") or unified_data.get("orgnr"),
            orgnr=unified_data.get("vat") or unified_data.get("orgnr"),
            payment_type=unified_data.get("payment_type"),
            purchase_datetime=_parse_purchase_datetime(unified_data.get("purchase_datetime")),
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
            credit_card_number=unified_data.get("credit_card_number"),
            credit_card_last_4_digits=card_last_4,
            credit_card_brand_full=unified_data.get("credit_card_brand_full"),
            credit_card_brand_short=unified_data.get("credit_card_brand_short"),
            credit_card_payment_variant=unified_data.get("credit_card_payment_variant"),
            credit_card_type=unified_data.get("credit_card_type"),
            credit_card_token=unified_data.get("credit_card_token"),
            credit_card_entering_mode=unified_data.get("credit_card_entering_mode"),
        )

        # Extract company data from LLM
        company_data = llm_result.get("company", {})
        if company_data in (None, {}):
            raise ValueError("AI3 response missing company payload")
        company = Company(
            name=company_data.get("name"),
            vat=company_data.get("vat") or company_data.get("orgnr"),
            orgnr=company_data.get("vat") or company_data.get("orgnr"),
            address=company_data.get("address"),
            address2=company_data.get("address2"),
            zip=company_data.get("zip"),
            city=company_data.get("city"),
            country=company_data.get("country"),
            phone=company_data.get("phone"),
            www=company_data.get("www"),
            email=company_data.get("email"),
        )

        # Extract receipt items from LLM
        receipt_items: List[ReceiptItem] = []
        llm_items_raw = llm_result.get("receipt_items")

        if llm_items_raw is None:
            raise ValueError("AI3 response missing receipt_items")

        if llm_items_raw:
            if not isinstance(llm_items_raw, list):
                raise ValueError("LLM receipt_items must be provided as a list of objects")
            logger.info(
                "AI3 LLM returned %d raw receipt_items for file_id=%s",
                len(llm_items_raw),
                request.file_id
            )
            for idx, raw_item in enumerate(llm_items_raw, 1):
                item_payload = dict(raw_item or {})
                item_main_id = item_payload.get("main_id")
                if not item_main_id or item_main_id != request.file_id:
                    if item_main_id:
                        logger.warning(
                            "AI3 receipt_items[%d] has main_id='%s' but file_id='%s' - correcting",
                            idx, item_main_id, request.file_id
                        )
                    item_payload["main_id"] = request.file_id

                if item_payload.get("article_id") is None:
                    item_payload["article_id"] = ""
                if "number" not in item_payload:
                    item_payload["number"] = 1

                try:
                    parsed_item = ReceiptItem(**item_payload)
                except ValidationError as exc:
                    logger.error(
                        "AI3 receipt_items[%d] invalid for file_id=%s: %s",
                        idx,
                        request.file_id,
                        exc,
                    )
                    raise ValueError(f"Invalid receipt_items[{idx}] payload") from exc

                receipt_items.append(parsed_item)
                logger.debug(
                    "AI3 parsed receipt_items[%d]: name='%s', qty=%d, article_id='%s', total_inc_vat=%s",
                    idx, parsed_item.name, parsed_item.number,
                    parsed_item.article_id or 'N/A', parsed_item.item_total_price_inc_vat
                )
        else:
            logger.warning(
                "AI3 LLM returned NO receipt_items for file_id=%s (this may be legitimate for some documents)",
                request.file_id
            )

        logger.info(
            "LLM extracted: company='%s', vat/orgnr='%s', gross=%s, items=%d, confidence=%.2f",
            company.name,
            company.vat or company.orgnr,
            unified_file.gross_amount_original,
            len(receipt_items),
            confidence,
        )

        match_type_raw = llm_result.get("company_match_type")
        if isinstance(match_type_raw, str):
            match_type = match_type_raw.strip().lower()
            synonyms = {
                "vat_match": "vat",
                "orgnr": "vat",
                "name_match": "name",
                "new_company": "new",
            }
            match_type = synonyms.get(match_type, match_type)
        else:
            match_type = None
        if match_type not in {"vat", "name", "new"}:
            raise ValueError("AI3 response missing or invalid company_match_type")

        if "company_create_needed" not in llm_result:
            raise ValueError("AI3 response missing company_create_needed")
        company_create_needed = bool(llm_result.get("company_create_needed"))

        return DataExtractionResponse(
            file_id=request.file_id,
            unified_file=unified_file,
            receipt_items=receipt_items,
            company=company,
            confidence=confidence,
            company_match_type=match_type,
            company_create_needed=company_create_needed,
        )

    def extract_data(self, request: DataExtractionRequest) -> DataExtractionResponse:
        """Backward-compatible wrapper. Prefer run_ai3_data_extraction."""
        return self.run_ai3_data_extraction(request)

    # ------------------------------------------------------------------
    # AI4 - Accounting classification
    # ------------------------------------------------------------------
    def _format_chart_of_accounts(self, chart_of_accounts: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
        """Format chart_of_accounts for LLM consumption.

        Input tuples: (sub_account, sub_account_description)
        Output: Compact list of account objects for LLM.
        """
        formatted = []
        for row in chart_of_accounts:
            if len(row) >= 2 and row[0]:  # Must have sub_account
                formatted.append({
                    "code": str(row[0]),
                    "name": str(row[1]) if row[1] else "",
                })
        return formatted

    def run_ai4_accounting_classification(
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

        # Format chart_of_accounts for LLM
        formatted_accounts = self._format_chart_of_accounts(chart_of_accounts)
        logger.info(
            "AI4 chart_of_accounts for %s: %d accounts available",
            request.file_id,
            len(formatted_accounts)
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
                "chart_of_accounts": formatted_accounts,
            },
            file_id=request.file_id,
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
            _validate_accounting_proposals(
                proposals,
                gross_amount=request.gross_amount,
                net_amount=request.net_amount,
                vat_amount=request.vat_amount,
                chart_of_accounts=chart_of_accounts,
            )
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

    def classify_accounting(
        self,
        request: AccountingClassificationRequest,
        chart_of_accounts: List[Tuple[Any, ...]],
    ) -> AccountingClassificationResponse:
        """Backward-compatible wrapper. Prefer run_ai4_accounting_classification."""
        return self.run_ai4_accounting_classification(request, chart_of_accounts)

    # ------------------------------------------------------------------
    # AI5 - Credit card matching
    # ------------------------------------------------------------------
    def run_ai5_credit_card_match(
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
                file_id=request.file_id,
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

    def match_credit_card(
        self,
        request: CreditCardMatchRequest,
        potential_matches: List[Tuple[Any, ...]],
    ) -> CreditCardMatchResponse:
        """Backward-compatible wrapper. Prefer run_ai5_credit_card_match."""
        return self.run_ai5_credit_card_match(request, potential_matches)

    # ------------------------------------------------------------------
    # AI6 - Credit card invoice parsing
    # ------------------------------------------------------------------
    def run_ai6_credit_card_invoice_parsing(
        self, request: CreditCardInvoiceExtractionRequest
    ) -> CreditCardInvoiceExtractionResponse:
        """Parse OCR text for a credit card invoice into structured data."""

        payload = {
            "invoice_id": request.invoice_id,
            "ocr_text": request.ocr_text,
            "page_ids": request.page_ids,
        }

        llm_result = self._provider_generate(
            "credit_card_invoice_parsing",
            payload,
            file_id=request.invoice_id,
        )
        if llm_result:
            try:
                header_payload = llm_result.get("header") or {}
                header_model = CreditCardInvoiceHeader(**header_payload)

                lines_payload = llm_result.get("lines") or []
                normalised_lines: List[CreditCardInvoiceLine] = []
                for idx, raw_line in enumerate(lines_payload, 1):
                    line_data = dict(raw_line or {})
                    line_data.setdefault("line_no", idx)
                    normalised_lines.append(CreditCardInvoiceLine(**line_data))

                response = CreditCardInvoiceExtractionResponse(
                    invoice_id=request.invoice_id,
                    header=header_model,
                    lines=normalised_lines,
                    overall_confidence=llm_result.get("overall_confidence"),
                )
                return response
            except ValidationError as exc:
                logger.error(
                    "AI6 response validation failed for %s: %s",
                    request.invoice_id,
                    exc,
                )
            except Exception as exc:
                logger.error(
                    "AI6 parsing raised unexpected error for %s: %s",
                    request.invoice_id,
                    exc,
                )

        logger.info(
            "Falling back to rule-based credit card parsing for invoice %s",
            request.invoice_id,
        )
        return self._fallback_credit_card_invoice_parse(request)

    def _fallback_credit_card_invoice_parse(
        self, request: CreditCardInvoiceExtractionRequest
    ) -> CreditCardInvoiceExtractionResponse:
        parsed = parse_credit_card_statement(request.ocr_text)

        header = CreditCardInvoiceHeader(
            invoice_number=request.invoice_id,
            period_start=self._safe_parse_date(parsed.get("period_start")),
            period_end=self._safe_parse_date(parsed.get("period_end")),
            currency="SEK",
        )

        lines: List[CreditCardInvoiceLine] = []
        total_amount = Decimal("0.00")
        confidences: List[float] = []

        for idx, raw_line in enumerate(parsed.get("lines") or [], 1):
            amount = Decimal(str(raw_line.get("amount") or 0))
            total_amount += amount
            confidence = float(raw_line.get("confidence") or 0.75)
            confidences.append(confidence)
            line = CreditCardInvoiceLine(
                line_no=idx,
                purchase_date=self._safe_parse_date(raw_line.get("transaction_date")),
                merchant_name=raw_line.get("merchant_name"),
                description=raw_line.get("description"),
                currency_original="SEK",
                amount_original=amount,
                amount_sek=amount,
                gross_amount=amount,
                confidence=confidence,
                source_text=raw_line.get("raw_text"),
            )
            lines.append(line)

        header.invoice_total = total_amount if lines else None
        header.amount_to_pay = total_amount if lines else None
        header.card_total = total_amount if lines else None

        overall_confidence = None
        if confidences:
            overall_confidence = sum(confidences) / len(confidences)

        return CreditCardInvoiceExtractionResponse(
            invoice_id=request.invoice_id,
            header=header,
            lines=lines,
            overall_confidence=overall_confidence,
        )

    def parse_credit_card_invoice(
        self, request: CreditCardInvoiceExtractionRequest
    ) -> CreditCardInvoiceExtractionResponse:
        """Backward-compatible wrapper. Prefer run_ai6_credit_card_invoice_parsing."""
        return self.run_ai6_credit_card_invoice_parsing(request)

    @staticmethod
    def _safe_parse_date(value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, date):
            return value
        try:
            parsed = datetime.fromisoformat(str(value))
            return parsed.date()
        except Exception:
            return None
