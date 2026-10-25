"""Rerank by query-term coverage, statute match, and profile-aware recency/authority.

ponytail: lexical reranker. A cross-encoder (bge-reranker-v2-m3) replaces `coverage` when a
GPU is available; the boosts stay.
"""

from helperinlaw.core.store import Store
from helperinlaw.core.types import Chunk, Profile
from helperinlaw.parse.statutes import aliases
from helperinlaw.retrieve.understand import Query, terms


def stem(t: str) -> str:
    return t[:5]


def coverage(query: str, text: str) -> float:
    q = {stem(t) for t in terms(query)}
    if not q:
        return 0.0
    doc = {stem(t) for t in terms(text)}
    return len(q & doc) / len(q)


def rerank(
    store: Store, q: Query, hits: list[tuple[Chunk, float]], profile: Profile, top: int = 8
) -> list[tuple[Chunk, float]]:
    wanted = {a for act, s in q.statutes for a in aliases(act, s)}
    scored = []
    for chunk, _ in hits:
        score = coverage(q.text, chunk.prefix + " " + chunk.text)
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
