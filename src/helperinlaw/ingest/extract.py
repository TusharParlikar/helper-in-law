"""Text extraction with a quality score, and OCR for pages without a text layer."""

import hashlib
import os
from pathlib import Path

from helperinlaw.core.logging import get_logger

log = get_logger(__name__)
MIN_PAGE_CHARS = 50  # a page with less text than this is treated as a scan
TESSDATA_DEFAULTS = (r"C:\Program Files\Tesseract-OCR\tessdata", "/usr/share/tesseract-ocr/5/tessdata",
                     "/usr/share/tesseract-ocr/4.00/tessdata", "/opt/homebrew/share/tessdata")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quality(text: str) -> float:
    """Share of non-space characters that are letters. Garbled OCR/encoding scores low."""
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 200:
        return 0.0
    return sum(c.isalpha() for c in chars) / len(chars)


def tessdata() -> str | None:
    """Tesseract's language data, from TESSDATA_PREFIX or a standard install; None = no OCR."""
    for d in (os.environ.get("TESSDATA_PREFIX", ""), *TESSDATA_DEFAULTS):
        if d and (Path(d) / "eng.traineddata").exists():
            return d
    return None


def page_text(page, ocr_data: str | None) -> str:  # type: ignore[no-untyped-def]
    text: str = page.get_text()
    if len(text.strip()) >= MIN_PAGE_CHARS or not ocr_data:
        return text
    # A scanned page: OCR it. Without Tesseract the page stays empty and the quality gate
    # sends the document to the dead-letter table.
    ocr: str = page.get_text(textpage=page.get_textpage_ocr(language="eng", dpi=300, full=True, tessdata=ocr_data))
    log.info("ocr page", extra={"extra_fields": {"page": page.number + 1, "chars": len(ocr)}})
    return ocr


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import fitz  # pymupdf, optional extra "pdf"

        ocr_data = tessdata()
        with fitz.open(path) as doc:
            return "\n".join(page_text(page, ocr_data) for page in doc)
    return path.read_text(encoding="utf-8", errors="replace")
