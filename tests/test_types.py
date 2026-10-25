import pytest
from pydantic import ValidationError

from helperinlaw.core.types import (
    LIMITS,
    AnswerBlock,
    Citation,
    Claim,
    Coverage,
    Response,
    VerificationReport,
)

COV = Coverage(corpus="x", as_of="2024-12-31", limits=LIMITS)
CIT = Citation(id="C1", case_id="a", case_title="A v. B", court="SC", date="2020-01-01",
               citation="(2020) 1 FSR 1", neutral_citation="", para="3", quote="q")


def test_claim_without_support_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Claim(text="Bail is the rule.", support=[])


def test_block_without_citation_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnswerBlock(text="x", citation_ids=[])


def test_block_citing_unknown_citation_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Response(answer_blocks=[AnswerBlock(text="x", citation_ids=["C9"])], citations=[CIT],
                 verification=VerificationReport(), coverage=COV, confidence="high")


def test_answer_needs_a_block() -> None:
    with pytest.raises(ValidationError):
        Response(answer_blocks=[], citations=[], verification=VerificationReport(),
                 coverage=COV, confidence="high")


def test_disclaimer_is_fixed() -> None:
    with pytest.raises(ValidationError):
        Response(answer_blocks=[], citations=[], verification=VerificationReport(),
                 coverage=COV, confidence="not_found", disclaimer="")


def test_valid_response() -> None:
    r = Response(answer_blocks=[AnswerBlock(text="x", citation_ids=["C1"])], citations=[CIT],
                 verification=VerificationReport(), coverage=COV, confidence="high")
    assert r.disclaimer.startswith("Research aid")
