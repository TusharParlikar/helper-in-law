"""Stage A: question -> Verified Claim Set. Style-independent; the presenter never adds facts.

Failure policy (§4.5): drop failed claims; too many dropped -> extractive mode; nothing left
-> abstain.
"""

from collections import Counter
from typing import Literal

from helperinlaw.core import ollama
from helperinlaw.core.config import Settings
from helperinlaw.core.logging import get_logger
from helperinlaw.core.store import Store
from helperinlaw.core.types import (
    Chunk,
    ClaimSet,
    Filters,
    Profile,
    Source,
    VerificationReport,
    VerifiedClaimSet,
)
from helperinlaw.ground.claim_extract import extractive_claims, llm_claims
from helperinlaw.ground.verify import verify
from helperinlaw.ingest.official import PREFIX, is_provision
from helperinlaw.retrieve.evidence_gate import enough_evidence, foreign
from helperinlaw.retrieve.hybrid import search
from helperinlaw.retrieve.rerank import rerank
from helperinlaw.retrieve.rewrite import rewrite
from helperinlaw.retrieve.stair import stair_articles
from helperinlaw.retrieve.understand import correct_spelling, understand

log = get_logger(__name__)
MAX_PROVISIONS, MAX_JUDGMENTS = 4, 6
PRECEDENT_BOOST = 0.4  # added to a provision cited by every retrieved judgment
STAIR_BOOST = 0.4  # added to STAIR's first pick (2/3 and 1/3 of it to the next two); cfg.use_stair
PARENT_WINDOW = 1  # neighbouring paragraphs added to each retrieved judgment passage
Mode = Literal["synthesised", "extractive"]


def retrieve(
    store: Store, cfg: Settings, question: str, filters: Filters | None, profile: Profile
) -> tuple[list[Source], bool]:
    question = correct_spelling(question, store.word_counts(cfg.index_version))
    q = understand(question, filters)
    queries = rewrite(q)

    # A scenario needs both: the constitutional text that governs it and precedent applying it,
    # searched separately so one long judgment can't crowd the Constitution out.
    def best(kind: str, n: int, per_case: int, extra: list[Chunk] | None = None,
             boost: dict[str, float] | None = None) -> list[tuple[Chunk, float]]:
        hits = search(store, q, queries, cfg.index_version, cfg.use_dense, 60, kind)
        seen = {c.id for c, _ in hits}
        hits += [(c, 0.0) for c in extra or [] if c.id not in seen]
        scored = [
            (c, round(s + (boost or {}).get(c.case_id, 0.0), 4))
            for c, s in rerank(store, q, hits, profile, top=80, index_version=cfg.index_version)
        ]
        out: list[tuple[Chunk, float]] = []
        count: Counter[str] = Counter()
        for chunk, score in sorted(scored, key=lambda x: -x[1]):
            if count[chunk.case_id] < per_case:
                out.append((chunk, score))
                count[chunk.case_id] += 1
        return out[:n]

    judgments = best("judgment", MAX_JUDGMENTS, 2)
    # Precedent votes for the provisions: an article the retrieved judgments apply is likely
    # the one governing the situation, even when the user's words don't match its text.
    # In rank order, not a set: the vote's candidates are appended in this order, and a set's
    # order changes with Python's hash seed, which made tied Articles swap between runs.
    cases = list(dict.fromkeys(c.case_id for c, _ in judgments))
    applied = Counter(s for cid in cases for act, s in store.statutes_of(cid) if act == "CONST")
    extra = [c for a in applied if (c := store.get_chunk(cfg.index_version, f"{PREFIX}{a}:1-1"))]
    # (Weighting votes by how rare an Article is was tried and measured worse: eval/run_scenarios.py.)
    boost = {f"{PREFIX}{a}": PRECEDENT_BOOST * k / len(cases) for a, k in applied.items()}
    # STAIR: the model reads the Constitution's table of contents and votes too (off by default).
    for rank, a in enumerate(picks := stair_articles(store, cfg, question)):
        if a not in applied and (c := store.get_chunk(cfg.index_version, f"{PREFIX}{a}:1-1")):
            extra.append(c)
        boost[f"{PREFIX}{a}"] = boost.get(f"{PREFIX}{a}", 0.0) + STAIR_BOOST * (1 - rank / len(picks))
    provisions = best("provision", MAX_PROVISIONS, 1, extra, boost)
    ranked = sorted(provisions + judgments, key=lambda x: -x[1])
    sources = [Source(id=f"S{i + 1}", chunk=c, score=s) for i, (c, s) in enumerate(ranked)]
    ok = enough_evidence(store, q, ranked, cfg.evidence_min_score, cfg.evidence_min_passages)
    return sources, ok


def expand(store: Store, chunk: Chunk) -> Chunk:
    """Parent expansion: a matched passage plus its neighbouring paragraphs, so the sentence
    that states the holding is available even when the match was the paragraph before it.
    Retrieval scores are unchanged; only what claims are drawn from grows."""
    window = PARENT_WINDOW
    if not window or is_provision(chunk.case_id):
        return chunk
    paras = store.get_paragraphs(chunk.case_id, chunk.para_from - window, chunk.para_to + window)
    if not paras:
        return chunk
    text = "\n".join(f"⟦{p.n}⟧ {p.text}" for p in paras)
    return chunk.model_copy(update={"para_from": paras[0].n, "para_to": paras[-1].n, "text": text})


def abstain(
    question: str,
    sources: list[Source],
    gaps: list[str],
    proposed: int = 0,
    reasons: dict[str, int] | None = None,
) -> VerifiedClaimSet:
    return VerifiedClaimSet(
        question=question,
        gaps=gaps or ["Not found in the indexed judgments."],
        nearest=list(dict.fromkeys(s.chunk.case_id for s in sources))[:3],
        report=VerificationReport(
            claims_proposed=proposed, dropped=proposed, mode="abstained", drop_reasons=reasons or {}
        ),
    )


def answer_content(
    store: Store, cfg: Settings, question: str, filters: Filters | None, profile: Profile
) -> VerifiedClaimSet:
    if where := foreign(question):
        return abstain(question, [], [f"Helper in Law covers Indian law only; this question is about \"{where}\"."])
    sources, ok = retrieve(store, cfg, question, filters, profile)
    if not ok:
        return abstain(question, sources, ["Not found in the indexed judgments."])
    sources = [s for s in sources if s.score >= cfg.evidence_min_score * 0.6] or sources[:3]
    sources = [s.model_copy(update={"chunk": expand(store, s.chunk)}) for s in sources]

    def run(cs: ClaimSet, rejected: int, mode: Mode) -> VerifiedClaimSet:
        claims, report = verify(
            store, cs, sources, cfg.judge_model, cfg.llm_model, cfg.fuzzy_quote_ratio
        )
        report.claims_proposed += rejected
        report.dropped += rejected
        if rejected:
            report.drop_reasons["schema"] = rejected
        report.mode = mode
        return VerifiedClaimSet(question=question, claims=claims, report=report, gaps=cs.gaps)

    result: VerifiedClaimSet | None = None
    if cfg.use_llm:
        try:
            result = run(*llm_claims(cfg.llm_model, question, sources), "synthesised")
        except ollama.OllamaError as e:
            log.warning("LLM unavailable, extractive mode", extra={"extra_fields": {"err": str(e)}})
        if result is not None and result.report.claims_proposed == 0:
            return abstain(question, sources, result.gaps)
        r = result.report if result else None
        if (
            result
            and r
            and r.claims_proposed
            and r.dropped / r.claims_proposed <= cfg.max_drop_ratio
        ):
            return result
    # G8: extractive fallback (or the configured mode when the LLM is off).
    llm_report = result.report if result else None
    ext = run(extractive_claims(store, question, sources), 0, "extractive")
    if llm_report:
        ext.report.claims_proposed += llm_report.claims_proposed
        ext.report.dropped += llm_report.claims_proposed
        for k, v in llm_report.drop_reasons.items():
            ext.report.drop_reasons[f"llm_{k}"] = v
    if not ext.claims:
        return abstain(
            question, sources, ext.gaps, ext.report.claims_proposed, ext.report.drop_reasons
        )
    return ext
