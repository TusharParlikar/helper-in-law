"""G3: the quote must exist in the cited chunk. Exact (normalised) first, then fuzzy for
whitespace/OCR noise only."""

from difflib import SequenceMatcher

from helperinlaw.ground.text import normalise, paragraphs_of

MIN_QUOTE_WORDS = 5  # "the court held" matches everything; a quote must pin something down


def find_quote(quote: str, chunk_text: str, fuzzy_ratio: float = 0.97) -> int | None:
    """Returns the paragraph number containing the quote, or None if it isn't there."""
    q = normalise(quote).strip(" .\"'")
    if len(q.split()) < MIN_QUOTE_WORDS:
        return None
    qw = q.split()
    for n, para in paragraphs_of(chunk_text):
        p = normalise(para)
        if q in p:
            return n
        if fuzzy_match(qw, p.split(), fuzzy_ratio):
            return n
    return None


def fuzzy_match(qw: list[str], pw: list[str], ratio: float) -> bool:
    """OCR noise changes letters, not whole words: compare equal-length word windows, and every
    word must have a close counterpart. Dropping or adding a word ("not") never matches."""
    for i in range(len(pw) - len(qw) + 1):
        win = pw[i : i + len(qw)]
        if SequenceMatcher(None, " ".join(qw), " ".join(win), autojunk=False).ratio() < ratio:
            continue
        if all(
            a == b or SequenceMatcher(None, a, b).ratio() >= 0.75
            for a, b in zip(qw, win, strict=True)
        ):
            return True
    return False
