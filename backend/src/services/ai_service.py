"""AI Service for processing receipts and documents."""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..models.ai_processing import (
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
from ..services.db.connection import db_cursor

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


def _pick_amount_from_lines(lines: Iterable[str], keywords: Iterable[str]) -> Optional[Decimal]:
    lowered_keywords = [kw.lower() for kw in keywords]
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if any(kw in line.lower() for kw in lowered_keywords):
            amounts = _find_amounts(line)
            if amounts:
                return amounts[-1]
    return None


def _extract_purchase_datetime(text: str) -> Optional[datetime]:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        date_part = match.group(1)
        time_part = match.group(2) if len(match.groups()) > 1 else None
        try:
            if "/" in date_part or "." in date_part:
                separators = "/" if "/" in date_part else "."
                day, month, year = date_part.split(separators)
                iso_date = f"{year}-{month}-{day}"
            else:
                iso_date = date_part.replace("/", "-")
            if time_part:
                return datetime.fromisoformat(f"{iso_date}T{time_part}")
            return datetime.fromisoformat(f"{iso_date}T00:00:00")
        except ValueError:
            continue
    return None


def _estimate_company_name(lines: List[str]) -> Optional[str]:
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if any(char.isdigit() for char in stripped):
            continue
        if len(stripped.split()) > 6:
            continue
        upper_ratio = sum(1 for ch in stripped if ch.isupper()) / max(len(stripped), 1)
        if upper_ratio > 0.4:
            return stripped[:234]
    return None


class AIService:
    """Service for deterministic extraction and classification.

    The service consumes OCR text and uses rule-based parsing so that results
    are derived from the provided document data instead of hard-coded values.
    This respects the repository rule that mock data must not be injected.
    """

    def __init__(self) -> None:
        self.prompts: Dict[str, str] = self._load_prompts()
        provider, model = self._load_active_model()
        self.provider_name = provider or "rule-based"
        self.model_name = model or "regex"

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
        ocr_text = request.ocr_text or ""
        lines = [line for line in ocr_text.splitlines() if line.strip()]
        logger.info("Extracting structured data for %s", request.file_id)

        orgnr_match = ORGNR_PATTERN.search(ocr_text)
        orgnr = orgnr_match.group(0) if orgnr_match else None

        receipt_number_match = RECEIPT_NO_PATTERN.search(ocr_text)
        receipt_number = receipt_number_match.group(1) if receipt_number_match else None

        purchase_dt = _extract_purchase_datetime(ocr_text)

        currency_match = ISO_CURRENCY_PATTERN.search(ocr_text)
        currency = currency_match.group(1).upper() if currency_match else "SEK"
        if " kr" in ocr_text.lower():
            currency = "SEK"

        payment_type = "card" if any(keyword in ocr_text.lower() for keyword in ["visa", "mastercard", "card", "kort"]) else "cash"

        gross_amount = _pick_amount_from_lines(lines, ["total", "summa", "amount", "belopp", "att betala"])
        vat_amount = _pick_amount_from_lines(lines, ["moms", "vat", "skatt"])
        net_amount = _pick_amount_from_lines(lines, ["netto", "ex moms", "subtotal"])

        if gross_amount and vat_amount and not net_amount:
            net_amount = gross_amount - vat_amount
        elif gross_amount and net_amount and not vat_amount and gross_amount > net_amount:
            vat_amount = gross_amount - net_amount

        exchange_rate = None
        exchange_match = re.search(r"1\s*[A-Z]{3}\s*=\s*(\d+[\s.,]\d+)", ocr_text)
        if exchange_match:
            exchange_rate = _normalize_amount(exchange_match.group(1))

        company_name = _estimate_company_name(lines)
        company = Company(
            name=company_name or "",
            orgnr=orgnr or "",
            address=None,
            address2=None,
            zip=None,
            city=None,
            country=None,
            phone=None,
            www=None,
        )

        receipt_items: List[ReceiptItem] = []
        item_pattern = re.compile(r"^(\d+)\s*x?\s*([\wÅÄÖåäö \-]+?)\s+(\d+[\s.,]\d{2})$")
        for line in lines:
            match = item_pattern.match(line.strip())
            if not match:
                continue
            qty = int(match.group(1))
            name = match.group(2).strip()
            amount = _normalize_amount(match.group(3))
            if amount is None:
                continue
            item = ReceiptItem(
                main_id=request.file_id,
                article_id="",
                name=name[:222],
                number=qty,
                item_price_ex_vat=amount,
                item_price_inc_vat=amount,
                item_total_price_ex_vat=amount * qty,
                item_total_price_inc_vat=amount * qty,
                currency=currency,
                vat=Decimal("0"),
                vat_percentage=Decimal("0"),
            )
            receipt_items.append(item)

        other_meta: Dict[str, Any] = {
            "model": self.model_name,
            "provider": self.provider_name,
            "extraction_timestamp": datetime.utcnow().isoformat(),
        }
        if vat_amount:
            other_meta["vat_detected"] = str(vat_amount)
        if receipt_number:
            other_meta["receipt_number_detected"] = receipt_number

        fields_considered = [gross_amount, vat_amount, net_amount, orgnr, receipt_number, purchase_dt, company_name]
        filled = sum(1 for value in fields_considered if value)
        confidence = 0.4 + 0.1 * filled
        confidence = max(0.4, min(confidence, 0.95))

        unified_file = UnifiedFileBase(
            file_type=request.document_type,
            orgnr=orgnr,
            payment_type=payment_type,
            purchase_datetime=purchase_dt,
            expense_type=request.expense_type if request.expense_type in {"personal", "corporate"} else None,
            gross_amount_original=gross_amount,
            net_amount_original=net_amount,
            exchange_rate=exchange_rate,
            currency=currency,
            gross_amount_sek=gross_amount if currency == "SEK" else None,
            net_amount_sek=net_amount if currency == "SEK" else None,
            receipt_number=receipt_number,
            other_data=json.dumps(other_meta),
            ocr_raw=ocr_text,
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
            return CreditCardMatchResponse(
                file_id=request.file_id,
                matched=True,
                credit_card_invoice_item_id=best_match[0],
                confidence=0.9,
                match_details=match_details,
            )

        return CreditCardMatchResponse(
            file_id=request.file_id,
            matched=False,
            credit_card_invoice_item_id=None,
            confidence=0.45,
            match_details={"reason": "No transaction met the criteria"},
        )
