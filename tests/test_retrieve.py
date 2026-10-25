from helperinlaw.core.config import Settings
from helperinlaw.core.store import Store
from helperinlaw.core.types import Filters, Profile
from helperinlaw.ground.pipeline import retrieve
from helperinlaw.retrieve.hybrid import cosine, fts_match
from helperinlaw.retrieve.rewrite import rewrite
from helperinlaw.retrieve.understand import understand


def test_understand_filters_and_statutes() -> None:
    q = understand("Supreme Court cases on Section 302 IPC after 2015")
    assert q.filters.court == "SC" and q.filters.year_from == 2015
    assert ("IPC", "302") in q.statutes
    q = understand("bail in the Bombay High Court between 2019 and 2022")
    assert q.filters.court == "Bombay HC"
    assert (q.filters.year_from, q.filters.year_to) == (2019, 2022)


def test_explicit_filters_win() -> None:
    q = understand("cases after 2015", Filters(year_from=2020))
    assert q.filters.year_from == 2020


def test_rewrite_adds_alias() -> None:
    qs = rewrite(understand("What does Section 103 BNS say?"))
    assert any("302" in q for q in qs)


def test_fts_match_is_safe() -> None:
    assert fts_match('bail" OR 1=1; DROP') == '"bail" OR "drop"'
    assert fts_match("the of and") == ""


def test_cosine() -> None:
    assert cosine([1, 0], [1, 0]) == 1.0 and cosine([1, 0], [0, 1]) == 0.0


def top_case(store: Store, cfg: Settings, q: str, f: Filters | None = None) -> str:
    sources, _ = retrieve(store, cfg, q, f, Profile())
    return sources[0].chunk.case_id


def test_alias_finds_old_code_judgment(store: Store, cfg: Settings) -> None:
    # BNS 103 question must reach IPC 302 judgments too.
    sources, ok = retrieve(store, cfg, "murder under Section 103 BNS", None, Profile())
    ids = {s.chunk.case_id for s in sources}
    assert ok and {"fs_2024_rao", "fs_2012_pillai"} <= ids


def test_filters_restrict_results(store: Store, cfg: Settings) -> None:
    # Filters choose precedents; Constitution articles always pass (they govern every court).
    sources, _ = retrieve(store, cfg, "bail", Filters(court="Bombay HC"), Profile())
    assert sources and all(s.chunk.case_id == "fs_2021_shaikh" for s in sources if not s.chunk.case_id.startswith("coi-"))
    sources, _ = retrieve(store, cfg, "bail", Filters(year_to=2016), Profile())
    assert all(
        s.chunk.case_id in {"fs_2015_mehta", "fs_2012_pillai", "fs_2016_verma"} for s in sources if not s.chunk.case_id.startswith("coi-")
    )


def test_evidence_gate(store: Store, cfg: Settings) -> None:
    _, ok = retrieve(
        store, cfg, "What is the punishment for sedition under Section 124A IPC?", None, Profile()
    )
    assert not ok
    _, ok = retrieve(
        store, cfg, "grounds for refusing bail under Section 439 CrPC", None, Profile()
    )
    assert ok
