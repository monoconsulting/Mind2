"""Utilities for converting PDF documents to images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import logging

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PdfPage:
    """Represents a rendered PDF page.

    The ``index`` is zero-based to match the source document ordering.
    """

    index: int
    path: Path
    bytes: bytes


def pdf_to_png_pages(pdf_bytes: bytes, output_dir: Path, base_name: str, dpi: int = 300) -> List[PdfPage]:
    """Convert a PDF into PNG pages saved on disk.

    Returns metadata for each generated page.
    """
    try:
        import fitz  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing handled at runtime
        raise RuntimeError("PyMuPDF (fitz) is required for PDF conversion") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[PdfPage] = []

    try:
        for page_index in range(doc.page_count):
            page = doc.load_page(page_index)
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            filename = f"{base_name}_page_{page_index + 1:04d}.png"
            file_path = output_dir / filename
            page_bytes = pix.tobytes("png")
            file_path.write_bytes(page_bytes)
            pages.append(PdfPage(index=page_index, path=file_path, bytes=page_bytes))
    finally:
        doc.close()

    logger.info("Converted PDF into %s page(s) at %s", len(pages), output_dir)
    return pages
