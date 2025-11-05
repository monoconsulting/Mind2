import textwrap

import pytest

from services.invoice_parser import parse_credit_card_statement


def test_parse_credit_card_statement_extracts_lines_and_period() -> None:
    sample_text = textwrap.dedent(
        """
        Period: 2025-08-01 to 2025-08-31
        2025-08-02 COOP CENTRAL BUTIK 123,45
        2025-08-15 SWEDISH TAXI AB 456,78
        """
    ).strip()

    result = parse_credit_card_statement(sample_text)

    assert result["period_start"] == "2025-08-01"
    assert result["period_end"] == "2025-08-31"
    assert len(result["lines"]) == 2

    first_line = result["lines"][0]
    assert first_line["transaction_date"] == "2025-08-02"
    assert first_line["merchant_name"] == "COOP CENTRAL BUTIK"
    assert first_line["description"] == "COOP CENTRAL BUTIK"
    assert first_line["amount"] == pytest.approx(123.45)
    assert first_line["confidence"] == pytest.approx(0.85)
    assert "COOP CENTRAL BUTIK" in first_line["raw_text"]


def test_parse_credit_card_statement_ignores_irrelevant_rows() -> None:
    sample_text = textwrap.dedent(
        """
        Period: 2025-08-01 to 2025-08-31
        Totalt belopp: 12345,67 kr
        Inga transaktioner rapporterade denna period
        """
    ).strip()

    result = parse_credit_card_statement(sample_text)

    assert result["period_start"] == "2025-08-01"
    assert result["period_end"] == "2025-08-31"
    assert result["lines"] == []


def test_parse_credit_card_statement_handles_empty_payload() -> None:
    assert parse_credit_card_statement("") == {
        "period_start": None,
        "period_end": None,
        "lines": [],
        "raw_text": "",
    }
