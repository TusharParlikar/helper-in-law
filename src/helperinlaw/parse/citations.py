"""Case-to-case citations with treatment tagging (followed / distinguished / overruled).

Recognised forms, each normalised to how the corpus stores it so it can be resolved:
  "(2015) 3 FSR 101"       generic "(year) volume REPORTER page"
  "[2018] 13 S.C.R. 1286"  Supreme Court Reports  -> "[2018] 13 S.C.R. 1286"
  "2018 INSC 1201"         neutral citation        -> "2018 INSC 1201"

🔍 Treatment is keyword-based on the citing paragraph; check it against the gold set.
"""

import re

from helperinlaw.parse.metadata import REPORTER

SCR = re.compile(r"\[(\d{4})\]\s*(\d{1,2})\s*S\.?\s*C\.?\s*R\.?\s*(\d{1,4})", re.I)
INSC = re.compile(r"\b(\d{4})\s*INSC\s*(\d{1,5})\b")
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


def references(text: str) -> list[str]:
    refs = [" ".join(m.group(0).split()) for m in REPORTER.finditer(text)]
    refs += [f"[{y}] {int(v)} S.C.R. {int(p)}" for y, v, p in SCR.findall(text)]
    refs += [f"{y} INSC {int(n)}" for y, n in INSC.findall(text)]
    return refs


def extract_citations(paras: list[tuple[int, str]]) -> list[tuple[str, str, int]]:
    """Returns [(citation string, treatment, para n)]. The strongest treatment seen for a
    citation wins (overruled > distinguished > followed > unknown)."""
    rank = {"overruled": 3, "distinguished": 2, "followed": 1, "unknown": 0}
    best: dict[str, tuple[str, int]] = {}
    for n, text in paras:
        t = treatment_of(text)
        for cit in references(text):
            if cit not in best or rank[t] > rank[best[cit][0]]:
                best[cit] = (t, n)
    return [(c, t, n) for c, (t, n) in best.items()]
