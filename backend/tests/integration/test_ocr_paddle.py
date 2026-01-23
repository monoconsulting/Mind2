import os

import pytest


def _integration_enabled() -> bool:
    return os.getenv("RUN_OCR_INTEGRATION") == "1"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        pytest.skip(f"{name} not set")
    return value


@pytest.mark.skipif(not _integration_enabled(), reason="RUN_OCR_INTEGRATION=1 required")
def test_paddleocr_sv_init() -> None:
    pytest.importorskip("paddleocr")
    from paddleocr import PaddleOCR

    PaddleOCR(lang="sv")


@pytest.mark.skipif(not _integration_enabled(), reason="RUN_OCR_INTEGRATION=1 required")
def test_paddleocr_en_init() -> None:
    pytest.importorskip("paddleocr")
    from paddleocr import PaddleOCR

    PaddleOCR(lang="en")


@pytest.mark.skipif(not _integration_enabled(), reason="RUN_OCR_INTEGRATION=1 required")
def test_page_ocr_fallback_to_en() -> None:
    pytest.importorskip("paddleocr")
    from services.ocr import OCR_MIN_NONWHITESPACE_CHARS, run_ocr

    page_id = _require_env("OCR_TEST_EN_PAGE_ID")
    storage_dir = os.getenv("STORAGE_DIR", "/data/storage")
    result = run_ocr(page_id, storage_dir)
    assert result.get("fallback_triggered") is True, (
        "Expected sv OCR to be too short and trigger en fallback. "
        "Provide an English-heavy OCR_TEST_EN_PAGE_ID."
    )
    assert result.get("lang_used") == "en"
    assert (result.get("char_count") or 0) >= OCR_MIN_NONWHITESPACE_CHARS


def test_merge_ocr_succeeds_with_partial_pages() -> None:
    pytest.importorskip("celery")
    from services.tasks.ocr_tasks import _merge_ocr_page_results

    results = [
        (1, "page-1", "Total 123.45\nThank you"),
        (1, "page-2", ""),
    ]
    stats = _merge_ocr_page_results(results)
    assert stats["pages_with_text"] == 1
    assert stats["failed_pages"] == ["page-2"]
    assert stats["combined_text"]

