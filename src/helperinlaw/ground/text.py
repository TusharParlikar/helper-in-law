"""Text helpers shared by the extractor and the verifiers."""

import re

PARA_MARK = re.compile(r"\[(\d+)\]\s*")
ABBREV = re.compile(r"\b(v|vs|Rs|No|Nos|J|JJ|Dr|Mr|Mrs|Ms|S|Sec|Cr|P|C|i\.e|e\.g|viz|Art|Ltd)\.$")
NEG = re.compile(r"\b(not|no|never|cannot|nor|neither|without)\b|n't\b", re.I)
WORD = re.compile(r"[a-z0-9]+")
MODALS = {"may", "must", "shall", "should", "can", "could", "would", "will"}
NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12", "fourteen": "14",
    "fifteen": "15", "twenty": "20", "thirty": "30",
}


def normalise(text: str) -> str:
    text = PARA_MARK.sub("", text)
    text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-"}))
    return " ".join(text.lower().split())


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.;?!])\s+(?=[A-Z\"(])", " ".join(text.split()))
    out: list[str] = []
    for p in parts:
        if out and ABBREV.search(out[-1]):
            out[-1] += " " + p  # "v. State", "Rs. 1,00,000" are not sentence ends
        else:
            out.append(p)
    return out


def paragraphs_of(chunk_text: str) -> list[tuple[int, str]]:
    """Split a chunk back into its [n]-marked paragraphs."""
    marks = list(PARA_MARK.finditer(chunk_text))
    return [
        (int(m.group(1)), chunk_text[m.end(): marks[i + 1].start() if i + 1 < len(marks) else None].strip())
        for i, m in enumerate(marks)
    ]


def negated(text: str) -> bool:
    return bool(NEG.search(text))


def content_terms(text: str) -> set[str]:
    from helperinlaw.retrieve.understand import STOP

    stop = STOP - MODALS  # "may" vs "must" changes the law; keep modals as content
    toks = (NUMBER_WORDS.get(t, t) for t in WORD.findall(text.lower()))
    return {t[:5] for t in toks if t not in stop and len(t) > 1}
