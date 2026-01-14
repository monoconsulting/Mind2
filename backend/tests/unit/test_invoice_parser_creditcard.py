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


def test_parse_credit_card_statement_handles_spaced_amounts() -> None:
    """Test handling of amounts with thousands separators (spaces)."""
    sample_text = textwrap.dedent(
        """
        2025-03-05 Bauhaus 2 579,80
        2025-03-05 Amazon 150,00
        """
    ).strip()

    result = parse_credit_card_statement(sample_text)
    assert len(result["lines"]) == 2
    
    line1 = result["lines"][0]
    assert line1["merchant_name"] == "Bauhaus"
    assert line1["amount"] == pytest.approx(2579.80)
    
    line2 = result["lines"][1]
    assert line2["merchant_name"] == "Amazon"
    assert line2["amount"] == pytest.approx(150.00)


def test_parse_credit_card_statement_handles_merged_lines() -> None:
    """Test splitting of multiple transactions merged onto a single line."""
    # This simulates the OCR error where two transactions appear on one line
    sample_text = "2025-03-05 Amazon 150,00 2025-03-05 Bauhaus 2 579,80"

    result = parse_credit_card_statement(sample_text)
    
    # Needs to find 2 distinct lines, not 1 merged one
    assert len(result["lines"]) == 2
    
    # Using sorted to ensure order doesn't fail test if implementation specifics vary,
    # though valid order preservation is preferred.
    # The new logic splits by inserting \n, so order should be preserved.
    
    # First transaction (Amazon)
    line1 = result["lines"][0]
    assert line1["transaction_date"] == "2025-03-05"
    assert line1["merchant_name"] == "Amazon"
    assert line1["amount"] == pytest.approx(150.00)
    
    # Second transaction (Bauhaus)
    line2 = result["lines"][1]
    assert line2["transaction_date"] == "2025-03-05"
    # Note: Regex consumption might leave leading spaces in description if not careful,
    # but .strip() in logic handles it.
    assert line2["merchant_name"] == "Bauhaus" 
    assert line2["amount"] == pytest.approx(2579.80)
