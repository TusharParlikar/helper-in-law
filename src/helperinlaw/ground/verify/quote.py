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
    for n, para in paragraphs_of(chunk_text):
        p = normalise(para)
        if q in p:
            return n
        m = SequenceMatcher(None, q, p, autojunk=False).find_longest_match(0, len(q), 0, len(p))
        start = max(0, m.b - m.a)
        window = p[start : start + len(q)]
        if SequenceMatcher(None, q, window, autojunk=False).ratio() >= fuzzy_ratio:
            return n
    return None
