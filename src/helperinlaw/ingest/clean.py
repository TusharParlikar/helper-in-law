"""Cleaner: page headers/footers, page numbers, hyphenation, banners."""

import re
from collections import Counter

PAGE_NO = re.compile(r"^\s*(page\s+\d+(\s+of\s+\d+)?|-?\s*\d+\s*-?)\s*$", re.I)
BANNER = re.compile(
    r"^\s*(digitally signed|signature not verified|reportable|non-reportable)\b", re.I
)


def clean(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    # Lines repeated on many pages are running headers/footers. Paragraphs never repeat verbatim.
    counts = Counter(line.strip() for line in lines if line.strip())
    repeated = {line for line, n in counts.items() if n >= 3 and len(line) < 120}
    kept = [
        line
        for line in lines
        if not PAGE_NO.match(line) and not BANNER.match(line) and line.strip() not in repeated
    ]
    out = "\n".join(kept)
    out = re.sub(r"(\w)-\n(\w)", r"\1\2", out)  # de-hyphenate words broken across lines
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
