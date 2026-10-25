"""Stage A: question -> Verified Claim Set. Style-independent; the presenter never adds facts.

Failure policy (§4.5): drop failed claims; too many dropped -> extractive mode; nothing left
-> abstain.
"""

from typing import Literal

from helperinlaw.core import ollama
from helperinlaw.core.config import Settings
from helperinlaw.core.logging import get_logger
from helperinlaw.core.store import Store
from helperinlaw.core.types import (
    ClaimSet,
    Filters,
    Profile,
    Source,
    VerificationReport,
    VerifiedClaimSet,
)
from helperinlaw.ground.claim_extract import extractive_claims, llm_claims
from helperinlaw.ground.verify import verify
from helperinlaw.retrieve.evidence_gate import enough_evidence
from helperinlaw.retrieve.hybrid import search
from helperinlaw.retrieve.rerank import rerank
from helperinlaw.retrieve.rewrite import rewrite
from helperinlaw.retrieve.understand import understand

log = get_logger(__name__)
Mode = Literal["synthesised", "extractive"]


def retrieve(
    store: Store, cfg: Settings, question: str, filters: Filters | None, profile: Profile
) -> tuple[list[Source], bool]:
    q = understand(question, filters)
    hits = search(store, q, rewrite(q), cfg.index_version, cfg.use_dense)
    ranked = rerank(store, q, hits, profile)
    sources = [Source(id=f"S{i + 1}", chunk=c, score=s) for i, (c, s) in enumerate(ranked)]
    ok = enough_evidence(store, q, ranked, cfg.evidence_min_score, cfg.evidence_min_passages)
    return sources, ok


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
    sources, ok = retrieve(store, cfg, question, filters, profile)
    if not ok:
        return abstain(question, sources, ["Not found in the indexed judgments."])
    sources = [s for s in sources if s.score >= cfg.evidence_min_score * 0.6] or sources[:3]

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
