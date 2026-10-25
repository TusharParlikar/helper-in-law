"""G5: numbers, sections, dates and amounts in a claim must appear in the cited text."""

import re

from helperinlaw.ground.text import NUMBER_WORDS

ENTITY = re.compile(r"\b\d[\d,]*(?:\.\d+)?[A-Za-z]?(?:\(\d+\))?")


def entities(text: str) -> set[str]:
    found = {m.group(0).replace(",", "").lower() for m in ENTITY.finditer(text)}
    words = re.findall(r"[a-z]+", text.lower())
    found |= {NUMBER_WORDS[w] for w in words if w in NUMBER_WORDS}
    # "65B(4)" also counts as "65b" so a claim citing the section matches a quote with the sub-section
    found |= {re.sub(r"\(\d+\)$", "", e) for e in found}
    return found


def entities_supported(claim: str, quotes: list[str]) -> set[str]:
    """Returns the claim entities missing from every quote (empty set = pass)."""
    have: set[str] = set()
    for q in quotes:
        have |= entities(q)
    return entities(claim) - have
