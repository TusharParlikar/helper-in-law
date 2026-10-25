from helperinlaw.core.types import (
    AnswerBlock,
    Citation,
    Claim,
    Profile,
    SupportRef,
    VerifiedClaim,
    VerifiedRef,
)
from helperinlaw.present.final_guard import guard
from helperinlaw.present.overrides import parse_overrides, strip_overrides
from helperinlaw.present.presenter import present, to_markdown


def vc(i: int, text: str, kind: str = "ratio") -> VerifiedClaim:
    return VerifiedClaim(
        id=f"c{i}",
        claim=Claim(
            text=text,
            type=kind,  # type: ignore[arg-type]
            support=[SupportRef(source_id="S1", quote=text)],
        ),
        refs=[VerifiedRef(case_id="a", para=i, quote=text)],
    )


CLAIMS = [
    vc(1, "Bail is the rule.", "ratio"),
    vc(2, "The appeal is allowed.", "holding"),
    vc(3, "The appellant spent 14 months in custody.", "fact"),
    vc(4, "Obiter point here.", "obiter"),
]
CITES = [
    Citation(
        id=f"C{i}",
        case_id="a",
        case_title="Arjun Mehta v. State of Rajasthan",
        court="SC",
        date="2015-03-12",
        citation="(2015) 3 FSR 101",
        neutral_citation="",
        para=str(i),
        quote=c.claim.text,
    )
    for i, c in enumerate(CLAIMS, 1)
]
BY = {c.id: [f"C{i}"] for i, c in enumerate(CLAIMS, 1)}


def test_depth_and_structure() -> None:
    assert len(present(CLAIMS, BY, CITES, Profile(depth="quick"))) == 3
    irac = present(CLAIMS, BY, CITES, Profile(structure="irac"))
    assert irac[0].text.startswith("Rule:") and any(b.text.startswith("Conclusion:") for b in irac)
    table = present(CLAIMS, BY, CITES, Profile(structure="table"))
    assert table[0].text.startswith("Arjun Mehta v. State of Rajasthan | para 1 |")


def test_obiter_and_word_cap() -> None:
    assert len(present(CLAIMS, BY, CITES, Profile(obiter="hide"))) == 3
    assert any("(Obiter)" in b.text for b in present(CLAIMS, BY, CITES, Profile()))
    assert len(present(CLAIMS, BY, CITES, Profile(max_words=5))) == 1


def test_markdown_citation_styles() -> None:
    blocks = present(CLAIMS[:1], BY, CITES, Profile())
    assert "(2015) 3 FSR 101, para 1" in to_markdown(blocks, CITES[:1], Profile())
    assert "[para 1]" in to_markdown(
        blocks, CITES[:1], Profile(citation_style="inline_para", quotes="hover")
    )


def test_guard_blocks_new_numbers_names_and_uncited() -> None:
    ok = AnswerBlock(text="The appellant spent 14 months in custody.", citation_ids=["C3"])
    new_num = AnswerBlock(text="The appellant spent 18 months in custody.", citation_ids=["C3"])
    new_case = AnswerBlock(
        text="As in Ramesh Gupta v. State of Punjab, bail is the rule.", citation_ids=["C1"]
    )
    bad_id = AnswerBlock(text="Bail is the rule.", citation_ids=["C9"])
    kept, blocked = guard([ok, new_num, new_case, bad_id], CLAIMS, CITES)
    assert kept == [ok] and blocked == 3


def test_overrides() -> None:
    patch, ignored = parse_overrides("shorter, as a table, explain simply, without citations")
    assert patch == {"depth": "quick", "structure": "table", "tone": "plain"}
    assert ignored == ["without citations"]
    assert parse_overrides("just give me the answer")[1]
    assert (
        strip_overrides("Grounds for bail? shorter please, as a table")
        == "Grounds for bail? please"
    )
    assert parse_overrides("asdf qwerty") == ({}, [])
