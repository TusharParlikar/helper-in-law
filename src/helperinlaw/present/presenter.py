"""Stage B presenter: shapes verified claims for a profile. It receives only the Verified Claim
Set and rendered citations; it can reorder, select and frame claims, never add facts.

ponytail: deterministic templates, no LLM restyling. Tone changes framing only; add an LLM
rewrite (checked by final_guard) if users want true plain-English paraphrase.
"""

from helperinlaw.core.types import AnswerBlock, Citation, Profile, VerifiedClaim

DEPTH_LIMIT = {"quick": 3, "standard": 6, "deep": 100}
LEAD = {
    "technical": "",
    "plain": "In simple terms: ",
    "new": "What this means: ",
}
IRAC = [("Rule", {"statute", "ratio"}), ("Application", {"fact", "procedural", "obiter"}),
        ("Conclusion", {"holding"})]
MEMO = [("Holdings", {"holding"}), ("Reasoning", {"ratio", "statute", "obiter"}),
        ("Facts and procedure", {"fact", "procedural"})]


def select(claims: list[VerifiedClaim], profile: Profile) -> list[VerifiedClaim]:
    out = [c for c in claims
           if not (profile.contrary_authority == "never" and c.claim.stance == "contrary")
           and not (profile.obiter == "hide" and c.claim.type == "obiter")]
    out = out[: DEPTH_LIMIT[profile.depth]]
    if profile.max_words:
        kept, words = [], 0
        for c in out:
            words += len(c.claim.text.split())
            if kept and words > profile.max_words:
                break
            kept.append(c)
        out = kept
    return out


def cite_label(c: Citation, style: str) -> str:
    if style == "neutral" and c.neutral_citation:
        return f"{c.neutral_citation}, para {c.para}"
    if style == "inline_para":
        return f"para {c.para}"
    if style == "footnotes":
        return c.id
    return f"{c.case_title}, {c.citation}, para {c.para}"


def present(claims: list[VerifiedClaim], by_claim: dict[str, list[str]],
            citations: list[Citation], profile: Profile) -> list[AnswerBlock]:
    chosen = select(claims, profile)
    cites = {c.id: c for c in citations}
    lead = LEAD[profile.tone]

    def text_of(c: VerifiedClaim) -> str:
        t = c.claim.text
        if profile.obiter == "highlight" and c.claim.type == "obiter":
            t = f"(Obiter) {t}"
        return t

    def block(c: VerifiedClaim, text: str) -> AnswerBlock:
        return AnswerBlock(text=text, citation_ids=by_claim[c.id])

    if profile.structure == "table":
        rows = []
        for c in chosen:
            first = cites[by_claim[c.id][0]]
            rows.append(block(c, f"{first.case_title} | para {first.para} | {text_of(c)}"))
        return rows
    if profile.structure in ("irac", "memo"):
        plan = IRAC if profile.structure == "irac" else MEMO
        blocks = []
        for heading, kinds in plan:
            group = [c for c in chosen if c.claim.type in kinds]
            for i, c in enumerate(group):
                prefix = f"{heading}: " if i == 0 else ""
                blocks.append(block(c, f"{prefix}{lead}{text_of(c)}"))
        return blocks
    bullet = "- " if profile.structure == "bullets" else ""
    return [block(c, f"{bullet}{lead}{text_of(c)}") for c in chosen]


def to_markdown(blocks: list[AnswerBlock], citations: list[Citation], profile: Profile) -> str:
    cites = {c.id: c for c in citations}
    lines = []
    for b in blocks:
        refs = "; ".join(cite_label(cites[i], profile.citation_style) for i in b.citation_ids)
        lines.append(f"{b.text} [{refs}]")
    if profile.citation_style == "footnotes" or profile.quotes == "always":
        lines.append("")
        for c in citations:
            lines.append(f"[{c.id}] {c.case_title}, {c.citation}, para {c.para}: \"{c.quote}\"")
    return "\n".join(lines)
