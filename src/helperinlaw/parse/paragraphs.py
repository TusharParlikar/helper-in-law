"""Split a cleaned judgment into its header and numbered paragraphs."""

import re

# Scanned reports can put a stray bullet or a margin letter before the number: "· 15." / "E 15."
PARA_START = re.compile(r"^\s*(?:[·•*]\s*|[A-Z]\s+)?(\d{1,4})\.\s+(?=\S)", re.M)
# Text extraction sometimes joins a paragraph onto the previous line: '...in mind." . 16. Considering'
MID_START = re.compile(r"(?<=[.:\"”'])[ \t.·]+(\d{1,4})\.\s+(?=[A-Z])")
# ...but not a reference that ends a sentence: "the scheme of Art. 15. Provisos to..."
REFERENCE = re.compile(r"\b(?:Arts?|Articles?|Secs?|Sections?|S|s|Nos?|Cl|cl|[Pp]aras?|Rules?|Order|Vol|pp?)\.?\s*$")


def split_paragraphs(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Returns (header, [(n, text)]). Only accepts numbers that increase by one, so a stray
    "2." inside a paragraph (a list, a date) doesn't start a new one."""
    found = sorted(
        [(m.start(), m.end(), int(m.group(1)), True) for m in PARA_START.finditer(text)]
        + [
            (m.start(), m.end(), int(m.group(1)), False)
            for m in MID_START.finditer(text)
            if not REFERENCE.search(text[max(0, m.start() - 12) : m.start()])
        ]
    )
    starts: list[tuple[int, int, int]] = []  # (n, match start, body start)
    for start, end, n, line_start in found:
        if starts and start < starts[-1][2]:
            continue  # overlaps the previous accepted start
        if not starts and (n != 1 or not line_start):
            continue
        if starts and n != starts[-1][0] + 1:
            continue
        starts.append((n, start, end))
    if not starts:
        return text, []
    header = text[: starts[0][1]].strip()
    paras = []
    for i, (n, _, body) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        paras.append((n, " ".join(text[body:end].split())))
    return header, paras
