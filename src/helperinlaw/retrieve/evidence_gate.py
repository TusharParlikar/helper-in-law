"""G7 evidence gate: weak evidence -> abstain, no generation."""

from helperinlaw.core.store import Store
from helperinlaw.core.types import Chunk
from helperinlaw.parse.statutes import aliases
from helperinlaw.retrieve.understand import Query


def enough_evidence(
    store: Store, q: Query, ranked: list[tuple[Chunk, float]], min_score: float, min_passages: int
) -> bool:
    strong = [c for c, s in ranked if s >= min_score]
    if len(strong) < min_passages:
        return False
    # A question about a specific provision needs a passage from a case that applies it.
    if q.statutes:
        wanted = {a for act, s in q.statutes for a in aliases(act, s)}
        return any(wanted & set(store.statutes_of(c.case_id)) for c in strong)
    return True
