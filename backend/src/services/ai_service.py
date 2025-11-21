"""AI Service for processing receipts and documents."""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

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
from services.db.connection import db_cursor
from services.invoice_parser import parse_credit_card_statement
from services.ai.providers import (
    BaseLLMProvider,
    OpenAIProvider,
    ResponsesApiOpenAIProvider,
    AzureOpenAIProvider,
    OllamaProvider,
)
from services.ai.parsers import parse_accounting_proposals
from services.ai.parsers.common import (
    _deep_clean_dict,
    AccountingProposalValidationError,
)

logger = logging.getLogger(__name__)


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
        fc_tokens = ["firstcard", "first card", "kortmatchning", "kontoutdrag", "firstcard company", "kortfaktura"]

        receipt_hits = sum(token in text for token in receipt_tokens)
        invoice_hits = sum(token in text for token in invoice_tokens)
        fc_hits = sum(token in text for token in fc_tokens)

        llm_result = self._provider_generate(
            "document_analysis", {"ocr_text": request.ocr_text or ""}
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
                f"provider={self.prompt_provider_names.get('data_extraction', 'unknown')}, "
                f"model={self.prompt_model_names.get('data_extraction', 'unknown')}, "
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
        unified_data = llm_result.get("unified_file", {}) or {}

        # Serialize other_data if it's a dict
        other_data_value = unified_data.get("other_data")
        if isinstance(other_data_value, dict):
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

                        # Fix AI3 validation errors: convert number to integer
                        if "number" in item_dict:
                            try:
                                # Convert float to int (e.g., 25.35 -> 25)
                                item_dict["number"] = int(round(float(item_dict["number"])))
                            except (TypeError, ValueError):
                                logger.warning(
                                    "AI3 receipt_items[%d] has invalid number field, defaulting to 1",
                                    idx
                                )
                                item_dict["number"] = 1

                        # Fix AI3 validation errors: round decimal fields to 2 decimal places
                        decimal_fields = [
                            "item_price_ex_vat", "item_price_inc_vat",
                            "item_total_price_ex_vat", "item_total_price_inc_vat",
                            "vat", "vat_percentage"
                        ]
                        for field in decimal_fields:
                            if field in item_dict and item_dict[field] is not None:
                                try:
                                    # Round to 2 decimal places (e.g., 12.392 -> 12.39)
                                    item_dict[field] = round(float(item_dict[field]), 2)
                                except (TypeError, ValueError):
                                    # If conversion fails, leave as None
                                    item_dict[field] = None

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

    # ------------------------------------------------------------------
    # AI6 - Credit card invoice parsing
    # ------------------------------------------------------------------
    def parse_credit_card_invoice(
        self, request: CreditCardInvoiceExtractionRequest
    ) -> CreditCardInvoiceExtractionResponse:
        """Parse OCR text for a credit card invoice into structured data."""

        payload = {
            "invoice_id": request.invoice_id,
            "ocr_text": request.ocr_text,
            "page_ids": request.page_ids,
        }

        llm_result = self._provider_generate("credit_card_invoice_parsing", payload)
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
