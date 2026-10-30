"""Natural-language style overrides ("shorter", "as a table", "explain simply") -> style patch.

Requests to drop safeguards ("without citations", "skip verification") map to no setting and
are reported back as ignored (§5.4)."""

import re
from typing import Any

from helperinlaw.ground.verify.injection import without_instructions

RULES: list[tuple[re.Pattern[str], dict[str, Any]]] = [
    (
        re.compile(r"\b(shorter|brief(ly)?|quick(ly)?|tl;?dr|in short|concise)\b", re.I),
        {"depth": "quick"},
    ),
    (
        re.compile(r"\b(in detail|detailed|deep(er)?|full analysis|elaborate)\b", re.I),
        {"depth": "deep"},
    ),
    (re.compile(r"\b(as a |in a )?table\b", re.I), {"structure": "table"}),
    (re.compile(r"\bbullets?|bullet points\b", re.I), {"structure": "bullets"}),
    (re.compile(r"\bIRAC\b", re.I), {"structure": "irac"}),
    (re.compile(r"\b(memo|research memo)\b", re.I), {"structure": "memo"}),
    (re.compile(r"\b(paragraphs?|prose)\b", re.I), {"structure": "paragraphs"}),
    (
        re.compile(r"\b(explain (it )?simply|plain (english|language)|simple terms)\b", re.I),
        {"tone": "plain"},
    ),
    (re.compile(r"\b(like i'?m new|eli5|beginner)\b", re.I), {"tone": "new"}),
    (re.compile(r"\b(in hindi|hindi me(in)?)\b", re.I), {"answer_language": "hi"}),
    (re.compile(r"\b(newest|latest|recent) first\b", re.I), {"recency": "newest"}),
    (re.compile(r"\blandmark\b", re.I), {"recency": "landmark"}),
    (re.compile(r"\bonly SC\b|\bsupreme court only\b|\bSC only\b", re.I), {"jurisdiction": ["SC"]}),
]

SAFEGUARD = re.compile(
    r"\b(without|no|skip|drop|remove|hide|don'?t (show|include|need))\s+(the\s+)?"
    r"(citations?|sources?|verification|verify|disclaimer|quotes? check|caveats?)\b"
    r"|\bjust (give me )?the answer\b|\bdon'?t abstain\b",
    re.I,
)


def parse_overrides(text: str) -> tuple[dict[str, Any], list[str]]:
    """Returns (style patch, ignored safeguard requests)."""
    patch: dict[str, Any] = {}
    for rx, change in RULES:
        if rx.search(text):
            patch.update(change)
    ignored = [m.group(0) for m in SAFEGUARD.finditer(text)]
    return patch, ignored


def strip_overrides(question: str) -> str:
    """The style words aren't part of the legal question; keep retrieval clean."""
    q = without_instructions(question)  # whole sentences addressed to the system go first
    for rx, _ in RULES:
        q = rx.sub(" ", q)
    q = SAFEGUARD.sub(" ", q)
    return " ".join(q.split()).strip(" ,;")
