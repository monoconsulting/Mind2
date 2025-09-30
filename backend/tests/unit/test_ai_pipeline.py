from datetime import datetime
from decimal import Decimal

import pytest

from services import ai_pipeline
from services.ai_pipeline import PipelineExecutionError
from services.ai_service import AIService
from models.ai_processing import (
    AccountingClassificationResponse,
    AccountingProposal,
    Company,
    CreditCardMatchResponse,
    DataExtractionResponse,
    DocumentClassificationResponse,
    ExpenseClassificationResponse,
    ReceiptItem,
    UnifiedFileBase,
)


class StubAIService(AIService):
    """Stubbed AIService with deterministic responses."""

    def __init__(self) -> None:  # pragma: no cover - we bypass parent init
        pass

    def classify_document(self, request):  # type: ignore[override]
        return DocumentClassificationResponse(
            file_id=request.file_id,
            document_type="receipt",
            confidence=0.81,
            reasoning="stubbed",
        )

    def classify_expense(self, request):  # type: ignore[override]
        return ExpenseClassificationResponse(
            file_id=request.file_id,
            expense_type="corporate",
            confidence=0.79,
            card_identifier="stub",
            reasoning="stubbed",
        )

    def extract_data(self, request):  # type: ignore[override]
        unified = UnifiedFileBase(
            id=request.file_id,
            file_type="receipt",
            orgnr="556677-8899",
            payment_type="card",
            purchase_datetime=datetime(2024, 1, 2, 12, 0, 0),
            expense_type="corporate",
            gross_amount_original=Decimal("100.00"),
            net_amount_original=Decimal("80.00"),
            gross_amount_sek=Decimal("100.00"),
            net_amount_sek=Decimal("80.00"),
            other_data="{}",
            ocr_raw=request.ocr_text,
        )
        item = ReceiptItem(
            main_id=request.file_id,
            article_id="001",
            name="Coffee",
            number=1,
            item_price_ex_vat=Decimal("80.00"),
            item_price_inc_vat=Decimal("100.00"),
            item_total_price_ex_vat=Decimal("80.00"),
            item_total_price_inc_vat=Decimal("100.00"),
            currency="SEK",
            vat=Decimal("20.00"),
            vat_percentage=Decimal("0.25"),
        )
        company = Company(name="Acme AB", orgnr="556677-8899")
        return DataExtractionResponse(
            file_id=request.file_id,
            unified_file=unified,
            receipt_items=[item],
            company=company,
            confidence=0.92,
        )

    def classify_accounting(self, request, chart):  # type: ignore[override]
        proposal = AccountingProposal(
            receipt_id=request.file_id,
            account_code="3000",
            debit=Decimal("0.00"),
            credit=Decimal("100.00"),
            vat_rate=Decimal("25.0"),
            notes="stub",
        )
        return AccountingClassificationResponse(
            file_id=request.file_id,
            proposals=[proposal],
            confidence=0.77,
            based_on_bas2025=True,
        )

    def match_credit_card(self, request, candidates):  # type: ignore[override]
        return CreditCardMatchResponse(
            file_id=request.file_id,
            matched=True,
            credit_card_invoice_item_id=42,
            confidence=0.74,
            match_details={"candidates": candidates},
        )


def test_run_ai_pipeline_persists_each_stage(monkeypatch):
    records = []

    monkeypatch.setattr(ai_pipeline, "fetch_pipeline_context", lambda fid: ("ocr text", None, None, None, None, None, None))
    monkeypatch.setattr(ai_pipeline, "fetch_company_name", lambda cid: None)
    monkeypatch.setattr(ai_pipeline, "persist_document_classification", lambda fid, res: records.append(("AI1", fid, res.document_type)))
    monkeypatch.setattr(ai_pipeline, "persist_expense_classification", lambda fid, res: records.append(("AI2", fid, res.expense_type)))
    monkeypatch.setattr(ai_pipeline, "persist_extraction_result", lambda fid, res: records.append(("AI3", fid, res.unified_file.purchase_datetime)))
    monkeypatch.setattr(ai_pipeline, "fetch_chart_of_accounts", lambda: [("3000", "Sales")])
    monkeypatch.setattr(ai_pipeline, "persist_accounting_proposals", lambda res: records.append(("AI4", res.file_id, len(res.proposals))))
    monkeypatch.setattr(ai_pipeline, "fetch_credit_card_candidates", lambda date, amount: [(1, "Acme", amount)])
    credit_matches = []
    monkeypatch.setattr(ai_pipeline, "persist_credit_card_match", lambda fid, invoice_id, amount: credit_matches.append((fid, invoice_id, amount)))

    service = StubAIService()
    result = ai_pipeline.run_ai_pipeline("file-123", service=service)

    assert [stage.name for stage in result.stages] == ["AI1", "AI2", "AI3", "AI4", "AI5"]
    assert records[0][0] == "AI1"
    assert records[1][0] == "AI2"
    assert records[2][0] == "AI3"
    assert records[3][0] == "AI4"
    assert credit_matches == [("file-123", 42, Decimal("100.00"))]


def test_run_ai_pipeline_requires_document_type(monkeypatch):
    monkeypatch.setattr(ai_pipeline, "fetch_pipeline_context", lambda fid: ("", None, None, None, None, None, None))
    monkeypatch.setattr(ai_pipeline, "fetch_company_name", lambda cid: None)

    service = StubAIService()

    with pytest.raises(PipelineExecutionError):
        ai_pipeline.run_ai_pipeline("file-err", steps=["AI2"], service=service)
