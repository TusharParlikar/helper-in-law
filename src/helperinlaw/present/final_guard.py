"""Final guard on presented text: every block maps to a verified claim, introduces no new
numbers, and names no case outside the cited set."""

from helperinlaw.core.types import AnswerBlock, Citation, VerifiedClaim
from helperinlaw.ground.verify.allowlist import suspicious
from helperinlaw.ground.verify.entities import entities
from helperinlaw.ground.verify.injection import looks_injected


def guard(blocks: list[AnswerBlock], claims: list[VerifiedClaim],
          citations: list[Citation]) -> tuple[list[AnswerBlock], int]:
    """Returns (blocks that pass, number blocked)."""
    cite_ids = {c.id for c in citations}
    allowed = {x.lower() for c in citations for x in (c.case_title, c.citation, c.neutral_citation) if x}
    known = set()
    for c in claims:
        known |= entities(c.claim.text)
    for c in citations:
        known |= entities(f"{c.para} {c.date} {c.citation} {c.neutral_citation}")
    kept = []
    for b in blocks:
        if not b.citation_ids or set(b.citation_ids) - cite_ids:
            continue
        if entities(b.text) - known or suspicious(b.text, allowed) or looks_injected(b.text):
            continue
        kept.append(b)
    return kept, len(blocks) - len(kept)
