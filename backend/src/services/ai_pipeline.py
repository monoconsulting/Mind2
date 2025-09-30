"""End-to-end orchestration helpers for AI1–AI5 stages.

The Celery workers use this module to execute deterministic AI stages in the
order defined by the system documentation.  Each stage delegates to the
``AIService`` for rule-based inference and relies on ``ai_persistence`` to
update the relational schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Sequence

from models.ai_processing import (
    AccountingClassificationRequest,
    CreditCardMatchRequest,
    DataExtractionRequest,
    DocumentClassificationRequest,
    ExpenseClassificationRequest,
    ReceiptItem,
)
from services.ai_service import AIService
from services.ai_persistence import (
    fetch_chart_of_accounts,
    fetch_company_name,
    fetch_credit_card_candidates,
    fetch_pipeline_context,
    persist_accounting_proposals,
    persist_credit_card_match,
    persist_document_classification,
    persist_expense_classification,
    persist_extraction_result,
)


class PipelineExecutionError(RuntimeError):
    """Raised when the pipeline cannot continue due to missing data."""


@dataclass
class PipelineContext:
    file_id: str
    ocr_text: str
    document_type: Optional[str]
    expense_type: Optional[str]
    purchase_datetime: Optional[datetime]
    gross_amount: Optional[Decimal]
    net_amount: Optional[Decimal]
    vendor_name: Optional[str]
    receipt_items: List[ReceiptItem] = field(default_factory=list)


@dataclass
class StageResult:
    name: str
    response: object


@dataclass
class PipelineResult:
    file_id: str
    stages: List[StageResult]


def _load_initial_context(file_id: str) -> PipelineContext:
    row = fetch_pipeline_context(file_id)
    if not row:
        raise PipelineExecutionError(f"File {file_id} not found for AI pipeline")

    (
        ocr_raw,
        document_type,
        expense_type,
        purchase_datetime,
        gross_amount_sek,
        net_amount_sek,
        company_id,
    ) = row

    ocr_text = (ocr_raw or "").strip()
    vendor_name = fetch_company_name(company_id)

    return PipelineContext(
        file_id=file_id,
        ocr_text=ocr_text,
        document_type=document_type,
        expense_type=expense_type,
        purchase_datetime=purchase_datetime,
        gross_amount=gross_amount_sek,
        net_amount=net_amount_sek,
        vendor_name=vendor_name,
    )


def _ensure(value: Optional[str], message: str) -> str:
    if not value:
        raise PipelineExecutionError(message)
    return value


def _ensure_decimal(value: Optional[Decimal], message: str) -> Decimal:
    if value is None:
        raise PipelineExecutionError(message)
    return value


def _prepare_steps(steps: Optional[Sequence[str]]) -> List[str]:
    ordered = ["AI1", "AI2", "AI3", "AI4", "AI5"]
    if steps is None:
        return ordered
    requested = [step.upper() for step in steps]
    return [step for step in ordered if step in requested]


def run_ai_pipeline(
    file_id: str,
    *,
    steps: Optional[Sequence[str]] = None,
    service: Optional[AIService] = None,
) -> PipelineResult:
    """Execute AI1–AI5 in order and persist each stage."""

    ai_service = service or AIService()
    context = _load_initial_context(file_id)
    stage_results: List[StageResult] = []

    for step in _prepare_steps(steps):
        if step == "AI1":
            request = DocumentClassificationRequest(
                file_id=file_id,
                ocr_text=context.ocr_text,
            )
            response = ai_service.classify_document(request)
            persist_document_classification(file_id, response)
            context.document_type = response.document_type
            stage_results.append(StageResult(name=step, response=response))
        elif step == "AI2":
            document_type = _ensure(
                context.document_type,
                "AI2 requires document type from AI1 or existing data",
            )
            request = ExpenseClassificationRequest(
                file_id=file_id,
                ocr_text=context.ocr_text,
                document_type=document_type,
            )
            response = ai_service.classify_expense(request)
            persist_expense_classification(file_id, response)
            context.expense_type = response.expense_type
            stage_results.append(StageResult(name=step, response=response))
        elif step == "AI3":
            document_type = _ensure(
                context.document_type,
                "AI3 requires document type",
            )
            expense_type = _ensure(
                context.expense_type,
                "AI3 requires expense type from AI2 or existing data",
            )
            request = DataExtractionRequest(
                file_id=file_id,
                ocr_text=context.ocr_text,
                document_type=document_type,
                expense_type=expense_type,
            )
            response = ai_service.extract_data(request)
            persist_extraction_result(file_id, response)

            context.purchase_datetime = response.unified_file.purchase_datetime
            context.gross_amount = (
                response.unified_file.gross_amount_sek
                or response.unified_file.gross_amount_original
            )
            context.net_amount = (
                response.unified_file.net_amount_sek
                or response.unified_file.net_amount_original
            )
            context.vendor_name = response.company.name
            context.receipt_items = list(response.receipt_items)
            stage_results.append(StageResult(name=step, response=response))
        elif step == "AI4":
            document_type = _ensure(
                context.document_type,
                "AI4 requires document type",
            )
            expense_type = _ensure(
                context.expense_type,
                "AI4 requires expense type",
            )
            gross_amount = _ensure_decimal(
                context.gross_amount,
                "AI4 requires gross amount from AI3",
            )
            net_amount = _ensure_decimal(
                context.net_amount,
                "AI4 requires net amount from AI3",
            )
            vat_amount = gross_amount - net_amount
            receipt_items = context.receipt_items
            if not receipt_items:
                raise PipelineExecutionError("AI4 requires receipt line items from AI3")
            request = AccountingClassificationRequest(
                file_id=file_id,
                document_type=document_type,
                expense_type=expense_type,
                gross_amount=gross_amount,
                net_amount=net_amount,
                vat_amount=vat_amount,
                vendor_name=context.vendor_name or "",
                receipt_items=receipt_items,
            )
            chart = fetch_chart_of_accounts()
            response = ai_service.classify_accounting(request, chart)
            persist_accounting_proposals(response)
            stage_results.append(StageResult(name=step, response=response))
        elif step == "AI5":
            purchase_date = context.purchase_datetime
            if not purchase_date:
                raise PipelineExecutionError("AI5 requires purchase date from AI3")
            amount = _ensure_decimal(
                context.gross_amount,
                "AI5 requires gross amount for matching",
            )
            candidates = fetch_credit_card_candidates(purchase_date, amount)
            request = CreditCardMatchRequest(
                file_id=file_id,
                purchase_date=purchase_date,
                amount=amount,
                vendor_name=context.vendor_name,
            )
            response = ai_service.match_credit_card(request, candidates)
            if response.matched and response.credit_card_invoice_item_id:
                persist_credit_card_match(
                    file_id,
                    response.credit_card_invoice_item_id,
                    amount,
                )
            stage_results.append(StageResult(name=step, response=response))
        else:
            raise PipelineExecutionError(f"Unknown AI pipeline step: {step}")

    return PipelineResult(file_id=file_id, stages=stage_results)


__all__ = [
    "PipelineExecutionError",
    "PipelineResult",
    "StageResult",
    "run_ai_pipeline",
]

