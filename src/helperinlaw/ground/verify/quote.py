"""G3: the quote must exist in the cited chunk. Exact (normalised) first, then fuzzy for
whitespace/OCR noise only."""

from difflib import SequenceMatcher

from helperinlaw.ground.text import normalise, paragraphs_of, sentences

MIN_QUOTE_WORDS = 5  # "the court held" matches everything; a quote must pin something down


def find_quote(quote: str, chunk_text: str, fuzzy_ratio: float = 0.97) -> int | None:
    """Returns the paragraph number containing the quote, or None if it isn't there."""
    q = normalise(quote).strip(" .\"'")
    if len(q.split()) < MIN_QUOTE_WORDS:
        return None
    paras = [(n, normalise(para)) for n, para in paragraphs_of(chunk_text)]
    for n, p in paras:  # exact everywhere first: the fuzzy scan is the expensive part
        if q in p:
            return n
    qw = q.split()
    for n, p in paras:
        if fuzzy_match(qw, p.split(), fuzzy_ratio):
            return n
    return None


def source_span(quote: str, para: str) -> str:
    """The verbatim source sentences a verified quote came from. Displayed quotes are always
    the record's own text, never the model's copy of it."""
    q = normalise(quote).strip(" .\"'")
    sents = sentences(para)
    windows = [" ".join(sents[i : i + size]) for size in range(1, 5) for i in range(len(sents) - size + 1)]
    for span in windows:  # shortest window first: a clause never drags in its neighbours
        if q in normalise(span):
            return span
    # only reached for a fuzzy (OCR-noise) match: pick the closest window
    return max(windows, key=lambda w: SequenceMatcher(None, q, normalise(w), autojunk=False).ratio(),
               default=para)


def fuzzy_match(qw: list[str], pw: list[str], ratio: float) -> bool:
    """OCR noise changes letters, not whole words: compare equal-length word windows, and every
    word must have a close counterpart. Dropping or adding a word ("not") never matches."""
    need = 0.6 * len(qw)
    for i in range(len(pw) - len(qw) + 1):
        win = pw[i : i + len(qw)]
        # cheap screen: noise touches a few words, so most must already match exactly
        if sum(a == b for a, b in zip(qw, win, strict=True)) < need:
            continue
        if SequenceMatcher(None, " ".join(qw), " ".join(win), autojunk=False).ratio() < ratio:
            continue
        if all(
            a == b or SequenceMatcher(None, a, b).ratio() >= 0.75
            for a, b in zip(qw, win, strict=True)
        ):
            return True
    return False
