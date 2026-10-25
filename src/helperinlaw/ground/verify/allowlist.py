"""G6: allowlist sanitiser. Case names and citations may only appear if they belong to the
retrieved set. Anything else is stripped with its sentence."""

import re

from helperinlaw.ground.text import sentences

CASE_NAME = re.compile(
    r"\b[A-Z][\w.&'-]*(?:\s+(?:of|the|and|&)?\s*[A-Z][\w.&'-]*)*\s+v(?:s)?\.?\s+"
    r"[A-Z][\w.&'-]*(?:\s+(?:of|the|and|&)?\s*[A-Z][\w.&'-]*)*"
)
REPORTER = re.compile(r"\(\d{4}\)\s+\d+\s+[A-Z]{2,6}\s+\d+")
NEUTRAL = re.compile(r"\b\d{4}\s+[A-Z]{2,6}\s+\d+\b")
AIR = re.compile(r"\bAIR\s+\d{4}\s+[A-Z]{2,5}\s+\d+")


def suspicious(sentence: str, allowed: set[str]) -> list[str]:
    """Case-name or citation strings in `sentence` that aren't in `allowed` (lowercased)."""
    bad = []
    for rx in (CASE_NAME, REPORTER, NEUTRAL, AIR):
        for m in rx.finditer(sentence):
            s = " ".join(m.group(0).split()).lower()
            if not any(s in a or a in s for a in allowed):
                bad.append(m.group(0))
    return bad


def sanitise(text: str, allowed: set[str]) -> tuple[str, list[str]]:
    kept, stripped = [], []
    for s in sentences(text):
        (stripped if suspicious(s, allowed) else kept).append(s)
    return " ".join(kept), stripped
