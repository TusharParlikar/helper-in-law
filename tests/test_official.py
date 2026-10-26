"""Constitution parser, real-judgment metadata parser, and the scenario flow over both."""

import json
from pathlib import Path

import pytest

from helperinlaw.core.store import Store
from helperinlaw.ingest.clean import clean
from helperinlaw.ingest.official import clean_markers, is_provision, parse_articles
from helperinlaw.ingest.sci import judgment_paragraphs, parse_meta, title_case
from helperinlaw.parse.statutes import extract_statutes
from helperinlaw.service import Service

FIXTURES = Path(__file__).parent / "fixtures"
OFFICIAL_PDF = Path("data/official/constitution_of_india_2024.pdf")


def lines(*text: str) -> list[tuple[int, str]]:
    return [(i + 1, t) for i, t in enumerate(text)]


def test_article_headings_follow_the_sequence() -> None:
    arts = parse_articles(lines(
        "Contents 1. Name and territory of the Union.",  # table of contents: no dash, ignored
        "1. Name and territory of the Union.—(1) India, that is Bharat, shall be a Union of States.",
        "9. Persons voluntarily acquiring citizenship.—No person shall be a citizen by virtue of article 5.",
        "10. Continuance of the rights of citizenship.—Every person who is a citizen shall continue.",
        "2[21A. Right to education.—The State shall provide free and compulsory education.]",
        "FIRST SCHEDULE",
        "238. The Rajasthan Colonisation (Amendment) Act.—not an article",
    ))
    assert [a.number for a in arts] == ["1", "9", "10", "21A"]  # "10." is never read as "0"
    assert arts[3].title == "Right to education"
    assert "article 5" in arts[1].text  # a cross-reference does not start a new article


def test_clean_markers() -> None:
    raw = "No person 1[shall be] deprived 3*** of his life. THE CONSTITUTION OF INDIA (Part III) 14 Right"
    assert clean_markers(raw) == "No person [shall be] deprived of his life."


def test_fixture_is_the_official_wording() -> None:
    arts = {a["number"]: a for a in json.loads((FIXTURES / "coi_articles.json").read_text(encoding="utf-8"))}
    assert arts["21"]["text"] == (
        "No person shall be deprived of his life or personal liberty except according to procedure "
        "established by law."
    )
    assert arts["22"]["text"].startswith("(1) No person who is arrested shall be detained in custody")


@pytest.mark.skipif(not OFFICIAL_PDF.exists(), reason="official PDF not downloaded")
def test_full_official_pdf_parses() -> None:
    from helperinlaw.ingest.official import english_lines

    arts = {a.number: a for a in parse_articles(english_lines(OFFICIAL_PDF))}
    assert len(arts) > 440
    for n in ("14", "19", "21", "21A", "22", "32", "226", "300A", "368"):
        assert n in arts and len(arts[n].text) > 40
    assert not any("THE CONSTITUTION OF INDIA" in a.text for a in arts.values())


def test_sci_metadata_and_paragraphs() -> None:
    d = json.loads((FIXTURES / "sci_meta_2018_13_1286.json").read_text(encoding="utf-8"))
    m = parse_meta(d["raw_html"], d["path"], d["nc_display"])
    assert m is not None
    assert m.title == "Dr. Ashwani Kumar v. Union of India & Ors."
    assert (m.citation, m.neutral, m.date) == ("[2018] 13 S.C.R. 1286", "2018 INSC 1201", "2018-12-13")
    assert m.coram == ["Madan B. Lokur", "Deepak Gupta"]
    assert "Art. 21" in m.headnote
    assert m.pdf_url.endswith("/data/pdf/year=2018/english/2018_13_1286_1311_EN.pdf")
    assert title_case("D.Y. CHANDRACHUD") == "D.Y. Chandrachud"
    text = clean("1. Headnote point.\nA\nB\n2. Another headnote.\nThe Judgment of the Court was delivered by\n"
                 "1. First paragraph of the Court.\n2. Second.\n3. Third.")
    assert [n for n, _ in judgment_paragraphs(text)] == [1, 2, 3]
    assert judgment_paragraphs(text)[0][1] == "First paragraph of the Court."


def test_article_references_in_judgments() -> None:
    assert ("CONST", "21") in extract_statutes("right to life u/Art. 21 of the Constitution")
    assert ("CONST", "14") in extract_statutes("violative of Article 14")
    assert ("CONST", "21A") in extract_statutes("Article 21A")


def test_scenario_gets_constitutional_provisions(service: Service) -> None:
    r = service.ask("My client was arrested and kept in custody without being informed of the grounds "
                    "of arrest and was not allowed to consult a lawyer.")
    provisions = [c for c in r.citations if c.kind == "provision"]
    assert provisions and provisions[0].case_id == "coi-22"
    assert "#page=" in provisions[0].url and "Legislative Department" in provisions[0].source
    assert all(c.quote in service.store.get_paragraphs(c.case_id)[0].text or c.kind == "judgment"
               for c in provisions)


def test_court_filter_never_hides_the_constitution(service: Service) -> None:
    from helperinlaw.core.types import Filters

    r = service.ask("Is there a right to personal liberty and life?", Filters(court="Bombay HC"))
    assert any(is_provision(c.case_id) for c in r.citations)


def test_article_lookup(service: Service, store: Store) -> None:
    a = service.get_article("Article 21")
    assert a["text"].startswith("Protection of life and personal liberty. No person shall be deprived")
    assert a["official_url"].startswith("https://cdnbbsr.s3waas.gov.in/") and "#page=" in a["official_url"]
    assert {j["case_id"] for j in a["judgments"]} >= {"fs_2015_mehta"}
    law = service.lookup_statute("Article", "21")["law"]
    assert law["text"] and law["official_url"] == a["official_url"]


def test_first_paragraph_on_the_authors_line() -> None:
    text = clean(
        "Headnote.\nThe Judgment of the Court was delivered by\n"
        "R. K. AGRAWAL, J. 1. The jurisdiction of this Court has been invoked.\n"
        "2. Brief facts follow.\n3. We hold so."
    )
    assert [n for n, _ in judgment_paragraphs(text)] == [1, 2, 3]


def test_unnumbered_first_paragraph_and_2024_layout() -> None:
    text = clean(
        "Headnotes\nJudgment / Order of the Supreme Court\nJudgment\nR. Mahadevan, J.\nLeave granted.\n"
        "2. This appeal is filed against the order of the High Court.\n3. We have heard both sides."
    )
    paras = judgment_paragraphs(text)
    assert [n for n, _ in paras] == [1, 2, 3]
    assert paras[0][1] == "Leave granted."  # the author's name line is not part of paragraph 1
