import json
from pathlib import Path

from helperinlaw.core.store import Store
from helperinlaw.parse.citations import treatment_of
from helperinlaw.parse.paragraphs import split_paragraphs
from helperinlaw.parse.statutes import aliases, extract_statutes

GOLD = Path(__file__).parent.parent / "eval" / "datasets" / "gold_parse.jsonl"


def test_paragraphs_only_accept_increasing_numbers() -> None:
    header, paras = split_paragraphs(
        "Title\n\n1. One. It cost Rs.\n2. 000 more.\n2. Two.\n3. Three."
    )
    assert header == "Title"
    assert [n for n, _ in paras] == [1, 2, 3]


def test_statute_extraction_variants() -> None:
    text = (
        "Section 302 IPC; Section 439 of the Code of Criminal Procedure; "
        "Section 65B(4) of the Indian Evidence Act; Section 103 of the Bharatiya Nyaya Sanhita, "
        "2023; Section 304 Part I IPC; Article 21 of the Constitution"
    )
    assert set(extract_statutes(text)) == {
        ("IPC", "302"),
        ("CrPC", "439"),
        ("IEA", "65B"),
        ("BNS", "103"),
        ("IPC", "304"),
        ("CONST", "21"),
    }


def test_aliases_both_ways() -> None:
    assert ("BNS", "103") in aliases("IPC", "302")
    assert ("IPC", "302") in aliases("BNS", "103")
    assert aliases("IPC", "999") == [("IPC", "999")]


def test_treatment_tagging() -> None:
    assert treatment_of("The view in X is accordingly overruled.") == "overruled"
    assert treatment_of("The principles in X are followed.") == "followed"
    assert treatment_of("X is clearly distinguishable on facts.") == "distinguished"
    assert treatment_of("Reference was made to X.") == "unknown"


def test_gold_parse_accuracy(store: Store) -> None:
    """M3 exit: >=95% title/date/bench, >=90% paragraph numbering on the gold set."""
    rows = [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]
    meta_ok = paras_ok = 0
    for g in rows:
        case = store.get_case(g["case_id"])
        assert case is not None
        meta_ok += (case.title, case.date, case.bench) == (g["title"], g["date"], g["bench"])
        paras_ok += len(store.get_paragraphs(case.id)) == g["paragraphs"]
    assert meta_ok / len(rows) >= 0.95
    assert paras_ok / len(rows) >= 0.90


def test_citation_graph(store: Store) -> None:
    assert store.citing_cases("fs_2016_verma") == [
        {"citing_id": "fs_2020_joshi", "treatment": "overruled", "para": 6}
    ]
    assert store.citing_cases("fs_2015_mehta")[0]["treatment"] == "followed"


def test_real_report_citations_are_normalised() -> None:
    from helperinlaw.parse.citations import extract_citations

    paras = [(4, "As held in [2018] 13 SCR 1286 and in 2021 INSC 295, which we have followed."),
             (9, "The view in [2017] 10 S.C.R. 569 is overruled.")]
    got = {c: (t, n) for c, t, n in extract_citations(paras)}
    assert got["[2018] 13 S.C.R. 1286"] == ("followed", 4)
    assert got["2021 INSC 295"] == ("followed", 4)
    assert got["[2017] 10 S.C.R. 569"] == ("overruled", 9)
