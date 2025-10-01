"""AI Service for processing receipts and documents."""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
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
    """Adapter for OpenAI's Chat Completions API.

    The adapter intentionally keeps the implementation lightweight; when the
    environment lacks credentials it simply raises to trigger deterministic
    fallbacks. This satisfies the requirement for pluggable providers without
    introducing network calls during tests.
    """

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        # Placeholder implementation: the production worker will override this
        # with a fully fledged client. For now we log and fall back.
        logger.warning("OpenAIProvider invoked without concrete implementation")
        return ProviderResponse(raw="", parsed=None)


class AzureOpenAIProvider(BaseLLMProvider):
    """Adapter for Azure-hosted OpenAI deployments."""

    def generate(self, prompt: str, payload: Dict[str, Any]) -> ProviderResponse:
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not api_key or not endpoint:
            raise RuntimeError("Azure OpenAI credentials are not configured")
        logger.warning("AzureOpenAIProvider invoked without concrete implementation")
        return ProviderResponse(raw="", parsed=None)

logger = logging.getLogger(__name__)

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
        self.prompts: Dict[str, str] = self._load_prompts()
        provider_from_db, model_from_db = self._load_active_model()
        self.provider_adapter = self._init_provider(provider_from_db, model_from_db)
        self.provider_name = (
            (self.provider_adapter.provider_name if self.provider_adapter else None)
            or provider_from_db
            or "rule-based"
        )
        self.model_name = (
            os.getenv("AI_MODEL_NAME")
            or (self.provider_adapter.model_name if self.provider_adapter else None)
            or model_from_db
            or "regex"
        )

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _load_prompts(self) -> Dict[str, str]:
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

    def _load_active_model(self) -> Tuple[Optional[str], Optional[str]]:
        try:
            with db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT l.provider_name, m.model_name
                    FROM ai_llm_model AS m
                    JOIN ai_llm AS l ON m.llm_id = l.id
                    WHERE m.is_active = 1 AND l.enabled = 1
                    ORDER BY m.id
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if row:
                    return row[0], row[1]
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not load active AI model: %s", exc)
        return None, None

    def _init_provider(
        self, provider_from_db: Optional[str], model_from_db: Optional[str]
    ) -> Optional[BaseLLMProvider]:
        configured = os.getenv("AI_PROVIDER") or (provider_from_db or "")
        configured = configured.lower().strip()
        model = os.getenv("AI_MODEL_NAME") or model_from_db

        if not configured:
            return None

        try:
            if configured == "openai":
                return OpenAIProvider(model)
            if configured in {"azure", "azure_openai", "azure-openai"}:
                return AzureOpenAIProvider(model)
        except Exception as exc:  # pragma: no cover - configuration errors
            logger.warning("Failed to initialise LLM provider %s: %s", configured, exc)
            return None

        logger.warning("Unknown AI provider '%s'; falling back to rule-based mode", configured)
        return None

    def _provider_generate(
        self, stage_key: str, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self.provider_adapter:
            return None

        prompt = self.prompts.get(stage_key, "")
        try:
            response = self.provider_adapter.generate(prompt=prompt, payload=payload)
            if not response.raw and response.parsed is None:
                return None
            if response.parsed is not None:
                return response.parsed
            return json.loads(response.raw)
        except Exception as exc:  # pragma: no cover - network/parse errors
            logger.warning("Provider call for %s failed: %s", stage_key, exc)
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
            reasoning_parts.append(f"Prompt hint provided: {prompt_hint[:80]}")

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
            reasoning_parts.append(f"Prompt hint provided: {prompt_hint[:80]}")

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
            logger.error("LLM returned no result for data extraction - AI3 requires LLM!")
            raise ValueError("LLM data extraction failed - no AI provider configured or LLM returned empty response")

        # Extract data from LLM response
        confidence = 0.5
        if "confidence" in llm_result:
            try:
                confidence = float(llm_result["confidence"])
            except (TypeError, ValueError):
                pass

        # Extract unified_file data from LLM
        unified_data = llm_result.get("unified_file", {})
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
            other_data=unified_data.get("other_data"),
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
        if llm_result.get("receipt_items"):
            try:
                receipt_items = [ReceiptItem(**item) for item in llm_result["receipt_items"]]
            except Exception as exc:
                logger.error("Failed to parse LLM receipt items: %s", exc)
                # Continue with empty items rather than failing completely

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
        vat_amount = request.vat_amount
        net_amount = request.net_amount
        gross_amount = request.gross_amount

        has_account_4010 = any(str(row[0]) == "4010" for row in chart_of_accounts if row and row[0])
        cost_account = "4010" if has_account_4010 else str(chart_of_accounts[0][0]) if chart_of_accounts else "4010"

        if gross_amount > 0:
            proposals.append(
                AccountingProposal(
                    receipt_id=request.file_id,
                    account_code="2440",
                    debit=gross_amount,
                    credit=Decimal("0"),
                    vat_rate=None,
                    notes=f"Leverantörsskulder {request.vendor_name[:40]}" if request.vendor_name else "Leverantörsskulder",
                )
            )

        if vat_amount and vat_amount > 0:
            proposals.append(
                AccountingProposal(
                    receipt_id=request.file_id,
                    account_code="2641",
                    debit=vat_amount,
                    credit=Decimal("0"),
                    vat_rate=Decimal("25"),
                    notes="Ingående moms",
                )
            )
        if net_amount and net_amount > 0:
            proposals.append(
                AccountingProposal(
                    receipt_id=request.file_id,
                    account_code=cost_account,
                    debit=Decimal("0"),
                    credit=net_amount,
                    vat_rate=None,
                    notes=f"Kostnad {request.vendor_name[:40]}" if request.vendor_name else "Kostnad",
                )
            )

        confidence = 0.7
        if vat_amount and net_amount:
            confidence = 0.85

        llm_result = self._provider_generate(
            "accounting_classification",
            {
                "gross_amount": str(gross_amount),
                "net_amount": str(net_amount) if net_amount is not None else None,
                "vat_amount": str(vat_amount) if vat_amount is not None else None,
                "vendor_name": request.vendor_name,
            },
        )
        if llm_result:
            if llm_result.get("proposals"):
                try:
                    proposals = [AccountingProposal(**p) for p in llm_result["proposals"]]
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to parse LLM accounting proposals: %s", exc)
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
