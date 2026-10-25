"""Rerank by query-term coverage, statute match, and profile-aware recency/authority.

ponytail: lexical reranker. A cross-encoder (bge-reranker-v2-m3) replaces `coverage` when a
GPU is available; the boosts stay.
"""

import math
from collections import Counter

from helperinlaw.core.store import Store
from helperinlaw.core.types import Chunk, Profile
from helperinlaw.parse.statutes import aliases
from helperinlaw.retrieve.understand import Query, terms


def stem(t: str) -> str:
    return t[:5]


MAX_TERMS = 10  # a long scenario is judged on its most distinctive words, not all of them
_IDF: dict[tuple[int, str, int], dict[str, float]] = {}


def idf_table(store: Store, index_version: str) -> dict[str, float]:
    """Inverse document frequency over the index's chunks, cached until the index changes."""
    n = store.db.execute(
        "SELECT COUNT(*) FROM chunks WHERE index_version=?", (index_version,)
    ).fetchone()[0]
    key = (id(store), index_version, n)
    if key not in _IDF:
        df: Counter[str] = Counter()
        for c in store.all_chunks(index_version):
            df.update({stem(t) for t in terms(c.prefix + " " + c.text)})
        _IDF.clear()
        _IDF[key] = {t: math.log((n + 1) / (k + 0.5)) for t, k in df.items()}
    return _IDF[key]


def coverage(query: str, text: str, idf: dict[str, float] | None = None) -> float:
    """Share of the query's informative weight that the passage contains (0..1)."""
    q = {stem(t) for t in terms(query)}
    if not q:
        return 0.0
    doc = {stem(t) for t in terms(text)}
    if not idf:
        return len(q & doc) / len(q)
    unseen = max(idf.values(), default=1.0)
    weights = sorted(((idf.get(t, unseen), t) for t in q), reverse=True)[:MAX_TERMS]
    total = sum(w for w, _ in weights)
    return sum(w for w, t in weights if t in doc) / total if total else 0.0


def rerank(
    store: Store,
    q: Query,
    hits: list[tuple[Chunk, float]],
    profile: Profile,
    top: int = 8,
    index_version: str = "v1",
) -> list[tuple[Chunk, float]]:
    wanted = {a for act, s in q.statutes for a in aliases(act, s)}
    idf = idf_table(store, index_version)
    scored = []
    for chunk, _ in hits:
        score = coverage(q.text, chunk.prefix + " " + chunk.text, idf)
        if wanted and wanted & set(store.statutes_of(chunk.case_id)):
            score += 0.15
        case = store.get_case(chunk.case_id)
        if case:
            if profile.recency == "newest":
                score += 0.01 * max(0, case.year - 2000) / 25
            if profile.recency == "landmark" and "Supreme" in case.court:
                score += 0.05
            if profile.jurisdiction and any(
                j.lower() in case.court.lower() or (j.upper() == "SC" and "Supreme" in case.court)
                for j in profile.jurisdiction
            ):
                score += 0.05
        scored.append((chunk, round(score, 4)))
    scored.sort(key=lambda x: -x[1])
    return scored[:top]
