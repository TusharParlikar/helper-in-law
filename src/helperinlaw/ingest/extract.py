"""Text extraction with a quality score."""

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quality(text: str) -> float:
    """Share of non-space characters that are letters. Garbled OCR/encoding scores low."""
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 200:
        return 0.0
    return sum(c.isalpha() for c in chars) / len(chars)


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        # ponytail: no OCR fallback; low-quality scans go to the dead-letter queue.
        # Add pytesseract here when scanned judgments enter the corpus.
        import fitz  # pymupdf, optional extra "pdf"

        with fitz.open(path) as doc:
            return "\n".join(page.get_text() for page in doc)
    return path.read_text(encoding="utf-8", errors="replace")
