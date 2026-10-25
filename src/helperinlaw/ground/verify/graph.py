"""Overruled-authority check (G10): treatment comes from the citation graph, never the LLM."""

from helperinlaw.core.store import Store
from helperinlaw.core.types import Treatment


def treatment(store: Store, case_id: str) -> Treatment:
    edges = {e["treatment"] for e in store.citing_cases(case_id)}
    for t in ("overruled", "distinguished", "followed"):
        if t in edges:
            return t  # type: ignore[return-value]
    return "unknown"


def overruled_by(store: Store, case_id: str) -> list[str]:
    return [e["citing_id"] for e in store.citing_cases(case_id) if e["treatment"] == "overruled"]
