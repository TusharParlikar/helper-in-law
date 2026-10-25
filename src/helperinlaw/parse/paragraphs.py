"""Split a cleaned judgment into its header and numbered paragraphs."""

import re

PARA_START = re.compile(r"^\s*(\d{1,4})\.\s+(?=\S)", re.M)


def split_paragraphs(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Returns (header, [(n, text)]). Only accepts numbers that increase, so a stray
    "2." inside a paragraph (a list, a date) doesn't start a new one."""
    starts: list[tuple[int, int, int]] = []  # (n, match start, body start)
    for m in PARA_START.finditer(text):
        n = int(m.group(1))
        if not starts and n != 1:
            continue
        if starts and n != starts[-1][0] + 1:
            continue
        starts.append((n, m.start(), m.end()))
    if not starts:
        return text, []
    header = text[: starts[0][1]].strip()
    paras = []
    for i, (n, _, body) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        paras.append((n, " ".join(text[body:end].split())))
    return header, paras
