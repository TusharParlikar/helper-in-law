"""Hybrid retrieval: BM25 (FTS5) + dense (Ollama embeddings), fused with RRF, then filtered."""

import math

from helperinlaw.core import ollama
from helperinlaw.core.store import Store
from helperinlaw.core.types import Case, Chunk, Filters
from helperinlaw.parse.metadata import short_court
from helperinlaw.parse.statutes import aliases
from helperinlaw.retrieve.understand import Query, terms

RRF_K = 60
POOL = 200


def fts_match(text: str) -> str:
    toks = terms(text)
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(toks))


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def dense(store: Store, index_version: str, text: str, limit: int) -> list[tuple[str, float]]:
    # ponytail: brute-force cosine over every vector; Qdrant when the corpus is large.
    vecs = store.all_embeddings(index_version)
    if not vecs:
        return []
    qv = ollama.embed([text])[0]
    scored = sorted(((cid, cosine(qv, v)) for cid, v in vecs), key=lambda x: -x[1])
    return scored[:limit]


def passes(case: Case, f: Filters, store: Store) -> bool:
    if f.case_id and case.id != f.case_id:
        return False
    if f.court and short_court(case.court).lower() != f.court.lower() \
            and case.court.lower() != f.court.lower():
        return False
    if f.year_from and case.year < f.year_from:
        return False
    if f.year_to and case.year > f.year_to:
        return False
    if f.statute:
        act, _, sec = f.statute.partition(":")
        wanted = set(aliases(act, sec))
        if not wanted & set(store.statutes_of(case.id)):
            return False
    return True


def search(store: Store, q: Query, queries: list[str], index_version: str,
           use_dense: bool, limit: int = 30) -> list[tuple[Chunk, float]]:
    rankings: list[list[str]] = []
    for text in queries:
        if match := fts_match(text):
            rankings.append([cid for cid, _ in store.bm25(index_version, match, POOL)])
    if use_dense:
        try:
            rankings.append([cid for cid, _ in dense(store, index_version, q.text, POOL)])
        except ollama.OllamaError:
            pass  # dense is an enhancement; BM25 alone still answers
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    out: list[tuple[Chunk, float]] = []
    cases: dict[str, Case | None] = {}
    for cid, score in sorted(fused.items(), key=lambda x: -x[1]):
        chunk = store.get_chunk(index_version, cid)
        if chunk is None:
            continue
        if chunk.case_id not in cases:
            cases[chunk.case_id] = store.get_case(chunk.case_id)
        case = cases[chunk.case_id]
        if case and passes(case, q.filters, store):
            out.append((chunk, score))
        if len(out) >= limit:
            break
    return out
