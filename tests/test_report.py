"""The research report: structured PDF when there is proof, refused when there is none."""

import pytest

from helperinlaw.service import Service

pytest.importorskip("fpdf")
pymupdf = pytest.importorskip("pymupdf")

from helperinlaw.report import NoProof, build_report, has_proof  # noqa: E402

SITUATION = "My client was arrested and not informed of the grounds of arrest and not allowed to consult a lawyer."


def test_report_has_every_section_and_the_verbatim_proof(service: Service) -> None:
    r = service.ask(SITUATION)
    assert has_proof(r)
    pdf = build_report(r, SITUATION, service.store)
    assert pdf.startswith(b"%PDF")
    text = " ".join(page.get_text() for page in pymupdf.open(stream=pdf, filetype="pdf"))
    for section in ("THE SITUATION", "SUMMARY", "GOVERNING CONSTITUTIONAL PROVISIONS", "ANALYSIS",
                    "TABLE OF AUTHORITIES", "LIMITS OF THIS RESEARCH"):
        assert section in text, section
    flat = " ".join(text.split())
    for c in r.citations:  # every quoted proof appears in the report, word for word
        assert " ".join(c.quote.split())[:60] in flat
    assert "Research aid, not legal advice" in flat


def test_no_proof_no_report(service: Service) -> None:
    r = service.ask("What is the recipe for butter chicken?")
    assert not has_proof(r)
    with pytest.raises(NoProof):
        build_report(r, "What is the recipe for butter chicken?", service.store)
