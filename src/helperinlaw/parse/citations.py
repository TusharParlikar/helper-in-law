"""Case-to-case citations with treatment tagging (followed / distinguished / overruled).

🔍 Treatment is keyword-based on the citing paragraph; check it against the gold set.
"""

import re

from helperinlaw.parse.metadata import REPORTER

TREATMENTS = [
    ("overruled", re.compile(r"\boverrul(ed|ing)\b", re.I)),
    ("distinguished", re.compile(r"\bdistinguish(ed|able|ing)\b", re.I)),
    ("followed", re.compile(r"\b(followed|relied (up)?on|affirmed|approved)\b", re.I)),
]


def treatment_of(para: str) -> str:
    for name, rx in TREATMENTS:
        if rx.search(para):
            return name
    return "unknown"


def extract_citations(paras: list[tuple[int, str]]) -> list[tuple[str, str, int]]:
    """Returns [(citation string, treatment, para n)]. The strongest treatment seen for a
    citation wins (overruled > distinguished > followed > unknown)."""
    rank = {"overruled": 3, "distinguished": 2, "followed": 1, "unknown": 0}
    best: dict[str, tuple[str, int]] = {}
    for n, text in paras:
        for m in REPORTER.finditer(text):
            cit = " ".join(m.group(0).split())
            t = treatment_of(text)
            if cit not in best or rank[t] > rank[best[cit][0]]:
                best[cit] = (t, n)
    return [(c, t, n) for c, (t, n) in best.items()]
