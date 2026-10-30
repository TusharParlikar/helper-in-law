"""Query understanding: filters, statutes and case names pulled out of a plain question."""

import re
from collections import Counter

from pydantic import BaseModel

from helperinlaw.core.types import Filters
from helperinlaw.parse.statutes import ACT_NAMES, extract_statutes, normalise_act

STOP = set(
    """a an and are as at be by can could did do does for from had has have how i if in
into is it its may me must my of on or our shall should so than that the their them then there
these this those to under upon was were what when where whether which who whom why will with
would you your about any all also been being court courts case cases law held hold says said
under section sections act
client clients my mine he she him her his hers they them their someone person mr mrs ms
day days night nights week weeks month months year years one two three four got get gets
want wants wanted asked ask also just even still like
sir madam dear hello hi kindly please urgent urgently query queries advise advice regards thanks
thank help guidance opinion""".split()  # conversational: rare in judgments, so they'd outrank facts
)

SHORT_SECTION = re.compile(
    r"\b(?:s\.?|sec\.?|section)?\s*(?P<s>\d+[A-Z]?)\s+(?P<act>"
    + "|".join(re.escape(n) for names in ACT_NAMES.values() for n in names)
    + r")\b",
    re.I,
)
CASE_NAME = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+v(?:s)?\.?\s+([A-Z][\w.]*(?:\s+(?:of\s+)?[A-Z][\w.]*)*)"
)


class Query(BaseModel):
    text: str
    filters: Filters
    statutes: list[tuple[str, str]] = []
    case_names: list[str] = []


LETTERS = "abcdefghijklmnopqrstuvwxyz"


def _edits(w: str) -> set[str]:
    """Words one typo away: a letter deleted, swapped with the next, replaced or inserted."""
    splits = [(w[:i], w[i:]) for i in range(len(w) + 1)]
    return {a + b[1:] for a, b in splits if b} | {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1} | {
        a + c + b[1:] for a, b in splits if b for c in LETTERS
    } | {a + c + b for a, b in splits for c in LETTERS}


def correct_spelling(text: str, counts: Counter[str]) -> str:
    """Replaces a lower-case word the corpus never uses with its most frequent one-typo
    neighbour ("arersted" -> "arrested"). Capitalised words (names) and short words are kept."""

    def fix(m: re.Match[str]) -> str:
        w = m.group(0)
        if len(w) < 5 or not w.islower() or w in counts:
            return w
        known = [e for e in _edits(w) if counts[e] >= 3]
        return max(known, key=lambda e: (counts[e], e)) if known else w

    return re.sub(r"[A-Za-z]+", fix, text)


def terms(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 1]


def understand(question: str, explicit: Filters | None = None) -> Query:
    f = explicit.model_copy() if explicit else Filters()
    q = question
    if f.court is None:
        if re.search(r"\b(supreme court|SC only|\bSC\b)", q, re.I):
            f.court = "SC"
        elif m := re.search(r"\b([A-Z][a-z]+)\s+(?:High Court|HC)\b", q):
            f.court = f"{m.group(1)} HC"
    if f.year_from is None and (m := re.search(r"\b(?:after|since|from)\s+(\d{4})\b", q, re.I)):
        f.year_from = int(m.group(1))
    if f.year_to is None and (m := re.search(r"\b(?:before|until|till)\s+(\d{4})\b", q, re.I)):
        f.year_to = int(m.group(1))
    if m := re.search(r"\bbetween\s+(\d{4})\s+and\s+(\d{4})\b", q, re.I):
        f.year_from, f.year_to = int(m.group(1)), int(m.group(2))
    statutes = set(extract_statutes(q))
    for m in SHORT_SECTION.finditer(q):
        if act := normalise_act(m.group("act")):
            statutes.add((act, m.group("s").upper()))
    names = [f"{a} v. {b}" for a, b in CASE_NAME.findall(q)]
    return Query(text=q, filters=f, statutes=sorted(statutes), case_names=names)
