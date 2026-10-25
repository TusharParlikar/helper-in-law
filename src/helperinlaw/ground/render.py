"""G1: citations are rendered from the database. The LLM only ever produced source ids."""

from helperinlaw.core.store import Store
from helperinlaw.core.types import Citation, VerifiedClaim
from helperinlaw.ground.verify.graph import treatment


def render_citations(
    store: Store, claims: list[VerifiedClaim]
) -> tuple[list[Citation], dict[str, list[str]]]:
    """Returns (citations, claim id -> citation ids). Identical (case, para, quote) refs share one id."""
    citations: list[Citation] = []
    index: dict[tuple[str, int, str], str] = {}
    by_claim: dict[str, list[str]] = {}
    for c in claims:
        ids = []
        for r in c.refs:
            key = (r.case_id, r.para, r.quote)
            if key not in index:
                case = store.get_case(r.case_id)
                if case is None:
                    continue
                cid = f"C{len(citations) + 1}"
                index[key] = cid
                citations.append(
                    Citation(
                        id=cid,
                        case_id=case.id,
                        case_title=case.title,
                        court=case.court,
                        date=case.date,
                        citation=case.citation,
                        neutral_citation=case.neutral_citation,
                        para=str(r.para),
                        quote=r.quote,
                        url=case.url,
                        treatment=treatment(store, case.id),
                    )
                )
            ids.append(index[key])
        by_claim[c.id] = ids
    return citations, by_claim
