"""Fault injection for the verifier (roadmap §10.2). Each generator takes a known-good claim
and returns a corrupted copy, or None if the fault doesn't apply to that claim."""

import re
from collections.abc import Callable

from helperinlaw.core.types import Claim, Source, SupportRef

Fault = Callable[[Claim, list[Source], list[Claim]], Claim | None]


def _with(
    claim: Claim,
    text: str | None = None,
    quote: str | None = None,
    source_id: str | None = None,
    type_: str | None = None,
) -> Claim:
    ref = claim.support[0]
    return Claim(
        text=text if text is not None else claim.text,
        support=[
            SupportRef(
                source_id=source_id or ref.source_id,
                quote=quote if quote is not None else ref.quote,
            )
        ],
        type=type_ or claim.type,  # type: ignore[arg-type]
        stance=claim.stance,
    )


def swap_case_name(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    return _with(c, text=f"{c.text.rstrip('.')} , as held in Ramesh Gupta v. State of Punjab.")


def swap_citation(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    return _with(c, text=f"{c.text.rstrip('.')} ((2019) 3 SCC 412).")


def alter_number(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    m = re.search(r"\d+", c.text)
    if not m:
        return None
    return _with(c, text=c.text[: m.start()] + str(int(m.group(0)) + 2) + c.text[m.end() :])


def invert_meaning(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    for a, b in (
        (" shall not ", " shall "),
        (" is not ", " is "),
        (" cannot ", " can "),
        (" shall ", " shall not "),
        (" must ", " must not "),
        (" may ", " may not "),
        (" is ", " is not "),
    ):
        if a in c.text:
            return _with(c, text=c.text.replace(a, b, 1))
    return None


def delete_negation_from_quote(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    q = c.support[0].quote
    for neg in (" not ", " no ", " never "):
        if neg in q:
            new = q.replace(neg, " ", 1)
            return _with(c, text=c.text.replace(neg, " ", 1), quote=new)
    return None


def quote_for_other_claim(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    for other in o:
        if other.support[0].quote != c.support[0].quote and other.text != c.text:
            return _with(c, quote=other.support[0].quote, source_id=other.support[0].source_id)
    return None


def fabricate_quote(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    fake = "The court categorically held that this principle admits of no exception whatsoever."
    return _with(c, text="The principle admits of no exception whatsoever.", quote=fake)


def nonexistent_source(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    return _with(c, source_id="S99")


def unsupported_tail(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    return _with(c, text=f"{c.text.rstrip('.')}, and the accused must therefore be acquitted.")


def argument_as_holding(c: Claim, s: list[Source], o: list[Claim]) -> Claim | None:
    """Counsel's submission presented as the court's holding (stands in for dissent/obiter)."""
    for src in s:
        for line in src.chunk.text.split("\n"):
            if "Learned counsel" in line:
                sent = re.sub(r"^⟦\d+⟧\s*", "", line).split(". ")[0].rstrip(".") + "."
                return Claim(
                    text=sent, type="holding", support=[SupportRef(source_id=src.id, quote=sent)]
                )
    return None


FAULTS: dict[str, Fault] = {
    "swap_case_name": swap_case_name,
    "swap_citation": swap_citation,
    "alter_number": alter_number,
    "invert_meaning": invert_meaning,
    "delete_negation_from_quote": delete_negation_from_quote,
    "quote_for_other_claim": quote_for_other_claim,
    "fabricate_quote": fabricate_quote,
    "nonexistent_source": nonexistent_source,
    "unsupported_tail": unsupported_tail,
    "argument_as_holding": argument_as_holding,
}
