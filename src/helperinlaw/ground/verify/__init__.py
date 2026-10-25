"""Verification suite (§4.4). Every claim runs every check; any failure drops it.
A dropped claim is never repaired by the LLM (§4.5)."""

from collections import Counter

from helperinlaw.core.store import Store
from helperinlaw.core.types import ClaimSet, Source, VerificationReport, VerifiedClaim, VerifiedRef
from helperinlaw.ground.text import content_terms, negated, normalise, paragraphs_of
from helperinlaw.ground.verify.allowlist import suspicious
from helperinlaw.ground.verify.entail import judge
from helperinlaw.ground.verify.entities import entities_supported
from helperinlaw.ground.verify.graph import overruled_by
from helperinlaw.ground.verify.injection import looks_injected
from helperinlaw.ground.verify.quote import find_quote, source_span

ROLE_BLOCKED = {"arguments"}  # counsel's submissions are not the court's holding


def allowlist_for(store: Store, sources: list[Source]) -> set[str]:
    allowed: set[str] = set()
    for s in sources:
        case = store.get_case(s.chunk.case_id)
        if case:
            allowed |= {x.lower() for x in (case.title, case.citation, case.neutral_citation) if x}
    return allowed


def section_of(store: Store, case_id: str, para: int) -> str:
    ps = store.get_paragraphs(case_id, para, para)
    return ps[0].section if ps else ""


def check_claim(
    store: Store,
    claim_text: str,
    refs: list[tuple[str, str]],
    by_id: dict[str, Source],
    allowed: set[str],
    claim_type: str,
    judge_model: str,
    answer_model: str,
    fuzzy: float,
) -> tuple[str | None, list[VerifiedRef]]:
    """Returns (drop reason or None, verified refs)."""
    if looks_injected(claim_text):
        return "injection", []
    if suspicious(claim_text, allowed):
        return "allowlist", []
    verified: list[VerifiedRef] = []
    displayed: list[str] = []
    for source_id, quote in refs:
        src = by_id.get(source_id)
        if src is None:
            return "unknown_source", []
        if looks_injected(quote):
            return "injection", []
        para = find_quote(quote, src.chunk.text, fuzzy)
        if para is None:
            return "quote_not_found", []
        if (
            claim_type in ("holding", "ratio")
            and section_of(store, src.chunk.case_id, para) in ROLE_BLOCKED
        ):
            return "role_mismatch", []
        verified.append(VerifiedRef(case_id=src.chunk.case_id, para=para, quote=quote.strip()))
        displayed.append(source_span(quote, dict(paragraphs_of(src.chunk.text))[para]))
    quotes = [r.quote for r in verified]
    if entities_supported(claim_text, quotes):
        return "entities", []
    if judge(claim_text, " ".join(quotes), judge_model, answer_model) != "supported":
        return "entailment", []
    # Checks ran on the model's quote; what the user sees is the verbatim source text.
    return None, [
        r.model_copy(update={"quote": d}) for r, d in zip(verified, displayed, strict=True)
    ]


def verify(
    store: Store,
    cs: ClaimSet,
    sources: list[Source],
    judge_model: str = "",
    answer_model: str = "",
    fuzzy: float = 0.97,
) -> tuple[list[VerifiedClaim], VerificationReport]:
    by_id = {s.id: s for s in sources}
    allowed = allowlist_for(store, sources)
    drops: Counter[str] = Counter()
    out: list[VerifiedClaim] = []
    seen: set[str] = set()
    for claim in cs.claims:
        key = normalise(claim.text)
        if key in seen:
            drops["duplicate"] += 1
            continue
        seen.add(key)
        reason, refs = check_claim(
            store,
            claim.text,
            [(r.source_id, r.quote) for r in claim.support],
            by_id,
            allowed,
            claim.type,
            judge_model,
            answer_model,
            fuzzy,
        )
        if reason:
            drops[reason] += 1
            continue
        out.append(VerifiedClaim(id=f"c{len(out) + 1}", claim=claim, refs=refs))

    report = VerificationReport(
        claims_proposed=len(cs.claims),
        verified=len(out),
        dropped=len(cs.claims) - len(out),
        drop_reasons=dict(drops),
        conflicts=conflicts(store, out),
    )
    return out, report


def conflicts(store: Store, claims: list[VerifiedClaim]) -> list[str]:
    """G10: surface disagreement and bad-law authorities from the graph, not the LLM."""
    notes: list[str] = []
    for c in claims:
        for r in c.refs:
            for later in overruled_by(store, r.case_id):
                case, by = store.get_case(r.case_id), store.get_case(later)
                if case and by:
                    note = f"{case.title} ({case.citation}) was overruled by {by.title} ({by.citation})."
                    if note not in notes:
                        notes.append(note)
    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            if {r.case_id for r in a.refs} == {r.case_id for r in b.refs}:
                continue  # one judgment's own sentences aren't a conflict of authority
            ta, tb = content_terms(a.claim.text), content_terms(b.claim.text)
            overlap = len(ta & tb) / max(1, len(ta), len(tb))
            if overlap >= 0.5 and negated(a.claim.text) != negated(b.claim.text):
                notes.append(f"Claims {a.id} and {b.id} appear to conflict; read both sources.")
    return notes
