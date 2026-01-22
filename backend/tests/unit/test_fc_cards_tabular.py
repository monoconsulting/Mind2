from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.fc_cards_tabular import (
    AMBIGUOUS_AMOUNT_ALIGNMENT,
    reconstruct_fc_cards_table_from_boxes,
)


def _load_fixture_boxes() -> list[dict[str, object]]:
    """Load OCR box fixture data for FC_2504 page 1.

    Returns:
        List of OCR box dictionaries.
    """
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "fc_cards"
        / "FC_2504_page1_ocr_boxes_subset.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_fc_cards_row_amount_alignment() -> None:
    """Ensure FC row amounts stay aligned for Amazon and BAUHAUS rows."""
    boxes = _load_fixture_boxes()
    page = reconstruct_fc_cards_table_from_boxes(
        page_file_id="page-1",
        page_index=0,
        boxes=boxes,
    )

    amazon_row = next(
        (row for row in page.rows if "amazon" in (row.merchant_raw or "").lower()),
        None,
    )
    bauhaus_row = next(
        (row for row in page.rows if "bauhaus" in (row.merchant_raw or "").lower()),
        None,
    )

    assert amazon_row is not None, "Amazon row not found in reconstruction"
    assert bauhaus_row is not None, "BAUHAUS row not found in reconstruction"

    assert amazon_row.amount_value == pytest.approx(875.40, abs=0.01)
    assert bauhaus_row.amount_value == pytest.approx(2579.80, abs=0.01)
    assert amazon_row.amount_value != bauhaus_row.amount_value
    assert amazon_row.amount_value != pytest.approx(2579.80, abs=0.01)
    assert bauhaus_row.amount_value != pytest.approx(875.40, abs=0.01)
    assert AMBIGUOUS_AMOUNT_ALIGNMENT not in amazon_row.warnings
    assert AMBIGUOUS_AMOUNT_ALIGNMENT not in bauhaus_row.warnings


def test_fc_cards_foreign_currency_miro_com() -> None:
    """Ensure MIRO COM row extracts foreign currency fields correctly.

    The MIRO COM row (purchase_date 2025-03-04) should have:
    - currency_original = "USD"
    - amount_original_value = 240.00
    - exchange_rate = 11.0297 (from Valutakurs line)
    - amount_value (SEK) = 2647.13
    """
    boxes = _load_fixture_boxes()
    page = reconstruct_fc_cards_table_from_boxes(
        page_file_id="page-1",
        page_index=0,
        boxes=boxes,
    )

    miro_row = next(
        (row for row in page.rows if "miro" in (row.merchant_raw or "").lower()),
        None,
    )

    assert miro_row is not None, "MIRO COM row not found in reconstruction"

    # Verify date matches 2025-03-04
    assert miro_row.date_iso == "2025-03-04", f"Expected date 2025-03-04, got {miro_row.date_iso}"

    # Verify foreign currency extraction
    assert miro_row.currency_original == "USD", (
        f"Expected currency_original 'USD', got {miro_row.currency_original!r}"
    )
    assert miro_row.amount_original_value == pytest.approx(240.00, abs=0.01), (
        f"Expected amount_original_value 240.00, got {miro_row.amount_original_value}"
    )

    # Verify exchange rate from Valutakurs (11,0297 → 11.0297)
    assert miro_row.exchange_rate is not None, "Exchange rate should be set from Valutakurs line"
    assert miro_row.exchange_rate == pytest.approx(11.0297, abs=0.01), (
        f"Expected exchange_rate ~11.0297, got {miro_row.exchange_rate}"
    )

    # Verify SEK amount (rightmost column)
    assert miro_row.amount_value == pytest.approx(2647.13, abs=0.01), (
        f"Expected amount_value (SEK) 2647.13, got {miro_row.amount_value}"
    )


def test_fc_cards_sek_rows_no_foreign_currency() -> None:
    """Ensure SEK-only rows have currency_original=SEK and exchange_rate=0."""
    boxes = _load_fixture_boxes()
    page = reconstruct_fc_cards_table_from_boxes(
        page_file_id="page-1",
        page_index=0,
        boxes=boxes,
    )

    amazon_row = next(
        (row for row in page.rows if "amazon" in (row.merchant_raw or "").lower()),
        None,
    )
    bauhaus_row = next(
        (row for row in page.rows if "bauhaus" in (row.merchant_raw or "").lower()),
        None,
    )

    # Amazon row should be SEK (no foreign currency in text)
    assert amazon_row is not None
    assert amazon_row.currency_original == "SEK", (
        f"Expected SEK for Amazon row, got {amazon_row.currency_original!r}"
    )
    assert amazon_row.exchange_rate == pytest.approx(0.0, abs=0.01)

    # BAUHAUS row should be SEK
    assert bauhaus_row is not None
    assert bauhaus_row.currency_original == "SEK", (
        f"Expected SEK for BAUHAUS row, got {bauhaus_row.currency_original!r}"
    )
    assert bauhaus_row.exchange_rate == pytest.approx(0.0, abs=0.01)
