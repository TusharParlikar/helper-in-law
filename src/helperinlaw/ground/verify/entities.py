"""G5: numbers, sections, dates and amounts in a claim must appear in the cited text."""

import re

from helperinlaw.ground.text import NUMBER_WORDS

TOKEN = re.compile(r"\b[a-z]{1,4}\d{3,}\b|\b\d[\d,]*(?:\.\d+)?[a-z]?(?:\(\d+\))?|[a-z]+")
TENS = {"twenty": 20, "thirty": 30}
COMPOUND = re.compile(r"\b(twenty|thirty)[- ](one|two|three|four|five|six|seven|eight|nine)\b")


IDENTIFIER = re.compile(r"\b[A-Z]{1,4}\d{3,}\b")  # docket / file numbers: "S247278", "WP1234"


def numbers(text: str) -> list[str]:
    """Numbers in order of appearance; number words count ("ten" -> "10", "twenty-four" -> "24"),
    and so do identifiers like "S247278". A footnote marker glued to a word ("Singh2",
    "Committee20") is not a number of the text."""
    ids = {m.group(0).lower() for m in IDENTIFIER.finditer(text)}
    low = COMPOUND.sub(lambda m: str(TENS[m.group(1)] + int(NUMBER_WORDS[m.group(2)])), text.lower())
    out = []
    for m in TOKEN.finditer(low):
        t = m.group(0)
        if t in ids:
            out.append(t)
        elif t[0].isdigit():
            out.append(t.replace(",", ""))
        elif t in NUMBER_WORDS:
            out.append(NUMBER_WORDS[t])
    return out


def _bare(e: str) -> str:
    return re.sub(r"\(\d+\)$", "", e)  # "65b(4)" -> "65b"


def entities(text: str) -> set[str]:
    found = set(numbers(text))
    # "65B(4)" also counts as "65b" so a claim citing the section matches a quote with the sub-section
    return found | {_bare(e) for e in found}


def entities_supported(claim: str, quotes: list[str]) -> set[str]:
    """Returns the claim's numbers not found in the quotes, in the same order (empty set = pass).
    Order matters: "(4) ... twenty-four hours" against "(2) ... twenty-four hours" fails, and so
    does "27 March" against a quote that says "25 March" and mentions 27 elsewhere."""
    pool = [n for q in quotes for n in numbers(q)]
    missing: set[str] = set()
    j = 0
    for c in numbers(claim):
        k = next((i for i in range(j, len(pool)) if c in (pool[i], _bare(pool[i]))), None)
        if k is None:
            missing.add(c)
        else:
            j = k + 1
    return missing
