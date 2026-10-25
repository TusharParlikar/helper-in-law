"""G1: citations are rendered from the database. The LLM only ever produced source ids."""

from urllib.parse import quote

from helperinlaw.core.store import Store
from helperinlaw.core.types import Citation, LawRef, VerifiedClaim
from helperinlaw.ground.verify.graph import treatment
from helperinlaw.parse.statutes import ACT_NAMES, aliases, extract_statutes

ACT_LABEL = {**{a: names[0] for a, names in ACT_NAMES.items()}, "CONST": "Constitution of India"}


def case_url(base: str, case_id: str, para: int | str | None = None) -> str:
    return f"{base}/cases/{case_id}/view" + (f"#para-{para}" if para else "")


def law_ref(act: str, section: str, base: str) -> LawRef:
    name = ACT_LABEL.get(act, act)
    unit = "Article" if act == "CONST" else "Section"
    search = quote(f"site:indiacode.nic.in {name} {unit.lower()} {section}")
    return LawRef(
        act=act,
        section=section,
        label=f"{unit} {section}, {name}",
        equivalents=[f"{a} {s}" for a, s in aliases(act, section)[1:]],
        url=f"{base}/statutes/{act}/{section}/view",
        official_url=f"https://www.google.com/search?q={search}",
    )


def render_laws(
    store: Store, citations: list[Citation], texts: list[str], base: str
) -> list[LawRef]:
    """Provisions named in the question/answer, else every provision the cited judgments apply."""
    applied = {tuple(x.split(" ", 1)) for c in citations for x in c.statutes}
    named = {r for t in texts for s in extract_statutes(t) for r in aliases(*s)}
    chosen = (applied & named) or applied
    return [law_ref(a, s, base) for a, s in sorted(chosen)][:8]


def render_citations(
    store: Store, claims: list[VerifiedClaim], base: str = ""
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
                        url=case_url(base, case.id, r.para),
                        treatment=treatment(store, case.id),
                        statutes=[f"{a} {s}" for a, s in store.statutes_of(case.id)],
                    )
                )
            ids.append(index[key])
        by_claim[c.id] = ids
    return citations, by_claim
