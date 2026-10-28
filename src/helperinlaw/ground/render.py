"""G1: citations are rendered from the database. The LLM only ever produced source ids."""

from urllib.parse import quote

from helperinlaw.core.store import Store
from helperinlaw.core.types import Citation, LawRef, VerifiedClaim
from helperinlaw.ground.verify.graph import treatment
from helperinlaw.ingest.official import COI_EDITION, PREFIX, is_provision
from helperinlaw.parse.statutes import ACT_NAMES, aliases, extract_statutes

ACT_LABEL = {**{a: names[0] for a, names in ACT_NAMES.items()}, "CONST": "Constitution of India"}


def source_of(case_id: str) -> str:
    if case_id.startswith("sc-"):
        return "Supreme Court of India, e-SCR (Indian Supreme Court Judgments dataset, CC-BY-4.0)"
    return "Sample corpus (fictional judgment written for testing)"


def case_url(base: str, case_id: str, para: int | str | None = None) -> str:
    if not base:  # no API: links open the Streamlit app's own reader
        return f"?case={quote(case_id)}" + (f"&para={para}" if para else "")
    return f"{base}/cases/{case_id}/view" + (f"#para-{para}" if para else "")


def statute_url(base: str, act: str, section: str | int) -> str:
    if not base:
        return f"?statute={quote(act)}&section={quote(str(section))}"
    return f"{base}/statutes/{act}/{section}/view"


def law_ref(act: str, section: str, base: str, store: Store | None = None) -> LawRef:
    name = ACT_LABEL.get(act, act)
    unit = "Article" if act == "CONST" else "Section"
    search = quote(f"site:indiacode.nic.in {name} {unit.lower()} {section}")
    article = store.get_case(f"{PREFIX}{section}") if store and act == "CONST" else None
    if article:  # the official government text is indexed: link the exact page, carry the text
        paras = store.get_paragraphs(article.id) if store else []
        return LawRef(
            act=act, section=section, label=f"Article {section}, Constitution of India",
            url=statute_url(base, act, section), official_url=article.url,
            text=paras[0].text if paras else "", source=COI_EDITION,
        )
    return LawRef(
        act=act,
        section=section,
        label=f"{unit} {section}, {name}",
        equivalents=[f"{a} {s}" for a, s in aliases(act, section)[1:]],
        url=statute_url(base, act, section),
        official_url=f"https://www.google.com/search?q={search}",
    )


def render_laws(
    store: Store, citations: list[Citation], texts: list[str], base: str
) -> list[LawRef]:
    """Provisions named in the question/answer, else every provision the cited judgments apply."""
    applied = {tuple(x.split(" ", 1)) for c in citations for x in c.statutes}
    named = {r for t in texts for s in extract_statutes(t) for r in aliases(*s)}
    chosen = (applied & named) or applied
    return [law_ref(a, s, base, store) for a, s in sorted(chosen)][:8]


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
                        url=case.url if is_provision(case.id) else case_url(base, case.id, r.para),
                        treatment=treatment(store, case.id),
                        statutes=[f"{a} {s}" for a, s in store.statutes_of(case.id)],
                        kind="provision" if is_provision(case.id) else "judgment",
                        source=COI_EDITION if is_provision(case.id) else source_of(case.id),
                    )
                )
            ids.append(index[key])
        by_claim[c.id] = ids
    return citations, by_claim
