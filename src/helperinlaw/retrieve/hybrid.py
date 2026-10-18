"""Hybrid retrieval: BM25 (FTS5) + dense (Ollama embeddings), fused with RRF, then filtered."""

import heapq
import math
import threading
from functools import lru_cache
from operator import mul

from helperinlaw.core import ollama
from helperinlaw.core.store import Store
from helperinlaw.core.types import Case, Chunk, Filters
from helperinlaw.ingest.official import PREFIX, is_provision
from helperinlaw.parse.metadata import short_court
from helperinlaw.parse.statutes import aliases
from helperinlaw.retrieve.understand import Query, terms

RRF_K = 60
POOL = 200


def fts_match(text: str) -> str:
    toks = terms(text)
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(toks))


def unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def cosine(a: list[float], b: list[float]) -> float:
    return sum(map(mul, unit(a), unit(b)))


_VECS: dict[tuple[int, str, int], list[tuple[str, list[float]]]] = {}
_VECS_LOCK = threading.Lock()


def vectors(store: Store, index_version: str) -> list[tuple[str, list[float]]]:
    """Unit vectors for the index, loaded once and kept until the embedding count changes."""
    n = store.db.execute(
        "SELECT COUNT(*) FROM embeddings WHERE index_version=?", (index_version,)
    ).fetchone()[0]
    key = (id(store), index_version, n)
    with _VECS_LOCK:
        if key not in _VECS:
            _VECS.clear()
            _VECS[key] = [(cid, unit(v)) for cid, v in store.all_embeddings(index_version)]
        return _VECS[key]


@lru_cache(maxsize=256)  # provisions and judgments are searched separately with the same text
def query_vector(text: str) -> tuple[float, ...]:
    return tuple(unit(ollama.embed([text])[0]))


def dense(store: Store, index_version: str, text: str, limit: int) -> list[tuple[str, float]]:
    # ponytail: brute-force cosine over every vector (~0.1 s at 9k); Qdrant when the corpus is large.
    vecs = vectors(store, index_version)
    if not vecs:
        return []
    qv = query_vector(text)
    return heapq.nlargest(limit, ((cid, sum(map(mul, qv, v))) for cid, v in vecs), key=lambda x: x[1])


def passes(case: Case, f: Filters, store: Store) -> bool:
    if f.case_id and case.id != f.case_id:
        return False
    if is_provision(case.id):
        return True  # court/year filters choose precedents; the Constitution always applies
    if (
        f.court
        and short_court(case.court).lower() != f.court.lower()
        and case.court.lower() != f.court.lower()
    ):
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


def search(
    store: Store,
    q: Query,
    queries: list[str],
    index_version: str,
    use_dense: bool,
    limit: int = 30,
    kind: str | None = None,
) -> list[tuple[Chunk, float]]:
    """kind: "provision" (Constitution only), "judgment" (everything else) or None (both)."""
    like, negate = (f"{PREFIX}%", kind == "judgment") if kind else ("%", False)
    rankings: list[list[str]] = []
    for text in queries:
        if match := fts_match(text):
            rankings.append([cid for cid, _ in store.bm25(index_version, match, POOL, like, negate)])
    if use_dense:
        try:
            hits = dense(store, index_version, q.text, POOL * 3)
            if kind:
                hits = [h for h in hits if is_provision(h[0]) == (kind == "provision")]
            rankings.append([cid for cid, _ in hits[:POOL]])
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
