from pathlib import Path

import pytest

from services.pdf_conversion import pdf_to_png_pages


@pytest.mark.parametrize(
    "pdf_name,expected_pages",
    [
        ("FC_2501.pdf", 2),
        ("FC_2502.pdf", 3),
    ],
)
def test_pdf_to_png_pages_generates_images_for_firstcard_statements(
    tmp_path, pdf_name: str, expected_pages: int
) -> None:
    pdf_path = Path("fc") / pdf_name
    if not pdf_path.exists():
        pytest.skip(f"FirstCard sample {pdf_name} not available")

    pdf_bytes = pdf_path.read_bytes()

    output_dir = tmp_path / "rendered"
    pages = pdf_to_png_pages(pdf_bytes, output_dir, pdf_path.stem)

    assert len(pages) == expected_pages
    assert all(page.path.exists() for page in pages)
    assert all(page.path.suffix.lower() == ".png" for page in pages)
    # Ensure byte payload is non-empty so downstream OCR can run
    assert all(page.bytes for page in pages)
